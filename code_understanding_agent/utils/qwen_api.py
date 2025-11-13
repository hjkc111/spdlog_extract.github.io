# utils/qwen_api.py
import os
import requests
import json
from typing import Dict, Any


class QwenAPI:
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv('QWEN_API_KEY')
        self.base_url = base_url or os.getenv('QWEN_BASE_URL',
                                              'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation')

    def query(self, prompt: str, model: str = "qwen-turbo", temperature: float = 0.7) -> str:
        """调用Qwen API"""
        if not self.api_key:
            return self.mock_qwen_response(prompt)

        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                'model': model,
                'input': {
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ]
                },
                'parameters': {
                    'temperature': temperature
                }
            }

            response = requests.post(self.base_url, headers=headers, json=data)
            response.raise_for_status()

            result = response.json()
            return result['output']['choices'][0]['message']['content']

        except Exception as e:
            print(f"Qwen API调用失败: {e}")
            return self.mock_qwen_response(prompt)

    def mock_qwen_response(self, prompt: str) -> str:
        """模拟Qwen响应（用于测试）"""
        print(f"模拟Qwen响应，提示: {prompt[:100]}...")

        # 基于提示内容生成模拟响应
        if "函数" in prompt and "实现" in prompt:
            return '''
            {
                "function_description": "这是一个示例函数的实现",
                "usage_scenarios": ["场景1", "场景2"],
                "key_algorithms": ["算法1", "算法2"],
                "complexity_analysis": "时间复杂度O(n)"
            }
            '''
        elif "类" in prompt and "语义" in prompt:
            return '''
            {
                "class_description": "这是一个示例类的描述",
                "design_patterns": ["单例模式", "工厂模式"],
                "key_members": ["成员1", "成员2"],
                "usage_recommendations": ["建议1", "建议2"]
            }
            '''
        else:
            return '''
            {
                "answer": "这是一个示例回答",
                "key_points": ["要点1", "要点2"],
                "detailed_explanation": "详细解释内容"
            }
            '''