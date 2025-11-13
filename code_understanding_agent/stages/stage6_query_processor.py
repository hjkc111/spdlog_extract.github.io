# stages/stage6_query_processor.py
import os
import json
import re
from typing import Dict, List, Any, Tuple
from loguru import logger

from utils.file_utils import load_json
from utils.qwen_api import qwen_api
from utils.vector_db import vector_db


class QueryProcessor:
    def __init__(self, stage5_output_file: str):
        self.project_data = load_json(stage5_output_file)
        self.project_name = self.project_data.get("project_name", "unknown")
        
        # 尝试加载知识图谱（如果存在）
        try:
            kg_file = stage5_output_file.replace("stage5", "stage4")
            if os.path.exists(kg_file):
                self.knowledge_graph = load_json(kg_file)
            else:
                self.knowledge_graph = {"nodes": {}, "edges": []}
        except:
            self.knowledge_graph = {"nodes": {}, "edges": []}

    def process_query(self, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理用户查询"""
        logger.info(f"处理查询: {user_query}")

        try:
            # 1. 使用向量数据库进行语义搜索
            search_results = vector_db.search_similar_code(
                query=user_query,
                n_results=10,
                filters=context.get('filters') if context else None
            )
            
            # 2. 简化的意图识别
            intent = self.identify_intent(user_query)
            
            # 3. 格式化搜索结果
            formatted_results = self.format_search_results(search_results, intent)
            
            return {
                "query": user_query,
                "intent": intent,
                "context": formatted_results,
                "total_results": len(search_results),
                "search_enabled": True
            }
            
        except Exception as e:
            logger.error(f"查询处理失败: {e}")
            return {
                "query": user_query,
                "intent": "GENERAL_QUERY",
                "context": [],
                "total_results": 0,
                "search_enabled": False,
                "error": str(e)
            }
    
    def identify_intent(self, user_query: str) -> str:
        """简化的意图识别"""
        query_lower = user_query.lower()
        
        # 意图分类
        if any(word in query_lower for word in ['实现', '怎么实现', '如何实现', 'implementation', 'implement']):
            return "FIND_IMPLEMENTATION"
        elif any(word in query_lower for word in ['定义', '在哪里定义', 'definition', 'define']):
            return "FIND_DEFINITION"
        elif any(word in query_lower for word in ['做什么', '功能', '作用', 'what does', 'function']):
            return "EXPLAIN_FUNCTION"
        elif any(word in query_lower for word in ['使用', '调用', 'usage', 'use', 'call']):
            return "FIND_USAGE"
        elif any(word in query_lower for word in ['关系', '依赖', '关联', 'relation', 'dependency']):
            return "SHOW_RELATIONS"
        elif any(word in query_lower for word in ['跳转', '转到', '查看', 'navigate', 'go to']):
            return "NAVIGATE_CODE"
        else:
            return "GENERAL_QUERY"
    
    def format_search_results(self, search_results: List[Dict[str, Any]], intent: str) -> List[Dict[str, Any]]:
        """格式化搜索结果"""
        formatted_results = []
        
        for result in search_results:
            formatted_result = {
                "id": result.get("id", ""),
                "content": result.get("content", ""),
                "metadata": result.get("metadata", {}),
                "similarity": result.get("similarity", 0.0),
                "relevance_score": self.calculate_relevance_score(result, intent)
            }
            formatted_results.append(formatted_result)
        
        # 根据相关性分数排序
        formatted_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return formatted_results
    
    def calculate_relevance_score(self, result: Dict[str, Any], intent: str) -> float:
        """计算相关性分数"""
        base_score = result.get("similarity", 0.0)
        metadata = result.get("metadata", {})
        
        # 根据意图调整分数
        if intent == "FIND_IMPLEMENTATION" and metadata.get("chunk_type") == "function":
            base_score *= 1.2
        elif intent == "EXPLAIN_FUNCTION" and metadata.get("chunk_type") == "function":
            base_score *= 1.1
        elif intent == "FIND_DEFINITION" and metadata.get("chunk_type") in ["class", "function"]:
            base_score *= 1.15
        
        # 根据复杂度调整分数（复杂度高的可能更重要）
        complexity = metadata.get("complexity", 0)
        if complexity > 10:
            base_score *= 1.05
        
        return min(base_score, 1.0)  # 确保分数不超过1.0

    def analyze_query(self, user_query: str) -> Dict[str, Any]:
        """分析查询"""
        prompt = f"""
        请分析以下代码理解查询：

        用户查询: "{user_query}"

        请分析：
        1. 查询的核心需求
        2. 查询中提到的代码概念
        3. 用户可能的知识水平
        4. 期望的回答详细程度

        请用JSON格式返回分析结果：
        {{
            "core_requirement": "核心需求描述",
            "code_concepts": ["概念1", "概念2"],
            "user_knowledge_level": "beginner|intermediate|expert",
            "expected_detail_level": "brief|detailed|comprehensive"
        }}
        """

        try:
            response = self.qwen_api.query(prompt)
            return self.parse_query_analysis(response)
        except Exception as e:
            print(f"查询分析失败: {e}")
            return self.fallback_query_analysis(user_query)

    def parse_query_analysis(self, response: str) -> Dict[str, Any]:
        """解析查询分析结果"""
        try:
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except:
            pass

        return self.fallback_query_analysis("")

    def fallback_query_analysis(self, user_query: str) -> Dict[str, Any]:
        """回退查询分析"""
        # 基于关键词的简单分析
        query_lower = user_query.lower()

        concepts = []
        if any(word in query_lower for word in ['函数', 'function']):
            concepts.append("function")
        if any(word in query_lower for word in ['类', 'class']):
            concepts.append("class")
        if any(word in query_lower for word in ['实现', 'implement']):
            concepts.append("implementation")

        return {
            "core_requirement": user_query,
            "code_concepts": concepts,
            "user_knowledge_level": "intermediate",
            "expected_detail_level": "detailed"
        }

    def identify_intent(self, user_query: str, query_analysis: Dict[str, Any]) -> str:
        """识别查询意图"""
        query_lower = user_query.lower()

        # 意图分类
        intents = {
            "FIND_IMPLEMENTATION": ["实现", "怎么实现", "如何实现", "implementation", "implement"],
            "FIND_DEFINITION": ["定义", "在哪里定义", "definition", "define"],
            "EXPLAIN_FUNCTION": ["做什么", "功能", "作用", "what does", "function"],
            "FIND_USAGE": ["使用", "调用", "usage", "use", "call"],
            "SHOW_RELATIONS": ["关系", "依赖", "关联", "relation", "dependency"],
            "NAVIGATE_CODE": ["跳转", "转到", "查看", "navigate", "go to"]
        }

        for intent, keywords in intents.items():
            if any(keyword in query_lower for keyword in keywords):
                return intent

        return "GENERAL_QUERY"

    def extract_entities(self, user_query: str, query_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取查询中的实体"""
        entities = []

        # 使用Qwen API提取实体
        prompt = f"""
        从以下查询中提取代码相关的实体：

        查询: "{user_query}"

        请识别：
        1. 函数名、类名、变量名等标识符
        2. 代码概念（如算法、设计模式等）
        3. 项目特定的术语

        请用JSON格式返回：
        {{
            "identifiers": ["标识符1", "标识符2"],
            "concepts": ["概念1", "概念2"], 
            "project_terms": ["术语1", "术语2"]
        }}
        """

        try:
            response = self.qwen_api.query(prompt)
            entity_data = self.parse_entity_response(response)
            entities.extend(self.format_entities(entity_data))
        except Exception as e:
            print(f"实体提取失败: {e}")
            entities.extend(self.fallback_entity_extraction(user_query))

        return entities

    def parse_entity_response(self, response: str) -> Dict[str, Any]:
        """解析实体响应"""
        try:
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except:
            pass

        return {"identifiers": [], "concepts": [], "project_terms": []}

    def format_entities(self, entity_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """格式化实体"""
        entities = []

        for identifier in entity_data.get("identifiers", []):
            entities.append({
                "type": "identifier",
                "value": identifier,
                "confidence": 0.8
            })

        for concept in entity_data.get("concepts", []):
            entities.append({
                "type": "concept",
                "value": concept,
                "confidence": 0.7
            })

        for term in entity_data.get("project_terms", []):
            entities.append({
                "type": "project_term",
                "value": term,
                "confidence": 0.6
            })

        return entities

    def fallback_entity_extraction(self, user_query: str) -> List[Dict[str, Any]]:
        """回退实体提取"""
        # 简单的基于正则表达式的提取
        entities = []

        # 提取可能的函数名/类名（大写字母开头的单词）
        pattern = r'\b[A-Z][a-zA-Z0-9_]*\b'
        matches = re.findall(pattern, user_query)

        for match in matches:
            entities.append({
                "type": "identifier",
                "value": match,
                "confidence": 0.5
            })

        return entities

    def select_retrieval_strategy(self, intent: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """选择检索策略"""
        strategies = {
            "FIND_IMPLEMENTATION": {
                "primary": "semantic_search",
                "secondary": ["exact_match", "relation_traversal"],
                "filters": ["function", "class"]
            },
            "FIND_DEFINITION": {
                "primary": "exact_match",
                "secondary": ["semantic_search"],
                "filters": ["function", "class", "variable"]
            },
            "EXPLAIN_FUNCTION": {
                "primary": "semantic_search",
                "secondary": ["relation_traversal", "context_analysis"],
                "filters": ["function"]
            },
            "FIND_USAGE": {
                "primary": "relation_traversal",
                "secondary": ["semantic_search"],
                "filters": ["function", "variable"]
            },
            "SHOW_RELATIONS": {
                "primary": "graph_query",
                "secondary": ["relation_traversal"],
                "filters": []
            }
        }

        return strategies.get(intent, {
            "primary": "semantic_search",
            "secondary": ["exact_match"],
            "filters": []
        })

    def execute_retrieval(self, strategy: Dict[str, Any], entities: List[Dict[str, Any]], context: Dict[str, Any]) -> \
    Dict[str, Any]:
        """执行检索"""
        results = {}

        # 主要检索策略
        primary_strategy = strategy["primary"]
        if primary_strategy == "semantic_search":
            results["primary"] = self.semantic_search(entities, context)
        elif primary_strategy == "exact_match":
            results["primary"] = self.exact_match_search(entities)
        elif primary_strategy == "relation_traversal":
            results["primary"] = self.relation_traversal_search(entities)
        elif primary_strategy == "graph_query":
            results["primary"] = self.graph_query_search(entities)

        # 次要检索策略
        results["secondary"] = {}
        for secondary_strategy in strategy.get("secondary", []):
            if secondary_strategy == "semantic_search":
                results["secondary"]["semantic"] = self.semantic_search(entities, context)
            elif secondary_strategy == "exact_match":
                results["secondary"]["exact"] = self.exact_match_search(entities)

        return results

    def semantic_search(self, entities: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """语义搜索"""
        results = []

        # 使用Qwen API进行语义搜索
        entity_text = ", ".join([e["value"] for e in entities])

        prompt = f"""
        基于以下代码实体进行语义搜索：

        实体: {entity_text}
        上下文: {json.dumps(context, ensure_ascii=False) if context else "无"}

        知识图谱中的节点：
        {json.dumps(list(self.knowledge_graph["nodes"].keys())[:10], ensure_ascii=False)}

        请返回最相关的节点ID列表，用JSON格式：
        {{
            "relevant_nodes": [
                {{
                    "node_id": "节点ID",
                    "relevance_score": 0.9,
                    "reason": "相关原因"
                }}
            ]
        }}
        """

        try:
            response = self.qwen_api.query(prompt)
            search_results = self.parse_search_results(response)
            results.extend(search_results)
        except Exception as e:
            print(f"语义搜索失败: {e}")

        return results

    def exact_match_search(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """精确匹配搜索"""
        results = []

        for entity in entities:
            entity_value = entity["value"]

            # 在节点名称中搜索
            for node_id, node_info in self.knowledge_graph["nodes"].items():
                node_name = node_info.get("name", "")
                if entity_value.lower() in node_name.lower():
                    results.append({
                        "node_id": node_id,
                        "match_type": "exact",
                        "score": 1.0,
                        "reason": f"名称匹配: {node_name}"
                    })

        return results

    def relation_traversal_search(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """关系遍历搜索"""
        results = []

        for entity in entities:
            entity_value = entity["value"]

            # 找到相关节点
            related_nodes = self.find_related_nodes(entity_value)
            results.extend(related_nodes)

        return results

    def graph_query_search(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """图查询搜索"""
        results = []

        # 这里可以实现更复杂的图查询
        # 暂时返回空结果
        return results

    def find_related_nodes(self, entity: str) -> List[Dict[str, Any]]:
        """找到相关节点"""
        related_nodes = []

        # 在知识图谱中查找相关节点
        for node_id, node_info in self.knowledge_graph["nodes"].items():
            node_name = node_info.get("name", "")
            if entity.lower() in node_name.lower():
                # 找到该节点的所有关系
                relations = self.get_node_relations(node_id)
                related_nodes.extend(relations)

        return related_nodes

    def get_node_relations(self, node_id: str) -> List[Dict[str, Any]]:
        """获取节点关系"""
        relations = []

        for edge in self.knowledge_graph["edges"]:
            if edge["source"] == node_id:
                relations.append({
                    "node_id": edge["target"],
                    "relation_type": edge["type"],
                    "score": 0.8,
                    "reason": f"通过 {edge['type']} 关系关联"
                })
            elif edge["target"] == node_id:
                relations.append({
                    "node_id": edge["source"],
                    "relation_type": edge["type"],
                    "score": 0.8,
                    "reason": f"通过 {edge['type']} 关系关联"
                })

        return relations

    def parse_search_results(self, response: str) -> List[Dict[str, Any]]:
        """解析搜索结果"""
        try:
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                return data.get("relevant_nodes", [])
        except:
            pass

        return []

    def rank_results(self, retrieval_results: Dict[str, Any], intent: str, user_query: str) -> List[Dict[str, Any]]:
        """排序结果"""
        all_results = []

        # 合并主要和次要结果
        if "primary" in retrieval_results:
            all_results.extend(retrieval_results["primary"])

        if "secondary" in retrieval_results:
            for secondary_results in retrieval_results["secondary"].values():
                all_results.extend(secondary_results)

        # 去重
        seen_nodes = set()
        unique_results = []

        for result in all_results:
            node_id = result["node_id"]
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                unique_results.append(result)

        # 根据意图调整排序
        if intent == "FIND_IMPLEMENTATION":
            # 优先返回函数节点
            unique_results.sort(key=lambda x: (
                1 if "function" in x.get("node_id", "").lower() else 0,
                x.get("score", 0)
            ), reverse=True)
        elif intent == "EXPLAIN_FUNCTION":
            # 优先返回有语义信息的节点
            unique_results.sort(key=lambda x: (
                len(self.knowledge_graph["nodes"].get(x["node_id"], {}).get("semantic", {})),
                x.get("score", 0)
            ), reverse=True)
        else:
            # 默认按分数排序
            unique_results.sort(key=lambda x: x.get("score", 0), reverse=True)

        return unique_results[:10]  # 返回前10个结果


def run_stage6_query(stage5_output_file: str, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """运行第六阶段：查询处理"""
    logger.info(f"开始查询处理: {user_query}")
    
    try:
        processor = QueryProcessor(stage5_output_file)
        result = processor.process_query(user_query, context)
        
        logger.info(f"查询处理完成，找到 {result.get('total_results', 0)} 个结果")
        return result
        
    except Exception as e:
        logger.error(f"查询处理失败: {e}")
        return {
            "query": user_query,
            "intent": "GENERAL_QUERY",
            "context": [],
            "total_results": 0,
            "search_enabled": False,
            "error": str(e)
        }