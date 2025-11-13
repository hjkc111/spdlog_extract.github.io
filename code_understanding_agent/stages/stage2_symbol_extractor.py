# stages/stage2_symbol_extractor.py
import os
import json
from typing import Dict, List, Any
from utils.clang_utils import ClangSymbolExtractor
from utils.file_utils import load_json, save_json


class SymbolExtractor:
    def __init__(self, stage1_output_file: str, output_dir: str = "data/processed"):
        self.stage1_output = load_json(stage1_output_file)
        self.output_dir = output_dir
        self.symbol_extractor = ClangSymbolExtractor()

    def extract_all_symbols(self) -> Dict[str, Any]:
        """提取所有符号"""
        print("开始提取符号...")

        project_path = self.stage1_output["project_path"]
        source_files = self.stage1_output["source_files"]
        compile_commands_path = self.stage1_output["compile_commands_path"]

        all_symbols = {
            "functions": {},
            "classes": {},
            "variables": {},
            "namespaces": {},
            "files": {}
        }

        # 解析每个文件
        for i, file_path in enumerate(source_files[:20]):  # 限制文件数量用于演示
            print(f"解析文件 {i + 1}/{min(20, len(source_files))}: {os.path.basename(file_path)}")

            try:
                file_symbols = self.symbol_extractor.extract_file_symbols(
                    file_path, compile_commands_path
                )

                # 合并符号
                self.merge_symbols(all_symbols, file_symbols, file_path)

            except Exception as e:
                print(f"解析文件 {file_path} 时出错: {e}")
                continue

        return all_symbols

    def merge_symbols(self, all_symbols: Dict[str, Any], file_symbols: Dict[str, Any], file_path: str):
        """合并符号信息"""
        # 记录文件级别的符号
        all_symbols["files"][file_path] = {
            "function_count": len(file_symbols.get("functions", {})),
            "class_count": len(file_symbols.get("classes", {})),
            "variable_count": len(file_symbols.get("variables", {}))
        }

        # 合并函数
        for func_name, func_info in file_symbols.get("functions", {}).items():
            func_id = f"{file_path}::{func_name}"
            all_symbols["functions"][func_id] = func_info

        # 合并类
        for class_name, class_info in file_symbols.get("classes", {}).items():
            class_id = f"{file_path}::{class_name}"
            all_symbols["classes"][class_id] = class_info

        # 合并变量
        for var_name, var_info in file_symbols.get("variables", {}).items():
            var_id = f"{file_path}::{var_name}"
            all_symbols["variables"][var_id] = var_info

    def analyze_symbol_statistics(self, all_symbols: Dict[str, Any]) -> Dict[str, Any]:
        """分析符号统计信息"""
        stats = {
            "total_functions": len(all_symbols["functions"]),
            "total_classes": len(all_symbols["classes"]),
            "total_variables": len(all_symbols["variables"]),
            "total_files": len(all_symbols["files"]),
            "function_complexity": self.calculate_complexity_stats(all_symbols["functions"]),
            "class_hierarchy": self.analyze_class_hierarchy(all_symbols["classes"])
        }
        return stats

    def calculate_complexity_stats(self, functions: Dict[str, Any]) -> Dict[str, Any]:
        """计算函数复杂度统计"""
        complexities = []
        for func_info in functions.values():
            if "complexity" in func_info:
                complexities.append(func_info["complexity"])

        if not complexities:
            return {"average": 0, "max": 0, "min": 0}

        return {
            "average": sum(complexities) / len(complexities),
            "max": max(complexities),
            "min": min(complexities)
        }

    def analyze_class_hierarchy(self, classes: Dict[str, Any]) -> Dict[str, Any]:
        """分析类层次结构"""
        hierarchy = {
            "total_base_classes": 0,
            "total_derived_classes": 0,
            "max_inheritance_depth": 0
        }

        for class_info in classes.values():
            base_classes = class_info.get("base_classes", [])
            if base_classes:
                hierarchy["total_derived_classes"] += 1
            else:
                hierarchy["total_base_classes"] += 1

        return hierarchy

    def save_stage_output(self, all_symbols: Dict[str, Any], stats: Dict[str, Any]) -> str:
        """保存阶段输出"""
        output_data = {
            "symbols": all_symbols,
            "statistics": stats,
            "stage1_reference": self.stage1_output["project_path"]
        }

        output_file = os.path.join(self.output_dir, "stage2_symbols.json")
        save_json(output_data, output_file)
        print(f"阶段2输出已保存: {output_file}")
        return output_file


def run_stage2(stage1_output_file: str) -> str:
    """运行第二阶段：符号提取"""
    extractor = SymbolExtractor(stage1_output_file)
    all_symbols = extractor.extract_all_symbols()
    stats = extractor.analyze_symbol_statistics(all_symbols)
    output_file = extractor.save_stage_output(all_symbols, stats)
    return output_file