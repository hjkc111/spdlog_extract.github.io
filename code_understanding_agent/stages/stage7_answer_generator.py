# stages/stage7_answer_generator.py
import os
import json
from typing import Dict, List, Any
from loguru import logger

from utils.file_utils import load_json
from utils.qwen_api import qwen_api


class AnswerGenerator:
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

    def generate_answer(self, query_processing_result: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """生成答案"""
        logger.info("开始生成答案...")

        context = query_processing_result.get("context", [])
        intent = query_processing_result.get("intent", "GENERAL_QUERY")

        if not context:
            return self.generate_no_results_answer(user_query)

        try:
            # 使用Qwen API生成答案
            answer_data = qwen_api.answer_code_question(user_query, context)
            
            # 添加额外的导航信息
            navigation_info = self.extract_navigation_info(context)
            if navigation_info:
                answer_data["navigation"] = navigation_info
            
            # 添加元数据
            answer_data["metadata"] = {
                "query_intent": intent,
                "results_count": len(context),
                "confidence_score": self.calculate_confidence(context),
                "project_name": self.project_name
            }
            
            logger.info("答案生成完成")
            return answer_data
            
        except Exception as e:
            logger.error(f"答案生成失败: {e}")
            return self.generate_fallback_answer(user_query, context)
    
    def generate_no_results_answer(self, user_query: str) -> Dict[str, Any]:
        """生成无结果答案"""
        return {
            "answer": f"抱歉，我没有找到与 '{user_query}' 相关的代码信息。请尝试使用不同的关键词或更具体的描述。",
            "key_points": [
                "没有找到相关的代码片段",
                "建议尝试不同的搜索关键词",
                "可以尝试更具体的函数名或类名"
            ],
            "code_examples": [],
            "related_functions": [],
            "implementation_steps": [],
            "navigation": []
        }
    
    def generate_fallback_answer(self, user_query: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成回退答案"""
        # 提取一些基本信息
        file_paths = set()
        function_names = set()
        
        for ctx in context[:3]:  # 只看前3个结果
            metadata = ctx.get("metadata", {})
            if metadata.get("file_path"):
                file_paths.add(metadata["file_path"])
            if metadata.get("function_name"):
                function_names.add(metadata["function_name"])
        
        answer = f"基于代码分析，我找到了与 '{user_query}' 相关的代码片段。"
        
        if function_names:
            answer += f" 主要涉及函数：{', '.join(list(function_names)[:3])}。"
        
        if file_paths:
            answer += f" 相关文件：{', '.join(list(file_paths)[:2])}。"
        
        return {
            "answer": answer,
            "key_points": [
                f"找到 {len(context)} 个相关代码片段",
                f"涉及 {len(file_paths)} 个文件",
                f"包含 {len(function_names)} 个函数"
            ],
            "code_examples": [
                {
                    "description": "相关代码片段",
                    "code": context[0].get("content", "")[:200] + "..." if context else ""
                }
            ],
            "related_functions": list(function_names)[:5],
            "implementation_steps": [],
            "navigation": self.extract_navigation_info(context)
        }
    
    def extract_navigation_info(self, context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取导航信息"""
        navigation = []
        
        for ctx in context[:5]:  # 只取前5个
            metadata = ctx.get("metadata", {})
            
            if metadata.get("function_name"):
                navigation.append({
                    "name": metadata["function_name"],
                    "type": "function",
                    "location": f"{metadata.get('file_path', 'unknown')}:{metadata.get('line_start', 0)}"
                })
            elif metadata.get("class_name"):
                navigation.append({
                    "name": metadata["class_name"],
                    "type": "class",
                    "location": f"{metadata.get('file_path', 'unknown')}:{metadata.get('line_start', 0)}"
                })
        
        return navigation
    
    def calculate_confidence(self, context: List[Dict[str, Any]]) -> float:
        """计算置信度分数"""
        if not context:
            return 0.0
        
        # 基于相似度分数计算平均置信度
        similarities = [ctx.get("similarity", 0.0) for ctx in context]
        avg_similarity = sum(similarities) / len(similarities)
        
        # 考虑结果数量的影响
        count_factor = min(len(context) / 5.0, 1.0)  # 5个结果为满分
        
        return min(avg_similarity * count_factor, 1.0)

    def generate_implementation_answer(self, results: List[Dict[str, Any]], user_query: str,
                                       query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成实现相关的答案"""
        primary_result = results[0] if results else None

        if not primary_result:
            return self.generate_no_results_answer(user_query, query_analysis)

        node_id = primary_result["node_id"]
        node_info = self.knowledge_graph["nodes"].get(node_id, {})

        prompt = f"""
        用户想知道如何实现某个功能：

        用户查询: "{user_query}"
        相关代码实体: {node_info.get('name', '未知')}
        代码位置: {node_info.get('location', '未知')}
        语义信息: {json.dumps(node_info.get('semantic', {}), ensure_ascii=False)}

        请生成一个详细的实现说明，包括：
        1. 这个功能的主要实现方式
        2. 关键的函数和类
        3. 实现步骤和算法
        4. 需要注意的技术细节

        请用JSON格式返回：
        {{
            "answer": "详细的实现说明",
            "key_functions": ["函数1", "函数2"],
            "implementation_steps": ["步骤1", "步骤2"],
            "technical_notes": ["注意1", "注意2"],
            "code_examples": ["代码示例1", "代码示例2"]
        }}
        """

        try:
            response = self.qwen_api.query(prompt)
            answer_data = self.parse_answer_response(response)

            # 添加导航信息
            navigation = self.generate_navigation_info([primary_result])
            answer_data["navigation"] = navigation

            return answer_data
        except Exception as e:
            print(f"生成实现答案失败: {e}")
            return self.generate_fallback_answer(results, user_query, "implementation")

    def generate_explanation_answer(self, results: List[Dict[str, Any]], user_query: str,
                                    query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成解释相关的答案"""
        primary_result = results[0] if results else None

        if not primary_result:
            return self.generate_no_results_answer(user_query, query_analysis)

        node_id = primary_result["node_id"]
        node_info = self.knowledge_graph["nodes"].get(node_id, {})

        prompt = f"""
        用户想了解某个代码实体的功能：

        用户查询: "{user_query}"
        代码实体: {node_info.get('name', '未知')}
        类型: {node_info.get('type', '未知')}
        位置: {node_info.get('location', '未知')}
        语义信息: {json.dumps(node_info.get('semantic', {}), ensure_ascii=False)}

        请生成一个详细的解释，包括：
        1. 这个实体的主要功能和作用
        2. 输入输出和副作用
        3. 在项目中的角色
        4. 使用示例和最佳实践

        请用JSON格式返回：
        {{
            "answer": "详细的解释",
            "main_function": "主要功能描述",
            "inputs_outputs": {{
                "inputs": ["输入1", "输入2"],
                "outputs": ["输出1", "输出2"]
            }},
            "project_role": "在项目中的角色",
            "usage_examples": ["示例1", "示例2"],
            "best_practices": ["最佳实践1", "最佳实践2"]
        }}
        """

        try:
            response = self.qwen_api.query(prompt)
            answer_data = self.parse_answer_response(response)

            # 添加相关实体信息
            related_entities = self.get_related_entities([primary_result])
            answer_data["related_entities"] = related_entities

            return answer_data
        except Exception as e:
            print(f"生成解释答案失败: {e}")
            return self.generate_fallback_answer(results, user_query, "explanation")

    def generate_definition_answer(self, results: List[Dict[str, Any]], user_query: str,
                                   query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成定义相关的答案"""
        primary_result = results[0] if results else None

        if not primary_result:
            return self.generate_no_results_answer(user_query, query_analysis)

        node_id = primary_result["node_id"]
        node_info = self.knowledge_graph["nodes"].get(node_id, {})

        prompt = f"""
        用户想找到某个实体的定义：

        用户查询: "{user_query}"
        代码实体: {node_info.get('name', '未知')}
        类型: {node_info.get('type', '未知')}
        位置: {node_info.get('location', '未知')}

        请提供定义信息，包括：
        1. 完整的定义位置
        2. 定义签名（对于函数）或声明（对于类）
        3. 访问权限和修饰符
        4. 定义所在的文件上下文

        请用JSON格式返回：
        {{
            "answer": "定义信息总结",
            "definition_location": "完整的位置信息",
            "signature": "函数签名或类声明",
            "access_modifiers": ["修饰符1", "修饰符2"],
            "file_context": "文件上下文信息",
            "direct_link": "可以直接跳转的链接（如果有）"
        }}
        """

        try:
            response = self.qwen_api.query(prompt)
            answer_data = self.parse_answer_response(response)

            # 添加快捷导航
            answer_data["quick_navigation"] = self.generate_quick_navigation([primary_result])

            return answer_data
        except Exception as e:
            print(f"生成定义答案失败: {e}")
            return self.generate_fallback_answer(results, user_query, "definition")

    def generate_usage_answer(self, results: List[Dict[str, Any]], user_query: str, query_analysis: Dict[str, Any]) -> \
    Dict[str, Any]:
        """生成使用相关的答案"""
        primary_result = results[0] if results else None

        if not primary_result:
            return self.generate_no_results_answer(user_query, query_analysis)

        node_id = primary_result["node_id"]
        node_info = self.knowledge_graph["nodes"].get(node_id, {})

        # 找到使用这个实体的其他实体
        usage_relations = self.find_usage_relations(node_id)

        prompt = f"""
        用户想了解如何使用某个代码实体：

        用户查询: "{user_query}"
        代码实体: {node_info.get('name', '未知')}
        类型: {node_info.get('type', '未知')}
        使用关系: {json.dumps(usage_relations, ensure_ascii=False)}

        请提供使用信息，包括：
        1. 主要的使用方式
        2. 调用示例
        3. 参数说明
        4. 常见的用法模式
        5. 注意事项

        请用JSON格式返回：
        {{
            "answer": "使用说明总结",
            "usage_patterns": ["模式1", "模式2"],
            "call_examples": ["示例1", "示例2"],
            "parameter_guide": "参数说明",
            "common_scenarios": ["场景1", "场景2"],
            "precautions": ["注意1", "注意2"]
        }}
        """

        try:
            response = self.qwen_api.query(prompt)
            answer_data = self.parse_answer_response(response)

            # 添加使用关系图
            answer_data["usage_relationships"] = usage_relations

            return answer_data
        except Exception as e:
            print(f"生成使用答案失败: {e}")
            return self.generate_fallback_answer(results, user_query, "usage")

    def generate_relations_answer(self, results: List[Dict[str, Any]], user_query: str,
                                  query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成关系相关的答案"""
        primary_result = results[0] if results else None

        if not primary_result:
            return self.generate_no_results_answer(user_query, query_analysis)

        node_id = primary_result["node_id"]

        # 找到所有相关关系
        all_relations = self.find_all_relations(node_id)

        prompt = f"""
        用户想了解代码实体之间的关系：

        用户查询: "{user_query}"
        主要实体: {node_id}
        所有关系: {json.dumps(all_relations, ensure_ascii=False)}

        请分析并提供关系信息，包括：
        1. 关系网络概述
        2. 最重要的关系
        3. 依赖关系分析
        4. 架构意义

        请用JSON格式返回：
        {{
            "answer": "关系分析总结",
            "relationship_network": "关系网络描述",
            "key_relationships": ["关系1", "关系2"],
            "dependency_analysis": "依赖分析",
            "architectural_significance": "架构意义",
            "relationship_graph": "关系图描述"
        }}
        """

        try:
            response = self.qwen_api.query(prompt)
            answer_data = self.parse_answer_response(response)

            # 添加关系可视化数据
            answer_data["visualization_data"] = self.generate_visualization_data(node_id, all_relations)

            return answer_data
        except Exception as e:
            print(f"生成关系答案失败: {e}")
            return self.generate_fallback_answer(results, user_query, "relations")

    def generate_general_answer(self, results: List[Dict[str, Any]], user_query: str, query_analysis: Dict[str, Any]) -> \
    Dict[str, Any]:
        """生成通用答案"""
        primary_result = results[0] if results else None

        if not primary_result:
            return self.generate_no_results_answer(user_query, query_analysis)

        node_id = primary_result["node_id"]
        node_info = self.knowledge_graph["nodes"].get(node_id, {})

        prompt = f"""
        用户提出了一个关于代码理解的问题：

        用户查询: "{user_query}"
        相关代码实体: {node_info.get('name', '未知')}
        类型: {node_info.get('type', '未知')}
        位置: {node_info.get('location', '未知')}
        语义信息: {json.dumps(node_info.get('semantic', {}), ensure_ascii=False)}

        请根据查询和代码信息生成一个全面、有用的答案。

        请用JSON格式返回：
        {{
            "answer": "全面的答案",
            "key_points": ["要点1", "要点2"],
            "detailed_explanation": "详细解释",
            "practical_advice": "实践建议",
            "further_reading": "进一步阅读"
        }}
        """

        try:
            response = self.qwen_api.query(prompt)
            answer_data = self.parse_answer_response(response)

            # 添加综合信息
            answer_data["comprehensive_info"] = self.generate_comprehensive_info([primary_result])

            return answer_data
        except Exception as e:
            print(f"生成通用答案失败: {e}")
            return self.generate_fallback_answer(results, user_query, "general")

    def generate_no_results_answer(self, user_query: str, query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成无结果的答案"""
        prompt = f"""
        用户查询没有找到相关结果：

        用户查询: "{user_query}"
        查询分析: {json.dumps(query_analysis, ensure_ascii=False)}

        请生成一个友好的无结果回答，并提供一些建议。

        请用JSON格式返回：
        {{
            "answer": "友好的无结果消息",
            "suggestions": ["建议1", "建议2"],
            "alternative_queries": ["替代查询1", "替代查询2"],
            "helpful_tips": ["提示1", "提示2"]
        }}
        """

        try:
            response = self.qwen_api.query(prompt)
            return self.parse_answer_response(response)
        except Exception as e:
            print(f"生成无结果答案失败: {e}")
            return {
                "answer": "抱歉，没有找到与您的查询相关的结果。",
                "suggestions": [
                    "尝试使用更具体的关键词",
                    "检查代码实体名称的拼写",
                    "描述您想了解的具体功能"
                ],
                "alternative_queries": [],
                "helpful_tips": [
                    "您可以使用函数名、类名或具体功能描述进行搜索"
                ]
            }

    def generate_fallback_answer(self, results: List[Dict[str, Any]], user_query: str, answer_type: str) -> Dict[
        str, Any]:
        """生成回退答案"""
        primary_result = results[0] if results else {}
        node_id = primary_result.get("node_id", "未知")
        node_info = self.knowledge_graph["nodes"].get(node_id, {})

        return {
            "answer": f"基于分析，这里是与 '{user_query}' 相关的信息：",
            "primary_entity": {
                "name": node_info.get("name", "未知"),
                "type": node_info.get("type", "未知"),
                "location": node_info.get("location", "未知")
            },
            "answer_type": answer_type,
            "confidence": "medium",
            "note": "这是一个基于基础分析的答案，完整功能需要AI增强。"
        }

    def find_usage_relations(self, node_id: str) -> List[Dict[str, Any]]:
        """找到使用关系"""
        usage_relations = []

        for edge in self.knowledge_graph["edges"]:
            if edge["target"] == node_id and edge["type"] in ["calls", "uses"]:
                source_node = self.knowledge_graph["nodes"].get(edge["source"], {})
                usage_relations.append({
                    "user": edge["source"],
                    "user_name": source_node.get("name", "未知"),
                    "relation_type": edge["type"],
                    "context": edge.get("properties", {})
                })

        return usage_relations

    def find_all_relations(self, node_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """找到所有关系"""
        relations = {
            "outgoing": [],
            "incoming": []
        }

        for edge in self.knowledge_graph["edges"]:
            if edge["source"] == node_id:
                target_node = self.knowledge_graph["nodes"].get(edge["target"], {})
                relations["outgoing"].append({
                    "target": edge["target"],
                    "target_name": target_node.get("name", "未知"),
                    "relation_type": edge["type"],
                    "properties": edge.get("properties", {})
                })
            elif edge["target"] == node_id:
                source_node = self.knowledge_graph["nodes"].get(edge["source"], {})
                relations["incoming"].append({
                    "source": edge["source"],
                    "source_name": source_node.get("name", "未知"),
                    "relation_type": edge["type"],
                    "properties": edge.get("properties", {})
                })

        return relations

    def generate_navigation_info(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成导航信息"""
        navigation = []

        for result in results[:3]:  # 前3个结果
            node_id = result["node_id"]
            node_info = self.knowledge_graph["nodes"].get(node_id, {})

            navigation.append({
                "node_id": node_id,
                "name": node_info.get("name", "未知"),
                "type": node_info.get("type", "未知"),
                "location": node_info.get("location", "未知"),
                "relevance_score": result.get("score", 0)
            })

        return navigation

    def get_related_entities(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """获取相关实体"""
        related_entities = []

        for result in results[:5]:
            node_id = result["node_id"]
            relations = self.find_all_relations(node_id)

            # 添加入边关系实体
            for incoming in relations["incoming"][:3]:
                related_entities.append({
                    "entity_id": incoming["source"],
                    "entity_name": incoming["source_name"],
                    "relation": f"被 {incoming['relation_type']}",
                    "type": "incoming"
                })

            # 添加出边关系实体
            for outgoing in relations["outgoing"][:3]:
                related_entities.append({
                    "entity_id": outgoing["target"],
                    "entity_name": outgoing["target_name"],
                    "relation": f"{outgoing['relation_type']}",
                    "type": "outgoing"
                })

        return related_entities

    def generate_quick_navigation(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成快捷导航"""
        primary_result = results[0] if results else {}
        node_id = primary_result.get("node_id")

        if not node_id:
            return {}

        node_info = self.knowledge_graph["nodes"].get(node_id, {})

        return {
            "jump_to_definition": node_info.get("location", ""),
            "related_functions": self.find_related_functions(node_id),
            "quick_actions": [
                {"action": "view_source", "description": "查看源代码"},
                {"action": "view_calls", "description": "查看调用关系"},
                {"action": "view_usage", "description": "查看使用示例"}
            ]
        }

    def find_related_functions(self, node_id: str) -> List[str]:
        """找到相关函数"""
        related_functions = []
        relations = self.find_all_relations(node_id)

        for relation in relations["outgoing"] + relations["incoming"]:
            related_id = relation.get("target") or relation.get("source")
            related_node = self.knowledge_graph["nodes"].get(related_id, {})
            if related_node.get("type") == "function":
                related_functions.append(related_node.get("name", related_id))

        return list(set(related_functions))[:5]  # 去重并限制数量

    def generate_visualization_data(self, node_id: str, relations: Dict[str, Any]) -> Dict[str, Any]:
        """生成可视化数据"""
        return {
            "center_node": {
                "id": node_id,
                "name": self.knowledge_graph["nodes"].get(node_id, {}).get("name", "未知"),
                "type": self.knowledge_graph["nodes"].get(node_id, {}).get("type", "未知")
            },
            "related_nodes": [
                {
                    "id": rel.get("source") or rel.get("target"),
                    "name": rel.get("source_name") or rel.get("target_name"),
                    "relation": rel["relation_type"],
                    "direction": "incoming" if "source" in rel else "outgoing"
                }
                for rel_type in relations.values()
                for rel in rel_type[:10]  # 限制数量
            ]
        }

    def generate_comprehensive_info(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成综合信息"""
        primary_result = results[0] if results else {}
        node_id = primary_result.get("node_id")

        if not node_id:
            return {}

        node_info = self.knowledge_graph["nodes"].get(node_id, {})
        relations = self.find_all_relations(node_id)

        return {
            "entity_overview": {
                "name": node_info.get("name", "未知"),
                "type": node_info.get("type", "未知"),
                "location": node_info.get("location", "未知"),
                "semantic_info": node_info.get("semantic", {})
            },
            "relationship_summary": {
                "total_relations": len(relations["incoming"]) + len(relations["outgoing"]),
                "incoming_count": len(relations["incoming"]),
                "outgoing_count": len(relations["outgoing"])
            },
            "key_metrics": {
                "complexity": node_info.get("semantic", {}).get("complexity_analysis", "未知"),
                "importance": self.estimate_importance(node_id, relations)
            }
        }

    def estimate_importance(self, node_id: str, relations: Dict[str, Any]) -> str:
        """估计重要性"""
        total_relations = len(relations["incoming"]) + len(relations["outgoing"])

        if total_relations > 10:
            return "high"
        elif total_relations > 5:
            return "medium"
        else:
            return "low"

    def calculate_confidence(self, results: List[Dict[str, Any]]) -> float:
        """计算置信度"""
        if not results:
            return 0.0

        # 基于结果数量和分数计算置信度
        scores = [result.get("score", 0) for result in results[:3]]
        avg_score = sum(scores) / len(scores) if scores else 0

        # 基于结果数量调整
        count_factor = min(len(results) / 5, 1.0)  # 最多5个结果

        return (avg_score * 0.7 + count_factor * 0.3)

    def parse_answer_response(self, response: str) -> Dict[str, Any]:
        """解析答案响应"""
        try:
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except Exception as e:
            print(f"解析答案响应失败: {e}")

        return {
            "answer": "抱歉，生成答案时出现错误。",
            "error": "解析响应失败",
            "raw_response": response[:200]  # 保留部分原始响应用于调试
        }


def run_stage7_answer(stage5_output_file: str, query_processing_result: Dict[str, Any], user_query: str) -> Dict[str, Any]:
    """运行第七阶段：答案生成"""
    logger.info("开始运行阶段7：答案生成")
    
    try:
        generator = AnswerGenerator(stage5_output_file)
        answer = generator.generate_answer(query_processing_result, user_query)
        
        logger.info("阶段7完成：答案生成成功")
        return answer
        
    except Exception as e:
        logger.error(f"阶段7执行失败: {e}")
        return {
            "answer": f"抱歉，生成答案时出现错误: {str(e)}",
            "key_points": [],
            "code_examples": [],
            "related_functions": [],
            "implementation_steps": [],
            "navigation": [],
            "error": str(e)
        }