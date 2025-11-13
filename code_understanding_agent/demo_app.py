#!/usr/bin/env python3
# demo_app.py
"""
C++ 代码理解智能体演示版本
简化版本，用于展示核心功能
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List

import streamlit as st
import requests
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from utils.qwen_api import qwen_api


# 页面配置
st.set_page_config(
    page_title="C++ 代码理解智能体 - 演示版",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .demo-box {
        background-color: #f0f8ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """初始化会话状态"""
    if 'demo_mode' not in st.session_state:
        st.session_state.demo_mode = True
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []


def show_header():
    """显示页面头部"""
    st.markdown('<div class="main-header">🤖 C++ 代码理解智能体 - 演示版</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="demo-box">
        <h4>🎯 演示功能</h4>
        <ul>
            <li>🔍 <strong>智能问答</strong>：基于预设的代码知识库回答问题</li>
            <li>🧠 <strong>代码理解</strong>：展示AI如何理解和分析C++代码</li>
            <li>📊 <strong>功能演示</strong>：展示完整系统的核心能力</li>
            <li>⚡ <strong>即时响应</strong>：无需实际分析项目即可体验</li>
        </ul>
        <p><strong>注意</strong>：这是演示版本，使用模拟数据展示功能。完整版本支持实际的C++项目分析。</p>
    </div>
    """, unsafe_allow_html=True)


def show_sidebar():
    """显示侧边栏"""
    with st.sidebar:
        st.header("⚙️ 演示配置")
        
        # API配置状态
        st.subheader("🔑 API状态")
        qwen_status = "✅ 已配置" if settings.qwen_api_key else "❌ 使用模拟响应"
        st.write(f"Qwen API: {qwen_status}")
        
        # 演示模式说明
        st.subheader("🎭 演示模式")
        st.write("当前运行在演示模式下")
        st.write("- 使用预设的代码示例")
        st.write("- 模拟智能分析结果")
        st.write("- 展示核心功能特性")
        
        # 示例项目信息
        st.subheader("📁 示例项目")
        st.write("项目名称: spdlog")
        st.write("类型: C++ 日志库")
        st.write("文件数: 45")
        st.write("函数数: 128")
        st.write("类数: 23")


def get_demo_context():
    """获取演示用的代码上下文"""
    return [
        {
            "id": "logger_class_1",
            "content": """
class logger {
public:
    logger(std::string name, std::vector<sink_ptr> sinks);
    
    void info(const std::string& msg);
    void warn(const std::string& msg);
    void error(const std::string& msg);
    void debug(const std::string& msg);
    
    void set_level(level::level_enum level);
    level::level_enum level() const;
    
private:
    std::string name_;
    std::vector<sink_ptr> sinks_;
    level::level_enum level_;
};
            """,
            "metadata": {
                "file_path": "include/spdlog/logger.h",
                "class_name": "logger",
                "chunk_type": "class",
                "line_start": 15,
                "line_end": 35
            },
            "similarity": 0.95
        },
        {
            "id": "info_function_1",
            "content": """
void logger::info(const std::string& msg) {
    if (should_log(level::info)) {
        log(level::info, msg);
    }
}

void logger::log(level::level_enum lvl, const std::string& msg) {
    if (!should_log(lvl)) {
        return;
    }
    
    auto formatted = formatter_->format(msg, lvl);
    for (auto& sink : sinks_) {
        sink->log(formatted);
    }
}
            """,
            "metadata": {
                "file_path": "src/logger.cpp",
                "function_name": "info",
                "chunk_type": "function",
                "line_start": 45,
                "line_end": 62,
                "complexity": 3
            },
            "similarity": 0.88
        },
        {
            "id": "sink_interface_1",
            "content": """
class sink {
public:
    virtual ~sink() = default;
    virtual void log(const log_msg& msg) = 0;
    virtual void flush() = 0;
    virtual void set_pattern(const std::string& pattern) = 0;
};

class file_sink : public sink {
public:
    file_sink(const std::string& filename);
    void log(const log_msg& msg) override;
    void flush() override;
    
private:
    std::ofstream file_;
};
            """,
            "metadata": {
                "file_path": "include/spdlog/sinks/sink.h",
                "class_name": "sink",
                "chunk_type": "class",
                "line_start": 20,
                "line_end": 40
            },
            "similarity": 0.82
        }
    ]


def show_demo_chat():
    """显示演示聊天界面"""
    st.markdown("## 💬 智能问答演示")
    
    # 预设问题
    st.subheader("🎯 试试这些问题")
    demo_questions = [
        "spdlog库的主要功能是什么？",
        "Logger类是如何实现的？",
        "如何使用info函数记录日志？",
        "有哪些不同类型的sink？",
        "如何设置日志级别？"
    ]
    
    cols = st.columns(len(demo_questions))
    for i, question in enumerate(demo_questions):
        with cols[i % 3]:  # 每行3个按钮
            if st.button(question, key=f"demo_q_{i}"):
                process_demo_question(question)
    
    # 聊天历史显示
    if st.session_state.chat_history:
        st.subheader("📝 对话历史")
        for i, (question, answer) in enumerate(st.session_state.chat_history):
            with st.expander(f"❓ {question}", expanded=(i == len(st.session_state.chat_history) - 1)):
                st.write("**回答：**")
                st.write(answer.get('answer', ''))
                
                if answer.get('key_points'):
                    st.write("**关键要点：**")
                    for point in answer['key_points']:
                        st.write(f"• {point}")
                
                if answer.get('code_examples'):
                    st.write("**代码示例：**")
                    for example in answer['code_examples']:
                        st.write(f"**{example.get('description', '')}**")
                        st.code(example.get('code', ''), language='cpp')
                
                if answer.get('navigation'):
                    st.write("**相关位置：**")
                    for nav in answer['navigation']:
                        st.write(f"• {nav.get('name', '')} ({nav.get('type', '')}) - {nav.get('location', '')}")
    
    # 自定义问题输入
    st.subheader("❓ 自定义问题")
    user_question = st.text_input("请输入您的问题:", key="demo_input")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🚀 提问", type="primary"):
            if user_question:
                process_demo_question(user_question)
    
    with col2:
        if st.button("🗑️ 清空历史"):
            st.session_state.chat_history = []
            st.rerun()


def process_demo_question(question: str):
    """处理演示问题"""
    with st.spinner("🤔 AI正在思考..."):
        try:
            # 获取演示上下文
            context = get_demo_context()
            
            # 使用Qwen API生成答案（如果可用）
            answer = qwen_api.answer_code_question(question, context)
            
            # 添加演示特定的导航信息
            if not answer.get('navigation'):
                answer['navigation'] = [
                    {"name": "logger", "type": "class", "location": "include/spdlog/logger.h:15"},
                    {"name": "info", "type": "function", "location": "src/logger.cpp:45"},
                    {"name": "sink", "type": "class", "location": "include/spdlog/sinks/sink.h:20"}
                ]
            
            # 添加到聊天历史
            st.session_state.chat_history.append((question, answer))
            
            # 重新运行以显示新消息
            st.rerun()
            
        except Exception as e:
            st.error(f"处理问题时出错: {str(e)}")


def show_demo_features():
    """显示演示功能"""
    st.markdown("## 🎯 核心功能演示")
    
    tab1, tab2, tab3 = st.tabs(["📊 项目分析", "🔍 代码搜索", "📈 统计信息"])
    
    with tab1:
        st.subheader("项目分析结果")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("文件数量", "45", "5")
        with col2:
            st.metric("函数数量", "128", "12")
        with col3:
            st.metric("类数量", "23", "3")
        with col4:
            st.metric("代码行数", "8,542", "234")
        
        st.subheader("主要组件")
        components = [
            {"name": "logger", "type": "核心类", "description": "主要的日志记录器类"},
            {"name": "sink", "type": "接口", "description": "日志输出目标的抽象接口"},
            {"name": "formatter", "type": "格式化器", "description": "日志消息格式化组件"},
            {"name": "level", "type": "枚举", "description": "日志级别定义"}
        ]
        
        for comp in components:
            with st.expander(f"📦 {comp['name']} - {comp['type']}"):
                st.write(comp['description'])
    
    with tab2:
        st.subheader("语义搜索演示")
        
        search_query = st.text_input("搜索代码:", placeholder="例如：如何记录错误日志")
        
        if search_query:
            st.write("**搜索结果：**")
            
            # 模拟搜索结果
            results = [
                {
                    "title": "error函数实现",
                    "file": "src/logger.cpp",
                    "similarity": "95%",
                    "preview": "void logger::error(const std::string& msg) { log(level::err, msg); }"
                },
                {
                    "title": "错误级别定义",
                    "file": "include/spdlog/level.h", 
                    "similarity": "87%",
                    "preview": "enum level_enum { trace = 0, debug = 1, info = 2, warn = 3, err = 4, critical = 5 };"
                }
            ]
            
            for result in results:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{result['title']}** - {result['file']}")
                        st.code(result['preview'], language='cpp')
                    with col2:
                        st.metric("相似度", result['similarity'])
    
    with tab3:
        st.subheader("项目统计")
        
        # 模拟统计图表
        import pandas as pd
        
        # 文件类型分布
        file_types = pd.DataFrame({
            '文件类型': ['.h', '.hpp', '.cpp', '.cc'],
            '数量': [25, 8, 10, 2]
        })
        
        st.write("**文件类型分布**")
        st.bar_chart(file_types.set_index('文件类型'))
        
        # 复杂度分布
        complexity_data = pd.DataFrame({
            '复杂度范围': ['1-5', '6-10', '11-20', '21+'],
            '函数数量': [45, 38, 32, 13]
        })
        
        st.write("**函数复杂度分布**")
        st.bar_chart(complexity_data.set_index('复杂度范围'))


def show_system_info():
    """显示系统信息"""
    st.markdown("## ℹ️ 系统信息")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔧 配置信息")
        st.write(f"**系统**: {settings.llvm_path}")
        st.write(f"**Clang可用**: {'✅' if os.path.exists(settings.clang_library_path) else '❌'}")
        st.write(f"**API配置**: {'✅' if settings.qwen_api_key else '❌ 演示模式'}")
        st.write(f"**嵌入模型**: {settings.embedding_model}")
    
    with col2:
        st.subheader("📋 功能状态")
        st.write("**代码解析**: 🎭 演示模式")
        st.write("**语义搜索**: 🎭 演示模式") 
        st.write("**智能问答**: ✅ 可用")
        st.write("**向量数据库**: 🎭 演示模式")


def main():
    """主函数"""
    initialize_session_state()
    show_header()
    show_sidebar()
    
    # 主要内容区域
    tab1, tab2, tab3 = st.tabs(["💬 智能问答", "🎯 功能演示", "ℹ️ 系统信息"])
    
    with tab1:
        show_demo_chat()
    
    with tab2:
        show_demo_features()
    
    with tab3:
        show_system_info()
    
    # 底部信息
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666;">
        <p>🤖 C++ 代码理解智能体 - 演示版本</p>
        <p>完整版本支持实际的C++项目分析、向量搜索和知识图谱构建</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()