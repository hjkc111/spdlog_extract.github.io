# stages/stage5_semantic_embedder.py
import os
import json
import numpy as np
from typing import Dict, List, Any
from utils.file_utils import load_json, save_json
from utils.qwen_api import QwenAPI


class SemanticEmbedder:
    def __init__(self, stage4_output_file: str, output_dir: str = "data/processed"):
        self.knowledge_graph = load_json(stage4_output_file)
        self.output_dir = output_dir
        self.qwen_api = QwenAPI()

    def generate_semantic_embeddings(self) -> Dict[str, Any]:
        """生成语义嵌入"""
        print("生成语义嵌入...")

        embeddings = {}

        # 为每个节点生成嵌入
        for node_id, node_info in self.knowledge_graph["nodes"].items():
            embedding = self.generate_node_embedding(node_info)
            embeddings[node_id] = embedding

        # 为边生成嵌入
        edge_embeddings = {}
        for i, edge in enumerate(self.knowledge_graph["edges"]):
            edge_embedding = self.generate_edge_embedding(edge)
            edge_embeddings[f"edge_{i}"] = edge_embedding

        return {
            "node_embeddings": embeddings,
            "edge_embeddings": edge_embeddings,
            "embedding_dimension": 512  # 假设的维度
        }

    def generate_node_embedding(self, node_info: Dict[str, Any]) -> Dict[str, Any]:
        """生成节点嵌入"""
        # 基于节点类型和语义信息生成嵌入
        if node_info["type"] == "function":
            return self.embed_function(node_info)
        elif node_info["type"] == "class":
            return self.embed_class(node_info)
        else:
            return self.embed_generic_node(node_info)

    def embed_function(self, function_info: Dict[str, Any]) -> Dict[str, Any]:
        """嵌入函数"""
        semantic_info = function_info.get("semantic", {})

        prompt = f"""
        请为以下C++函数生成语义特征向量：

        函数名: {function_info.get('name', '')}
        返回类型: {function_info.get('return_type', '')}
        功能描述: {semantic_info.get('function_description', '')}
        使用场景: {', '.join(semantic_info.get('usage_scenarios', []))}
        关键算法: {', '.join(semantic_info.get('key_algorithms', []))}

        请生成一个512维的语义特征向量，用JSON数组格式返回：
        {{
            "embedding": [0.1, 0.2, ...],  // 512个浮点数
            "semantic_tags": ["标签1", "标签2", ...],
            "complexity_score": 0.5  // 0-1之间的复杂度评分
        }}
        """

        try:
            response = self.qwen_api.query(prompt)
            return self.parse_embedding_response(response)
        except Exception as e:
            print(f"生成函数嵌入失败: {e}")
            return self.generate_fallback_embedding(function_info)

    def embed_class(self, class_info: Dict[str, Any]) -> Dict[str, Any]:
        """嵌入类"""
        semantic_info = class_info.get("semantic", {})

        prompt = f"""
        请为以下C++类生成语义特征向量：

        类名: {class_info.get('name', '')}
        职责描述: {semantic_info.get('class_description', '')}
        设计模式: {', '.join(semantic_info.get('design_patterns', []))}
        关键成员: {', '.join(semantic_info.get('key_members', []))}

        请生成一个512维的语义特征向量，用JSON数组格式返回：
        {{
            "embedding": [0.1, 0.2, ...],  // 512个浮点数  
            "semantic_tags": ["标签1", "标签2", ...],
            "abstraction_level": 0.5  // 0-1之间的抽象级别
        }}
        """

        try:
            response = self.qwen_api.query(prompt)
            return self.parse_embedding_response(response)
        except Exception as e:
            print(f"生成类嵌入失败: {e}")
            return self.generate_fallback_embedding(class_info)

    def embed_generic_node(self, node_info: Dict[str, Any]) -> Dict[str, Any]:
        """嵌入通用节点"""
        return self.generate_fallback_embedding(node_info)

    def generate_edge_embedding(self, edge_info: Dict[str, Any]) -> Dict[str, Any]:
        """生成边嵌入"""
        relation_type = edge_info["type"]

        prompt = f"""
        请为以下代码关系生成语义特征向量：

        关系类型: {relation_type}
        源节点: {edge_info['source']}
        目标节点: {edge_info['target']}
        属性: {json.dumps(edge_info.get('properties', {}), ensure_ascii=False)}

        请生成一个256维的关系特征向量，用JSON数组格式返回：
        {{
            "embedding": [0.1, 0.2, ...],  // 256个浮点数
            "relation_strength": 0.8,  // 0-1之间的关系强度
            "semantic_relation": "语义关系描述"
        }}
        """

        try:
            response = self.qwen_api.query(prompt)
            return self.parse_embedding_response(response)
        except Exception as e:
            print(f"生成边嵌入失败: {e}")
            return self.generate_fallback_edge_embedding(edge_info)

    def parse_embedding_response(self, response: str) -> Dict[str, Any]:
        """解析嵌入响应"""
        try:
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                embedding_data = json.loads(json_str)

                # 确保嵌入向量格式正确
                if "embedding" in embedding_data and isinstance(embedding_data["embedding"], list):
                    return embedding_data
        except Exception as e:
            print(f"解析嵌入响应失败: {e}")

        return self.generate_fallback_embedding({})

    def generate_fallback_embedding(self, node_info: Dict[str, Any]) -> Dict[str, Any]:
        """生成回退嵌入"""
        # 基于节点名称和类型生成简单的嵌入
        node_name = node_info.get('name', 'unknown')
        node_type = node_info.get('type', 'unknown')

        # 简单的哈希嵌入（实际应用中应该使用更好的方法）
        import hashlib
        hash_obj = hashlib.md5(f"{node_name}_{node_type}".encode())
        hash_bytes = hash_obj.digest()

        # 生成伪随机但确定性的嵌入
        np.random.seed(int.from_bytes(hash_bytes[:4], 'little'))
        embedding = np.random.randn(512).tolist()

        return {
            "embedding": embedding,
            "semantic_tags": [node_type, "fallback_embedding"],
            "confidence": 0.3  # 低置信度
        }

    def generate_fallback_edge_embedding(self, edge_info: Dict[str, Any]) -> Dict[str, Any]:
        """生成回退边嵌入"""
        relation_type = edge_info["type"]

        import hashlib
        hash_obj = hashlib.md5(f"{relation_type}_{edge_info['source']}_{edge_info['target']}".encode())
        hash_bytes = hash_obj.digest()

        np.random.seed(int.from_bytes(hash_bytes[:4], 'little'))
        embedding = np.random.randn(256).tolist()

        return {
            "embedding": embedding,
            "relation_strength": 0.5,
            "semantic_relation": f"{relation_type} relation"
        }

    def build_semantic_index(self, embeddings: Dict[str, Any]) -> Dict[str, Any]:
        """构建语义索引"""
        print("构建语义索引...")

        semantic_index = {
            "node_embeddings": embeddings["node_embeddings"],
            "edge_embeddings": embeddings["edge_embeddings"],
            "similarity_matrix": self.compute_similarity_matrix(embeddings["node_embeddings"]),
            "search_index": self.build_search_index(embeddings["node_embeddings"])
        }

        return semantic_index

    def compute_similarity_matrix(self, node_embeddings: Dict[str, Any]) -> Dict[str, Any]:
        """计算相似度矩阵"""
        # 简化的实现：只计算前几个节点的相似度
        node_ids = list(node_embeddings.keys())[:10]  # 限制数量

        similarity_matrix = {}
        for i, node_id1 in enumerate(node_ids):
            similarities = {}
            emb1 = np.array(node_embeddings[node_id1].get("embedding", []))

            for node_id2 in node_ids:
                if node_id1 != node_id2:
                    emb2 = np.array(node_embeddings[node_id2].get("embedding", []))
                    if len(emb1) > 0 and len(emb2) > 0 and len(emb1) == len(emb2):
                        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                        similarities[node_id2] = float(similarity)

            similarity_matrix[node_id1] = similarities

        return similarity_matrix

    def build_search_index(self, node_embeddings: Dict[str, Any]) -> Dict[str, Any]:
        """构建搜索索引"""
        search_index = {}

        for node_id, embedding_info in node_embeddings.items():
            tags = embedding_info.get("semantic_tags", [])
            for tag in tags:
                if tag not in search_index:
                    search_index[tag] = []
                search_index[tag].append({
                    "node_id": node_id,
                    "confidence": embedding_info.get("confidence", 0.5)
                })

        return search_index

    def save_stage_output(self, semantic_index: Dict[str, Any]) -> str:
        """保存阶段输出"""
        output_data = {
            "semantic_index": semantic_index,
            "knowledge_graph_reference": self.knowledge_graph["metadata"]["project"]
        }

        output_file = os.path.join(self.output_dir, "stage5_semantic_index.json")
        save_json(output_data, output_file)
        print(f"阶段5输出已保存: {output_file}")
        return output_file


def run_stage5(stage4_output_file: str) -> str:
    """运行第五阶段：语义嵌入"""
    embedder = SemanticEmbedder(stage4_output_file)
    embeddings = embedder.generate_semantic_embeddings()
    semantic_index = embedder.build_semantic_index(embeddings)
    output_file = embedder.save_stage_output(semantic_index)
    return output_file