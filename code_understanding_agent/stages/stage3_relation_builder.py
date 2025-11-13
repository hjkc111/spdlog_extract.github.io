# stages/stage3_relation_builder.py
import os
import json
from typing import Dict, List, Any, Tuple
from utils.clang_utils import ClangRelationExtractor
from utils.file_utils import load_json, save_json


class RelationBuilder:
    def __init__(self, stage2_output_file: str, output_dir: str = "data/processed"):
        self.stage2_output = load_json(stage2_output_file)
        self.output_dir = output_dir
        self.relation_extractor = ClangRelationExtractor()

    def extract_all_relations(self) -> Dict[str, Any]:
        """提取所有关系"""
        print("开始提取关系...")

        symbols = self.stage2_output["symbols"]
        project_path = self.stage2_output["stage1_reference"]

        relations = {
            "call_relations": [],
            "inheritance_relations": [],
            "containment_relations": [],
            "usage_relations": [],
            "friend_relations": [],
            "template_relations": []
        }

        # 提取函数调用关系
        relations["call_relations"] = self.extract_call_relations(symbols["functions"])

        # 提取继承关系
        relations["inheritance_relations"] = self.extract_inheritance_relations(symbols["classes"])

        # 提取包含关系
        relations["containment_relations"] = self.extract_containment_relations(symbols)

        # 提取使用关系
        relations["usage_relations"] = self.extract_usage_relations(symbols)

        return relations

    def extract_call_relations(self, functions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取函数调用关系"""
        call_relations = []

        for func_id, func_info in functions.items():
            if "calls" in func_info:
                for called_func in func_info["calls"]:
                    call_relations.append({
                        "caller": func_id,
                        "callee": called_func,
                        "relation_type": "calls",
                        "location": func_info.get("location", "")
                    })

        return call_relations

    def extract_inheritance_relations(self, classes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取继承关系"""
        inheritance_relations = []

        for class_id, class_info in classes.items():
            base_classes = class_info.get("base_classes", [])
            for base_class in base_classes:
                inheritance_relations.append({
                    "derived_class": class_id,
                    "base_class": base_class,
                    "relation_type": "inherits_from",
                    "access_specifier": base_class.get("access", "public")
                })

        return inheritance_relations

    def extract_containment_relations(self, symbols: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取包含关系（类包含成员）"""
        containment_relations = []

        for class_id, class_info in symbols["classes"].items():
            # 类包含成员函数
            member_functions = class_info.get("member_functions", [])
            for member_func in member_functions:
                containment_relations.append({
                    "container": class_id,
                    "contained": member_func,
                    "relation_type": "contains",
                    "member_type": "function"
                })

            # 类包含成员变量
            member_variables = class_info.get("member_variables", [])
            for member_var in member_variables:
                containment_relations.append({
                    "container": class_id,
                    "contained": member_var,
                    "relation_type": "contains",
                    "member_type": "variable"
                })

        return containment_relations

    def extract_usage_relations(self, symbols: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取使用关系"""
        usage_relations = []

        # 函数使用变量
        for func_id, func_info in symbols["functions"].items():
            used_variables = func_info.get("uses_variables", [])
            for var in used_variables:
                usage_relations.append({
                    "user": func_id,
                    "used": var,
                    "relation_type": "uses",
                    "usage_type": "variable"
                })

        return usage_relations

    def build_relation_graph(self, relations: Dict[str, Any]) -> Dict[str, Any]:
        """构建关系图"""
        print("构建关系图...")

        graph = {
            "nodes": {},
            "edges": [],
            "statistics": {
                "total_nodes": 0,
                "total_edges": 0,
                "node_types": {},
                "edge_types": {}
            }
        }

        # 添加节点
        self.add_nodes_to_graph(graph, self.stage2_output["symbols"])

        # 添加边
        self.add_edges_to_graph(graph, relations)

        # 计算统计信息
        self.calculate_graph_statistics(graph)

        return graph

    def add_nodes_to_graph(self, graph: Dict[str, Any], symbols: Dict[str, Any]):
        """添加节点到图"""
        # 添加函数节点
        for func_id, func_info in symbols["functions"].items():
            graph["nodes"][func_id] = {
                "type": "function",
                "name": func_info.get("name", ""),
                "return_type": func_info.get("return_type", ""),
                "location": func_info.get("location", "")
            }

        # 添加类节点
        for class_id, class_info in symbols["classes"].items():
            graph["nodes"][class_id] = {
                "type": "class",
                "name": class_info.get("name", ""),
                "location": class_info.get("location", "")
            }

    def add_edges_to_graph(self, graph: Dict[str, Any], relations: Dict[str, Any]):
        """添加边到图"""
        for relation_type, relation_list in relations.items():
            for relation in relation_list:
                edge = {
                    "source": relation.get("caller") or relation.get("derived_class") or
                              relation.get("container") or relation.get("user"),
                    "target": relation.get("callee") or relation.get("base_class") or
                              relation.get("contained") or relation.get("used"),
                    "type": relation["relation_type"],
                    "properties": {k: v for k, v in relation.items()
                                   if k not in ["caller", "callee", "derived_class", "base_class",
                                                "container", "contained", "user", "used", "relation_type"]}
                }
                graph["edges"].append(edge)

    def calculate_graph_statistics(self, graph: Dict[str, Any]):
        """计算图统计信息"""
        # 节点类型统计
        node_types = {}
        for node_id, node_info in graph["nodes"].items():
            node_type = node_info["type"]
            node_types[node_type] = node_types.get(node_type, 0) + 1

        # 边类型统计
        edge_types = {}
        for edge in graph["edges"]:
            edge_type = edge["type"]
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

        graph["statistics"] = {
            "total_nodes": len(graph["nodes"]),
            "total_edges": len(graph["edges"]),
            "node_types": node_types,
            "edge_types": edge_types
        }

    def save_stage_output(self, relations: Dict[str, Any], graph: Dict[str, Any]) -> str:
        """保存阶段输出"""
        output_data = {
            "relations": relations,
            "graph": graph,
            "statistics": graph["statistics"],
            "stage2_reference": self.stage2_output["stage1_reference"]
        }

        output_file = os.path.join(self.output_dir, "stage3_relations.json")
        save_json(output_data, output_file)
        print(f"阶段3输出已保存: {output_file}")
        return output_file


def run_stage3(stage2_output_file: str) -> str:
    """运行第三阶段：关系构建"""
    builder = RelationBuilder(stage2_output_file)
    relations = builder.extract_all_relations()
    graph = builder.build_relation_graph(relations)
    output_file = builder.save_stage_output(relations, graph)
    return output_file