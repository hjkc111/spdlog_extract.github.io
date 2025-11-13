# stages/stage4_knowledge_graph.py
import os
import json
from typing import Dict, List, Any
from utils.file_utils import load_json, save_json
from utils.qwen_api import QwenAPI


class KnowledgeGraphBuilder:
    def __init__(self, stage3_output_file: str, output_dir: str = "data/processed"):
        self.stage3_output = load_json(stage3_output_file)
        self.output_dir = output_dir
        self.qwen_api = QwenAPI()

    def enhance_with_semantic_understanding(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        """使用Qwen API增强语义理解"""
        print("使用Qwen API增强语义理解...")

        enhanced_graph = graph.copy()

        # 为每个节点添加语义描述
        for node_id, node_info in enhanced_graph["nodes"].items():
            if node_info["type"] == "function":
                semantic_info = self.analyze_function_semantics(node_info)
                node_info["semantic"] = semantic_info
            elif node_info["type"] == "class":
                semantic_info = self.analyze_class_semantics(node_info)
                node_info["semantic"] = semantic_info

        return enhanced_graph

    def analyze_function_semantics(self, function_info: Dict[str, Any]) -> Dict[str, Any]:
        """分析函数语义"""
        prompt = f"""
        请分析以下C++函数的语义信息：

        函数名: {function_info.get('name', '')}
        返回类型: {function_info.get('return_type', '')}
        位置: {function_info.get('location', '')}

        请提供：
        1. 函数的主要功能描述
        2. 可能的使用场景
        3. 关键算法或逻辑
        4. 复杂度分析

        请用JSON格式返回：
        {{
            "function_description": "描述",
            "usage_scenarios": ["场景1", "场景2"],
            "key_algorithms": ["算法1", "算法2"], 
            "complexity_analysis": "复杂度分析"
        }}
        """

        try:
            response = self.qwen_api.query(prompt)
            return self.parse_semantic_response(response)
        except Exception as e:
            print(f"Qwen API调用失败: {e}")
            return {
                "function_description": "无法获取语义分析",
                "usage_scenarios": [],
                "key_algorithms": [],
                "complexity_analysis": "未知"
            }

    def analyze_class_semantics(self, class_info: Dict[str, Any]) -> Dict[str, Any]:
        """分析类语义"""
        prompt = f"""
        请分析以下C++类的语义信息：

        类名: {class_info.get('name', '')}
        位置: {class_info.get('location', '')}

        请提供：
        1. 类的主要职责和功能
        2. 设计模式或架构模式
        3. 关键成员和方法
        4. 使用建议

        请用JSON格式返回：
        {{
            "class_description": "描述",
            "design_patterns": ["模式1", "模式2"],
            "key_members": ["成员1", "成员2"],
            "usage_recommendations": ["建议1", "建议2"]
        }}
        """

        try:
            response = self.qwen_api.query(prompt)
            return self.parse_semantic_response(response)
        except Exception as e:
            print(f"Qwen API调用失败: {e}")
            return {
                "class_description": "无法获取语义分析",
                "design_patterns": [],
                "key_members": [],
                "usage_recommendations": []
            }

    def parse_semantic_response(self, response: str) -> Dict[str, Any]:
        """解析语义响应"""
        try:
            # 尝试从响应中提取JSON
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except:
            pass

        return {"raw_response": response}

    def build_knowledge_graph(self) -> Dict[str, Any]:
        """构建知识图谱"""
        print("构建知识图谱...")

        graph = self.stage3_output["graph"]

        # 增强语义理解
        enhanced_graph = self.enhance_with_semantic_understanding(graph)

        # 构建知识图谱结构
        knowledge_graph = {
            "metadata": {
                "project": self.stage3_output["stage2_reference"],
                "total_nodes": len(enhanced_graph["nodes"]),
                "total_edges": len(enhanced_graph["edges"]),
                "enhanced_with_ai": True
            },
            "nodes": enhanced_graph["nodes"],
            "edges": enhanced_graph["edges"],
            "clusters": self.identify_clusters(enhanced_graph)
        }

        return knowledge_graph

    def identify_clusters(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        """识别代码簇（相关功能的代码组）"""
        clusters = {}

        # 基于调用关系识别簇
        call_clusters = self.identify_call_clusters(graph)
        clusters["call_clusters"] = call_clusters

        # 基于类层次识别簇
        class_clusters = self.identify_class_clusters(graph)
        clusters["class_clusters"] = class_clusters

        # 基于语义相似性识别簇
        semantic_clusters = self.identify_semantic_clusters(graph)
        clusters["semantic_clusters"] = semantic_clusters

        return clusters

    def identify_call_clusters(self, graph: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于调用关系识别簇"""
        # 简化的实现：找到相互调用的函数组
        clusters = []
        visited = set()

        for node_id, node_info in graph["nodes"].items():
            if node_id not in visited and node_info["type"] == "function":
                cluster = self.find_connected_component(graph, node_id, visited)
                if len(cluster) > 1:  # 至少两个节点
                    clusters.append({
                        "type": "call_cluster",
                        "nodes": cluster,
                        "size": len(cluster),
                        "description": f"包含 {len(cluster)} 个相关函数的调用簇"
                    })

        return clusters

    def find_connected_component(self, graph: Dict[str, Any], start_node: str, visited: set) -> List[str]:
        """找到连通分量"""
        cluster = []
        stack = [start_node]

        while stack:
            node = stack.pop()
            if node not in visited:
                visited.add(node)
                cluster.append(node)

                # 找到所有相邻节点
                for edge in graph["edges"]:
                    if edge["source"] == node and edge["target"] not in visited:
                        stack.append(edge["target"])
                    elif edge["target"] == node and edge["source"] not in visited:
                        stack.append(edge["source"])

        return cluster

    def identify_class_clusters(self, graph: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于类层次识别簇"""
        clusters = []

        # 找到所有基类及其派生类
        base_classes = {}
        for edge in graph["edges"]:
            if edge["type"] == "inherits_from":
                base_class = edge["target"]
                derived_class = edge["source"]

                if base_class not in base_classes:
                    base_classes[base_class] = []
                base_classes[base_class].append(derived_class)

        for base_class, derived_classes in base_classes.items():
            if derived_classes:
                clusters.append({
                    "type": "inheritance_cluster",
                    "base_class": base_class,
                    "derived_classes": derived_classes,
                    "size": len(derived_classes) + 1,
                    "description": f"以 {base_class.split('::')[-1]} 为基类的继承层次"
                })

        return clusters

    def identify_semantic_clusters(self, graph: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于语义相似性识别簇"""
        # 这里可以基于AI分析的语义信息进行聚类
        # 暂时返回空列表，后续可以增强
        return []

    def save_stage_output(self, knowledge_graph: Dict[str, Any]) -> str:
        """保存阶段输出"""
        output_file = os.path.join(self.output_dir, "stage4_knowledge_graph.json")
        save_json(knowledge_graph, output_file)
        print(f"阶段4输出已保存: {output_file}")
        return output_file


def run_stage4(stage3_output_file: str) -> str:
    """运行第四阶段：知识图谱构建"""
    builder = KnowledgeGraphBuilder(stage3_output_file)
    knowledge_graph = builder.build_knowledge_graph()
    output_file = builder.save_stage_output(knowledge_graph)
    return output_file