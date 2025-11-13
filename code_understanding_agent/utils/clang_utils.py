# utils/clang_utils.py
import os
import clang.cindex
from typing import Dict, List, Any
from config.settings import LLVM_PATH, LLVM_BIN_PATH, CLANG_LIBRARY_PATH

class ClangProjectAnalyzer:
    def __init__(self):
        self.setup_clang()

    def setup_clang(self):
        """设置Clang环境 - 支持自定义路径"""
        try:
            # 优先使用配置文件中的路径
            if CLANG_LIBRARY_PATH and os.path.exists(CLANG_LIBRARY_PATH):
                clang.cindex.Config.set_library_file(CLANG_LIBRARY_PATH)
                print(f"✅ 使用配置的libclang路径: {CLANG_LIBRARY_PATH}")
                return

            # 备用：尝试在LLVM路径中查找
            possible_paths = [
                CLANG_LIBRARY_PATH,
                os.path.join(LLVM_BIN_PATH, 'libclang.dll'),
                os.path.join(LLVM_PATH, 'bin', 'libclang.dll'),
                r'C:\Program Files\LLVM\bin\libclang.dll',
                r'C:\LLVM\bin\libclang.dll',
            ]

            for path in possible_paths:
                if path and os.path.exists(path):
                    clang.cindex.Config.set_library_file(path)
                    print(f"✅ 设置libclang路径: {path}")
                    return

            # 如果自动查找失败，提供详细错误信息
            print("❌ 未找到libclang.dll，请检查以下路径:")
            for path in possible_paths:
                exists = "存在" if path and os.path.exists(path) else "不存在"
                print(f"  {path} - {exists}")

            print(f"\n请确保:")
            print(f"1. LLVM已安装到: {LLVM_PATH}")
            print(f"2. 在.env文件中正确设置LLVM_PATH")
            print(f"3. libclang.dll存在于bin目录中")

        except Exception as e:
            print(f"❌ Clang配置失败: {e}")
            print("请检查LLVM安装和路径配置")

    def get_compile_args_for_file(self, file_path: str, compile_commands_path: str) -> List[str]:
        """获取文件的编译参数"""
        if not compile_commands_path or not os.path.exists(compile_commands_path):
            # 使用LLVM路径中的头文件
            include_paths = self.get_llvm_include_paths()
            return ['-x', 'c++', '-std=c++17'] + include_paths

        try:
            import json
            with open(compile_commands_path, 'r') as f:
                compile_commands = json.load(f)

            for command in compile_commands:
                if command['file'] == file_path:
                    import shlex
                    args = shlex.split(command['command'])
                    # 过滤掉编译器路径和源文件路径
                    filtered_args = []
                    skip_next = False
                    for arg in args:
                        if skip_next:
                            skip_next = False
                            continue
                        if arg in ['-o', '-c']:
                            skip_next = True
                            continue
                        if not arg.endswith('.cpp') and not arg.endswith('.cc') and not arg.endswith('.c'):
                            filtered_args.append(arg)
                    return filtered_args

        except Exception as e:
            print(f"解析编译数据库失败: {e}")

        # 默认参数
        include_paths = self.get_llvm_include_paths()
        return ['-x', 'c++', '-std=c++17'] + include_paths

    def get_llvm_include_paths(self) -> List[str]:
        """获取LLVM包含路径"""
        include_paths = []

        # LLVM包含路径
        possible_include_dirs = [
            os.path.join(LLVM_PATH, 'include'),
            os.path.join(LLVM_PATH, 'lib', 'clang', '16.0.6', 'include'),  # 根据版本调整
            os.path.join(LLVM_PATH, 'lib', 'clang', '16', 'include'),
        ]

        for include_dir in possible_include_dirs:
            if os.path.exists(include_dir):
                include_paths.append(f'-I{include_dir}')

        return include_paths

class ClangSymbolExtractor:
    def __init__(self):
        self.analyzer = ClangProjectAnalyzer()

    def extract_file_symbols(self, file_path: str, compile_commands_path: str) -> Dict[str, Any]:
        """提取文件中的符号"""
        symbols = {
            "functions": {},
            "classes": {},
            "variables": {},
            "namespaces": {}
        }

        try:
            index = clang.cindex.Index.create()
            args = self.analyzer.get_compile_args_for_file(file_path, compile_commands_path)
            tu = index.parse(file_path, args=args)

            # 遍历AST
            self.traverse_ast(tu.cursor, file_path, symbols)

        except Exception as e:
            print(f"提取符号失败 {file_path}: {e}")

        return symbols

    def traverse_ast(self, cursor, file_path: str, symbols: Dict[str, Any], depth: int = 0):
        """遍历AST"""
        # 只处理在目标文件中的定义
        if (cursor.location.file and
                cursor.location.file.name == file_path and
                cursor.kind != clang.cindex.CursorKind.TRANSLATION_UNIT):

            if cursor.kind == clang.cindex.CursorKind.FUNCTION_DECL:
                self.extract_function(cursor, symbols)
            elif cursor.kind == clang.cindex.CursorKind.CXX_METHOD:
                self.extract_method(cursor, symbols)
            elif cursor.kind == clang.cindex.CursorKind.CLASS_DECL:
                self.extract_class(cursor, symbols)
            elif cursor.kind == clang.cindex.CursorKind.VAR_DECL:
                self.extract_variable(cursor, symbols)
            elif cursor.kind == clang.cindex.CursorKind.NAMESPACE:
                self.extract_namespace(cursor, symbols)

        # 递归遍历子节点
        for child in cursor.get_children():
            self.traverse_ast(child, file_path, symbols, depth + 1)

    def extract_function(self, cursor, symbols: Dict[str, Any]):
        """提取函数信息"""
        func_info = {
            "name": cursor.spelling,
            "return_type": cursor.result_type.spelling if cursor.result_type else "void",
            "parameters": self.extract_parameters(cursor),
            "location": f"{cursor.location.file}:{cursor.location.line}",
            "access_specifier": self.get_access_specifier(cursor),
            "is_static": cursor.is_static_method(),
            "is_virtual": cursor.is_virtual_method(),
            "complexity": self.estimate_complexity(cursor)
        }

        symbols["functions"][cursor.spelling] = func_info

    def extract_method(self, cursor, symbols: Dict[str, Any]):
        """提取方法信息"""
        # 方法与函数类似，但属于类
        self.extract_function(cursor, symbols)

    def extract_class(self, cursor, symbols: Dict[str, Any]):
        """提取类信息"""
        class_info = {
            "name": cursor.spelling,
            "location": f"{cursor.location.file}:{cursor.location.line}",
            "access_specifier": self.get_access_specifier(cursor),
            "base_classes": self.extract_base_classes(cursor),
            "member_functions": [],
            "member_variables": []
        }

        symbols["classes"][cursor.spelling] = class_info

    def extract_variable(self, cursor, symbols: Dict[str, Any]):
        """提取变量信息"""
        var_info = {
            "name": cursor.spelling,
            "type": cursor.type.spelling,
            "location": f"{cursor.location.file}:{cursor.location.line}",
            "is_const": cursor.type.is_const_qualified(),
            "is_static": cursor.storage_class == clang.cindex.StorageClass.STATIC
        }

        symbols["variables"][cursor.spelling] = var_info

    def extract_namespace(self, cursor, symbols: Dict[str, Any]):
        """提取命名空间信息"""
        namespace_info = {
            "name": cursor.spelling,
            "location": f"{cursor.location.file}:{cursor.location.line}"
        }

        symbols["namespaces"][cursor.spelling] = namespace_info

    def extract_parameters(self, cursor) -> List[Dict[str, str]]:
        """提取参数列表"""
        parameters = []
        for arg in cursor.get_arguments():
            parameters.append({
                "name": arg.spelling,
                "type": arg.type.spelling
            })
        return parameters

    def extract_base_classes(self, cursor) -> List[Dict[str, str]]:
        """提取基类列表"""
        base_classes = []
        for child in cursor.get_children():
            if child.kind == clang.cindex.CursorKind.CXX_BASE_SPECIFIER:
                base_classes.append({
                    "name": child.type.spelling,
                    "access": self.get_access_specifier(child)
                })
        return base_classes

    def get_access_specifier(self, cursor) -> str:
        """获取访问说明符"""
        access_map = {
            clang.cindex.AccessSpecifier.PUBLIC: "public",
            clang.cindex.AccessSpecifier.PROTECTED: "protected",
            clang.cindex.AccessSpecifier.PRIVATE: "private",
            clang.cindex.AccessSpecifier.NONE: "none"
        }
        return access_map.get(cursor.access_specifier, "none")

    def estimate_complexity(self, cursor) -> int:
        """估计函数复杂度（简化版）"""
        complexity = 1
        for child in cursor.get_children():
            if child.kind in [
                clang.cindex.CursorKind.IF_STMT,
                clang.cindex.CursorKind.FOR_STMT,
                clang.cindex.CursorKind.WHILE_STMT,
                clang.cindex.CursorKind.DO_STMT,
                clang.cindex.CursorKind.SWITCH_STMT
            ]:
                complexity += 1
        return complexity


class ClangRelationExtractor:
    def __init__(self):
        self.analyzer = ClangProjectAnalyzer()

    def extract_call_relations(self, file_path: str, compile_commands_path: str) -> List[Dict[str, str]]:
        """提取调用关系"""
        # 这里可以实现更复杂的调用关系提取
        # 暂时返回空列表
        return []