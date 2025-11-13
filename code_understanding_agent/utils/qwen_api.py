# utils/qwen_api.py
import os
import json
import time
import asyncio
from typing import Dict, Any, List, Optional, Generator, AsyncGenerator
import requests
from loguru import logger

from config.settings import settings


class QwenAPI:
    """增强的Qwen API客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or settings.qwen_api_key
        self.base_url = base_url or settings.qwen_base_url
        self.session = requests.Session()
        
        # 设置请求头
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
    
    def query(self, prompt: str, model: str = "qwen-turbo", 
              temperature: float = 0.7, max_tokens: int = 2000,
              system_prompt: str = None) -> str:
        """调用Qwen API"""
        if not self.api_key:
            logger.warning("未设置Qwen API Key，使用模拟响应")
            return self.mock_qwen_response(prompt)
        
        try:
            messages = []
            
            # 添加系统提示
            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })
            
            # 添加用户消息
            messages.append({
                'role': 'user',
                'content': prompt
            })
            
            data = {
                'model': model,
                'input': {
                    'messages': messages
                },
                'parameters': {
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    'top_p': 0.8,
                    'repetition_penalty': 1.1
                }
            }
            
            logger.debug(f"发送Qwen API请求: {model}")
            response = self.session.post(self.base_url, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            
            # 检查响应格式
            if 'output' in result and 'choices' in result['output']:
                content = result['output']['choices'][0]['message']['content']
                logger.debug(f"Qwen API响应成功，长度: {len(content)}")
                return content
            else:
                logger.error(f"Qwen API响应格式异常: {result}")
                return self.mock_qwen_response(prompt)
                
        except requests.exceptions.Timeout:
            logger.error("Qwen API请求超时")
            return self.mock_qwen_response(prompt)
        except requests.exceptions.RequestException as e:
            logger.error(f"Qwen API请求失败: {e}")
            return self.mock_qwen_response(prompt)
        except Exception as e:
            logger.error(f"Qwen API调用异常: {e}")
            return self.mock_qwen_response(prompt)
    
    def stream_query(self, prompt: str, model: str = "qwen-turbo",
                    temperature: float = 0.7, system_prompt: str = None) -> Generator[str, None, None]:
        """流式调用Qwen API"""
        if not self.api_key:
            logger.warning("未设置Qwen API Key，使用模拟流式响应")
            yield from self.mock_stream_response(prompt)
            return
        
        try:
            messages = []
            
            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })
            
            messages.append({
                'role': 'user',
                'content': prompt
            })
            
            data = {
                'model': model,
                'input': {
                    'messages': messages
                },
                'parameters': {
                    'temperature': temperature,
                    'incremental_output': True
                }
            }
            
            response = self.session.post(self.base_url, json=data, stream=True, timeout=60)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        line_data = json.loads(line.decode('utf-8'))
                        if 'output' in line_data and 'choices' in line_data['output']:
                            content = line_data['output']['choices'][0]['message']['content']
                            yield content
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"Qwen流式API调用失败: {e}")
            yield from self.mock_stream_response(prompt)
    
    def analyze_code_function(self, function_info: Dict[str, Any]) -> Dict[str, Any]:
        """分析代码函数"""
        system_prompt = """你是一个专业的C++代码分析专家。请分析给定的函数，提供详细的分析结果。
        
请按照以下JSON格式返回分析结果：
{
    "function_description": "函数的详细描述",
    "parameters": [{"name": "参数名", "type": "参数类型", "description": "参数描述"}],
    "return_value": {"type": "返回类型", "description": "返回值描述"},
    "complexity": "时间复杂度分析",
    "usage_scenarios": ["使用场景1", "使用场景2"],
    "key_algorithms": ["关键算法1", "关键算法2"],
    "potential_issues": ["潜在问题1", "潜在问题2"],
    "optimization_suggestions": ["优化建议1", "优化建议2"]
}"""
        
        prompt = f"""请分析以下C++函数：

文件路径: {function_info.get('file_path', 'Unknown')}
函数名: {function_info.get('name', 'Unknown')}
所属类: {function_info.get('class_name', 'None')}

函数代码:
```cpp
{function_info.get('content', '')}
```

请提供详细的分析结果。"""
        
        try:
            response = self.query(prompt, system_prompt=system_prompt)
            # 尝试解析JSON响应
            if response.strip().startswith('{'):
                return json.loads(response)
            else:
                # 如果不是JSON格式，包装成标准格式
                return {
                    "function_description": response,
                    "parameters": [],
                    "return_value": {"type": "unknown", "description": ""},
                    "complexity": "未分析",
                    "usage_scenarios": [],
                    "key_algorithms": [],
                    "potential_issues": [],
                    "optimization_suggestions": []
                }
        except Exception as e:
            logger.error(f"函数分析失败: {e}")
            return self.get_default_function_analysis()
    
    def analyze_code_class(self, class_info: Dict[str, Any]) -> Dict[str, Any]:
        """分析代码类"""
        system_prompt = """你是一个专业的C++代码分析专家。请分析给定的类，提供详细的分析结果。

请按照以下JSON格式返回分析结果：
{
    "class_description": "类的详细描述",
    "design_patterns": ["设计模式1", "设计模式2"],
    "key_members": [{"name": "成员名", "type": "成员类型", "description": "成员描述"}],
    "key_methods": [{"name": "方法名", "description": "方法描述"}],
    "inheritance": {"base_classes": ["基类1"], "derived_classes": ["派生类1"]},
    "usage_recommendations": ["使用建议1", "使用建议2"],
    "potential_improvements": ["改进建议1", "改进建议2"]
}"""
        
        prompt = f"""请分析以下C++类：

文件路径: {class_info.get('file_path', 'Unknown')}
类名: {class_info.get('name', 'Unknown')}

类声明:
```cpp
{class_info.get('declaration', '')}
```

请提供详细的分析结果。"""
        
        try:
            response = self.query(prompt, system_prompt=system_prompt)
            if response.strip().startswith('{'):
                return json.loads(response)
            else:
                return {
                    "class_description": response,
                    "design_patterns": [],
                    "key_members": [],
                    "key_methods": [],
                    "inheritance": {"base_classes": [], "derived_classes": []},
                    "usage_recommendations": [],
                    "potential_improvements": []
                }
        except Exception as e:
            logger.error(f"类分析失败: {e}")
            return self.get_default_class_analysis()
    
    def answer_code_question(self, question: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """回答代码相关问题"""
        system_prompt = """你是一个专业的C++代码助手。基于提供的代码上下文，回答用户的问题。

请按照以下JSON格式返回答案：
{
    "answer": "详细的答案",
    "key_points": ["关键要点1", "关键要点2"],
    "code_examples": [{"description": "示例描述", "code": "示例代码"}],
    "related_functions": ["相关函数1", "相关函数2"],
    "implementation_steps": ["步骤1", "步骤2"],
    "navigation": [{"name": "项目名", "type": "类型", "location": "位置"}]
}"""
        
        # 构建上下文信息
        context_text = ""
        for i, ctx in enumerate(context[:5]):  # 限制上下文数量
            context_text += f"\n--- 上下文 {i+1} ---\n"
            context_text += f"文件: {ctx.get('metadata', {}).get('file_path', 'Unknown')}\n"
            context_text += f"内容:\n{ctx.get('content', '')}\n"
        
        prompt = f"""基于以下代码上下文回答问题：

问题: {question}

代码上下文:
{context_text}

请提供详细的答案。"""
        
        try:
            response = self.query(prompt, system_prompt=system_prompt, max_tokens=3000)
            if response.strip().startswith('{'):
                return json.loads(response)
            else:
                return {
                    "answer": response,
                    "key_points": [],
                    "code_examples": [],
                    "related_functions": [],
                    "implementation_steps": [],
                    "navigation": []
                }
        except Exception as e:
            logger.error(f"问题回答失败: {e}")
            return self.get_default_answer()
    
    def mock_qwen_response(self, prompt: str) -> str:
        """模拟Qwen响应（用于测试）"""
        logger.info(f"模拟Qwen响应，提示长度: {len(prompt)}")
        
        # 基于提示内容生成模拟响应
        if "函数" in prompt or "function" in prompt.lower():
            return json.dumps({
                "function_description": "这是一个示例函数，用于演示代码分析功能",
                "parameters": [{"name": "param1", "type": "int", "description": "示例参数"}],
                "return_value": {"type": "bool", "description": "返回操作是否成功"},
                "complexity": "时间复杂度O(1)",
                "usage_scenarios": ["场景1：基本使用", "场景2：错误处理"],
                "key_algorithms": ["算法1", "算法2"],
                "potential_issues": ["注意空指针", "注意边界条件"],
                "optimization_suggestions": ["可以使用缓存优化", "可以并行处理"]
            }, ensure_ascii=False, indent=2)
        
        elif "类" in prompt or "class" in prompt.lower():
            return json.dumps({
                "class_description": "这是一个示例类，展示了良好的面向对象设计",
                "design_patterns": ["单例模式", "工厂模式"],
                "key_members": [{"name": "member1", "type": "int", "description": "示例成员变量"}],
                "key_methods": [{"name": "method1", "description": "示例方法"}],
                "inheritance": {"base_classes": ["BaseClass"], "derived_classes": []},
                "usage_recommendations": ["建议1：正确初始化", "建议2：及时释放资源"],
                "potential_improvements": ["可以添加更多错误检查", "可以优化内存使用"]
            }, ensure_ascii=False, indent=2)
        
        else:
            return json.dumps({
                "answer": "这是一个示例回答，展示了代码理解智能体的功能",
                "key_points": ["要点1：代码结构清晰", "要点2：性能表现良好"],
                "code_examples": [{"description": "使用示例", "code": "example_function();"}],
                "related_functions": ["related_func1", "related_func2"],
                "implementation_steps": ["步骤1：初始化", "步骤2：处理数据", "步骤3：返回结果"],
                "navigation": [{"name": "ExampleClass", "type": "class", "location": "example.h:10"}]
            }, ensure_ascii=False, indent=2)
    
    def mock_stream_response(self, prompt: str) -> Generator[str, None, None]:
        """模拟流式响应"""
        response = self.mock_qwen_response(prompt)
        words = response.split()
        
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            time.sleep(0.05)  # 模拟流式延迟
    
    def get_default_function_analysis(self) -> Dict[str, Any]:
        """获取默认函数分析结果"""
        return {
            "function_description": "函数分析暂时不可用",
            "parameters": [],
            "return_value": {"type": "unknown", "description": ""},
            "complexity": "未分析",
            "usage_scenarios": [],
            "key_algorithms": [],
            "potential_issues": [],
            "optimization_suggestions": []
        }
    
    def get_default_class_analysis(self) -> Dict[str, Any]:
        """获取默认类分析结果"""
        return {
            "class_description": "类分析暂时不可用",
            "design_patterns": [],
            "key_members": [],
            "key_methods": [],
            "inheritance": {"base_classes": [], "derived_classes": []},
            "usage_recommendations": [],
            "potential_improvements": []
        }
    
    def get_default_answer(self) -> Dict[str, Any]:
        """获取默认答案"""
        return {
            "answer": "抱歉，暂时无法回答这个问题。请检查API配置或稍后重试。",
            "key_points": [],
            "code_examples": [],
            "related_functions": [],
            "implementation_steps": [],
            "navigation": []
        }


# 全局实例
qwen_api = QwenAPI()