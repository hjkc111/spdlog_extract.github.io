# stages/stage1_project_parser.py
import os
import json
import clang.cindex
from typing import Dict, List, Any
from utils.clang_utils import ClangProjectAnalyzer
from utils.file_utils import save_json, load_json


class ProjectParser:
    def __init__(self, project_path: str, output_dir: str = "data/processed"):
        self.project_path = project_path
        self.output_dir = output_dir
        self.clang_analyzer = ClangProjectAnalyzer()

    def find_compile_commands(self) -> str:
        """查找编译数据库"""
        possible_paths = [
            "compile_commands.json",
            "build/compile_commands.json",
            "cmake-build-debug/compile_commands.json"
        ]

        for path in possible_paths:
            full_path = os.path.join(self.project_path, path)
            if os.path.exists(full_path):
                print(f"找到编译数据库: {full_path}")
                return full_path

        # 如果没有找到，尝试生成
        return self.generate_compile_commands()

    def generate_compile_commands(self) -> str:
        """生成编译数据库"""
        print("未找到编译数据库，尝试生成...")
        # 这里可以调用bear或者使用CMake生成
        # 暂时返回空路径，使用默认参数
        return ""

    def collect_source_files(self) -> List[str]:
        """收集所有C++源文件"""
        source_files = []
        extensions = ['.cpp', '.cc', '.cxx', '.c', '.h', '.hpp', '.hxx']

        for root, dirs, files in os.walk(self.project_path):
            # 跳过一些常见的不需要解析的目录
            skip_dirs = {'build', 'cmake-build', 'test', 'tests', 'third_party', 'external'}
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    full_path = os.path.join(root, file)
                    source_files.append(full_path)

        print(f"找到 {len(source_files)} 个源文件")
        return source_files

    def parse_project_structure(self) -> Dict[str, Any]:
        """解析项目结构"""
        print("开始解析项目结构...")

        # 1. 获取编译数据库
        compile_commands_path = self.find_compile_commands()

        # 2. 收集源文件
        source_files = self.collect_source_files()

        # 3. 分析文件依赖
        file_dependencies = self.analyze_file_dependencies(source_files, compile_commands_path)

        # 4. 构建项目概览
        project_overview = {
            "project_path": self.project_path,
            "total_files": len(source_files),
            "source_files": source_files,
            "file_dependencies": file_dependencies,
            "compile_commands_path": compile_commands_path,
            "main_modules": self.identify_main_modules(file_dependencies)
        }

        return project_overview

    def analyze_file_dependencies(self, source_files: List[str], compile_commands_path: str) -> Dict[str, List[str]]:
        """分析文件依赖关系"""
        dependencies = {}

        for file_path in source_files[:10]:  # 先解析前10个文件作为示例
            try:
                file_deps = self.clang_analyzer.get_file_dependencies(file_path, compile_commands_path)
                dependencies[file_path] = file_deps
            except Exception as e:
                print(f"解析文件 {file_path} 时出错: {e}")
                dependencies[file_path] = []

        return dependencies

    def identify_main_modules(self, dependencies: Dict[str, List[str]]) -> List[str]:
        """识别主要模块"""
        # 简单的启发式方法：包含main函数的文件或依赖较多的文件
        main_modules = []
        for file_path, deps in dependencies.items():
            if len(deps) > 5:  # 依赖较多的文件可能是重要模块
                main_modules.append(file_path)

        return main_modules

    def save_stage_output(self, project_overview: Dict[str, Any]) -> str:
        """保存阶段输出"""
        output_file = os.path.join(self.output_dir, "stage1_project_overview.json")
        save_json(project_overview, output_file)
        print(f"阶段1输出已保存: {output_file}")
        return output_file


def run_stage1(project_path: str) -> str:
    """运行第一阶段：项目解析"""
    parser = ProjectParser(project_path)
    project_overview = parser.parse_project_structure()
    output_file = parser.save_stage_output(project_overview)
    return output_file