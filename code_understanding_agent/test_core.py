#!/usr/bin/env python3
# test_core.py
"""
测试核心功能
"""

import os
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from utils.qwen_api import qwen_api


def test_config():
    """测试配置"""
    print("=== 配置测试 ===")
    from config.settings import PROJECT_ROOT, DATA_DIR
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"数据目录: {DATA_DIR}")
    print(f"Qwen API Key: {'已设置' if settings.qwen_api_key else '未设置'}")
    print(f"嵌入模型: {settings.embedding_model}")
    print(f"Clang库路径: {settings.clang_library_path}")
    print(f"Clang库存在: {os.path.exists(settings.clang_library_path)}")
    print()


def test_qwen_api():
    """测试Qwen API"""
    print("=== Qwen API测试 ===")
    
    test_question = "什么是C++中的智能指针？"
    print(f"测试问题: {test_question}")
    
    try:
        response = qwen_api.query(test_question)
        print(f"响应长度: {len(response)}")
        print(f"响应预览: {response[:200]}...")
        
        # 测试代码分析功能
        print("\n--- 测试代码分析功能 ---")
        function_info = {
            "name": "test_function",
            "file_path": "test.cpp",
            "content": "void test_function() { std::cout << \"Hello World\" << std::endl; }",
            "line_start": 1,
            "line_end": 3
        }
        
        analysis = qwen_api.analyze_code_function(function_info)
        print(f"函数分析结果: {json.dumps(analysis, ensure_ascii=False, indent=2)}")
        
    except Exception as e:
        print(f"API测试失败: {e}")
    
    print()


def test_file_structure():
    """测试文件结构"""
    print("=== 文件结构测试 ===")
    
    from config.settings import DATA_DIR, PROCESSED_DIR, CACHE_DIR, EMBEDDINGS_DIR, KNOWLEDGE_GRAPH_DIR, LOGS_DIR
    
    required_dirs = [
        DATA_DIR,
        PROCESSED_DIR,
        CACHE_DIR,
        EMBEDDINGS_DIR,
        KNOWLEDGE_GRAPH_DIR,
        LOGS_DIR
    ]
    
    for dir_path in required_dirs:
        exists = dir_path.exists()
        print(f"{dir_path}: {'✅' if exists else '❌'}")
        if not exists:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"  已创建目录: {dir_path}")
            except Exception as e:
                print(f"  创建目录失败: {e}")
    
    print()


def test_demo_functionality():
    """测试演示功能"""
    print("=== 演示功能测试 ===")
    
    # 模拟代码上下文
    demo_context = [
        {
            "id": "test_1",
            "content": "class Logger { public: void info(const std::string& msg); };",
            "metadata": {
                "file_path": "logger.h",
                "class_name": "Logger",
                "chunk_type": "class"
            },
            "similarity": 0.9
        }
    ]
    
    test_questions = [
        "Logger类的作用是什么？",
        "如何使用info函数？",
        "这个代码的主要功能是什么？"
    ]
    
    for question in test_questions:
        print(f"问题: {question}")
        try:
            answer = qwen_api.answer_code_question(question, demo_context)
            print(f"回答: {answer.get('answer', '无回答')[:100]}...")
            print(f"关键点数量: {len(answer.get('key_points', []))}")
            print()
        except Exception as e:
            print(f"回答生成失败: {e}")
            print()


def main():
    """主函数"""
    print("🤖 C++ 代码理解智能体 - 核心功能测试")
    print("=" * 60)
    
    test_config()
    test_file_structure()
    test_qwen_api()
    test_demo_functionality()
    
    print("✅ 核心功能测试完成")
    print("\n💡 提示:")
    print("- 如果Qwen API未配置，系统将使用模拟响应")
    print("- 演示版本可以在没有完整依赖的情况下运行")
    print("- 完整功能需要安装所有依赖包")


if __name__ == "__main__":
    main()