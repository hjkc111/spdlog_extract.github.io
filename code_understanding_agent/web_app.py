# web_app.py
import streamlit as st
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List
import plotly.graph_objects as go
import plotly.express as px
from streamlit_chat import message
from streamlit_ace import st_ace

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from utils.qwen_api import qwen_api
from utils.vector_db import vector_db
from stages.stage1_project_parser import run_stage1
from stages.stage2_symbol_extractor import run_stage2
from stages.stage3_relation_builder import run_stage3
from stages.stage4_knowledge_graph import run_stage4
from stages.stage5_semantic_embedder import run_stage5
from stages.stage6_query_processor import run_stage6_query
from stages.stage7_answer_generator import run_stage7_answer


# 页面配置
st.set_page_config(
    page_title="C++ 代码理解智能体",
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
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #ff7f0e;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #f0f2f6;
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
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """初始化会话状态"""
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    if 'project_data' not in st.session_state:
        st.session_state.project_data = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'current_project_path' not in st.session_state:
        st.session_state.current_project_path = None


def show_header():
    """显示页面头部"""
    st.markdown('<div class="main-header">🤖 C++ 代码理解智能体</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <h4>🎯 功能特点</h4>
        <ul>
            <li>🔍 <strong>深度代码分析</strong>：基于Clang AST的精确C++代码解析</li>
            <li>🧠 <strong>智能问答</strong>：基于RAG的代码理解和问答系统</li>
            <li>📊 <strong>可视化展示</strong>：代码结构和关系的图形化展示</li>
            <li>⚡ <strong>实时交互</strong>：流式对话和即时响应</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


def show_sidebar():
    """显示侧边栏"""
    with st.sidebar:
        st.header("⚙️ 配置")
        
        # API配置状态
        st.subheader("🔑 API状态")
        qwen_status = "✅ 已配置" if settings.qwen_api_key else "❌ 未配置"
        st.write(f"Qwen API: {qwen_status}")
        
        # 系统信息
        st.subheader("💻 系统信息")
        st.write(f"系统: {settings.llvm_path}")
        clang_status = "✅ 可用" if os.path.exists(settings.clang_library_path) else "❌ 不可用"
        st.write(f"Clang: {clang_status}")
        
        # 向量数据库状态
        st.subheader("🗄️ 数据库状态")
        try:
            stats = vector_db.get_collection_stats()
            st.write(f"代码块数量: {stats.get('total_chunks', 0)}")
            st.write(f"嵌入模型: {stats.get('embedding_model', 'Unknown')}")
        except:
            st.write("数据库未初始化")
        
        # 清理选项
        st.subheader("🧹 维护")
        if st.button("清空向量数据库"):
            if vector_db.clear_collection():
                st.success("向量数据库已清空")
            else:
                st.error("清空失败")


def show_project_analysis():
    """显示项目分析页面"""
    st.markdown('<div class="section-header">📁 项目分析</div>', unsafe_allow_html=True)
    
    # 项目路径输入
    project_path = st.text_input(
        "请输入C++项目路径:",
        value=st.session_state.get('current_project_path', ''),
        help="输入要分析的C++项目的完整路径"
    )
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        analyze_button = st.button("🔍 开始分析", type="primary")
    
    with col2:
        if st.session_state.analysis_complete:
            st.success("✅ 分析完成")
    
    if analyze_button and project_path:
        if not os.path.exists(project_path):
            st.error("❌ 项目路径不存在")
            return
        
        st.session_state.current_project_path = project_path
        
        # 显示进度
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # 阶段1: 项目解析
            status_text.text("🎯 阶段1: 项目解析...")
            progress_bar.progress(0.1)
            stage1_output = run_stage1(project_path)
            
            # 阶段2: 符号提取
            status_text.text("🎯 阶段2: 符号提取...")
            progress_bar.progress(0.3)
            stage2_output = run_stage2(stage1_output)
            
            # 阶段3: 关系构建
            status_text.text("🎯 阶段3: 关系构建...")
            progress_bar.progress(0.5)
            stage3_output = run_stage3(stage2_output)
            
            # 阶段4: 知识图谱
            status_text.text("🎯 阶段4: 知识图谱构建...")
            progress_bar.progress(0.7)
            stage4_output = run_stage4(stage3_output)
            
            # 阶段5: 语义嵌入
            status_text.text("🎯 阶段5: 语义嵌入...")
            progress_bar.progress(0.9)
            stage5_output = run_stage5(stage4_output)
            
            progress_bar.progress(1.0)
            status_text.text("✅ 分析完成!")
            
            # 保存结果到会话状态
            st.session_state.analysis_complete = True
            st.session_state.project_data = stage5_output
            
            st.success("🎉 项目分析完成！现在可以开始提问了。")
            
        except Exception as e:
            st.error(f"❌ 分析过程中出错: {str(e)}")
            progress_bar.progress(0)
            status_text.text("分析失败")


def show_project_overview():
    """显示项目概览"""
    if not st.session_state.analysis_complete:
        st.info("请先完成项目分析")
        return
    
    st.markdown('<div class="section-header">📊 项目概览</div>', unsafe_allow_html=True)
    
    try:
        # 加载项目数据
        if st.session_state.project_data and os.path.exists(st.session_state.project_data):
            with open(st.session_state.project_data, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 统计信息
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("文件数量", len(data.get('files', [])))
            
            with col2:
                total_functions = sum(len(file_data.get('functions', [])) for file_data in data.get('files', []))
                st.metric("函数数量", total_functions)
            
            with col3:
                total_classes = sum(len(file_data.get('classes', [])) for file_data in data.get('files', []))
                st.metric("类数量", total_classes)
            
            with col4:
                total_lines = sum(file_data.get('line_count', 0) for file_data in data.get('files', []))
                st.metric("总行数", total_lines)
            
            # 文件类型分布
            st.subheader("📁 文件类型分布")
            file_extensions = {}
            for file_data in data.get('files', []):
                ext = Path(file_data.get('path', '')).suffix
                file_extensions[ext] = file_extensions.get(ext, 0) + 1
            
            if file_extensions:
                fig = px.pie(
                    values=list(file_extensions.values()),
                    names=list(file_extensions.keys()),
                    title="文件类型分布"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # 复杂度分析
            st.subheader("📈 复杂度分析")
            complexities = []
            for file_data in data.get('files', []):
                for func in file_data.get('functions', []):
                    if 'complexity' in func:
                        complexities.append(func['complexity'])
            
            if complexities:
                fig = px.histogram(
                    x=complexities,
                    title="函数复杂度分布",
                    labels={'x': '复杂度', 'y': '函数数量'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
    except Exception as e:
        st.error(f"加载项目数据失败: {str(e)}")


def show_chat_interface():
    """显示聊天界面"""
    st.markdown('<div class="section-header">💬 智能问答</div>', unsafe_allow_html=True)
    
    if not st.session_state.analysis_complete:
        st.info("请先完成项目分析后再开始提问")
        return
    
    # 聊天历史显示
    chat_container = st.container()
    
    with chat_container:
        for i, (question, answer) in enumerate(st.session_state.chat_history):
            message(question, is_user=True, key=f"user_{i}")
            message(answer.get('answer', ''), key=f"bot_{i}")
            
            # 显示额外信息
            if answer.get('key_points'):
                with st.expander("📌 关键要点"):
                    for point in answer['key_points']:
                        st.write(f"• {point}")
            
            if answer.get('code_examples'):
                with st.expander("💻 代码示例"):
                    for example in answer['code_examples']:
                        st.write(f"**{example.get('description', '')}**")
                        st.code(example.get('code', ''), language='cpp')
            
            if answer.get('navigation'):
                with st.expander("📍 相关位置"):
                    for nav in answer['navigation']:
                        st.write(f"• {nav.get('name', '')} ({nav.get('type', '')}) - {nav.get('location', '')}")
    
    # 问题输入
    st.markdown("---")
    
    # 预设问题
    st.subheader("🎯 常见问题")
    preset_questions = [
        "这个项目的主要功能是什么？",
        "有哪些重要的类和函数？",
        "代码的整体架构是怎样的？",
        "有哪些潜在的性能问题？",
        "如何使用这个库？"
    ]
    
    cols = st.columns(len(preset_questions))
    for i, question in enumerate(preset_questions):
        with cols[i]:
            if st.button(question, key=f"preset_{i}"):
                process_question(question)
    
    # 自定义问题输入
    st.subheader("❓ 自定义问题")
    user_question = st.text_input("请输入您的问题:", key="user_input")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        ask_button = st.button("🚀 提问", type="primary")
    
    if ask_button and user_question:
        process_question(user_question)
    
    # 清空聊天历史
    if st.button("🗑️ 清空聊天记录"):
        st.session_state.chat_history = []
        st.rerun()


def process_question(question: str):
    """处理用户问题"""
    if not st.session_state.project_data:
        st.error("项目数据未加载")
        return
    
    with st.spinner("🤔 思考中..."):
        try:
            # 查询相关代码
            query_result = run_stage6_query(st.session_state.project_data, question)
            
            # 生成答案
            answer = run_stage7_answer(st.session_state.project_data, query_result, question)
            
            # 添加到聊天历史
            st.session_state.chat_history.append((question, answer))
            
            # 重新运行以显示新消息
            st.rerun()
            
        except Exception as e:
            st.error(f"处理问题时出错: {str(e)}")


def show_code_viewer():
    """显示代码查看器"""
    st.markdown('<div class="section-header">📝 代码查看器</div>', unsafe_allow_html=True)
    
    if not st.session_state.analysis_complete:
        st.info("请先完成项目分析")
        return
    
    try:
        # 加载项目数据
        if st.session_state.project_data and os.path.exists(st.session_state.project_data):
            with open(st.session_state.project_data, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 文件选择
            files = [file_data.get('path', '') for file_data in data.get('files', [])]
            if files:
                selected_file = st.selectbox("选择文件:", files)
                
                # 找到选中的文件数据
                file_data = None
                for f in data.get('files', []):
                    if f.get('path') == selected_file:
                        file_data = f
                        break
                
                if file_data:
                    # 显示文件信息
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("行数", file_data.get('line_count', 0))
                    with col2:
                        st.metric("函数数", len(file_data.get('functions', [])))
                    with col3:
                        st.metric("类数", len(file_data.get('classes', [])))
                    
                    # 显示代码
                    if os.path.exists(selected_file):
                        with open(selected_file, 'r', encoding='utf-8', errors='ignore') as f:
                            code_content = f.read()
                        
                        st.subheader("📄 源代码")
                        st_ace(
                            value=code_content,
                            language='cpp',
                            theme='github',
                            key="code_viewer",
                            height=400,
                            auto_update=False,
                            wrap=True,
                            font_size=14
                        )
                    
                    # 显示函数列表
                    if file_data.get('functions'):
                        st.subheader("🔧 函数列表")
                        for func in file_data['functions']:
                            with st.expander(f"📋 {func.get('name', 'Unknown')}"):
                                st.write(f"**行数:** {func.get('line_start', 0)} - {func.get('line_end', 0)}")
                                st.write(f"**复杂度:** {func.get('complexity', 'Unknown')}")
                                if func.get('parameters'):
                                    st.write("**参数:**")
                                    for param in func['parameters']:
                                        st.write(f"  • {param.get('type', '')} {param.get('name', '')}")
                    
                    # 显示类列表
                    if file_data.get('classes'):
                        st.subheader("🏗️ 类列表")
                        for cls in file_data['classes']:
                            with st.expander(f"📦 {cls.get('name', 'Unknown')}"):
                                st.write(f"**行数:** {cls.get('line_start', 0)} - {cls.get('line_end', 0)}")
                                if cls.get('members'):
                                    st.write("**成员变量:**")
                                    for member in cls['members']:
                                        st.write(f"  • {member.get('type', '')} {member.get('name', '')}")
                                if cls.get('methods'):
                                    st.write("**成员函数:**")
                                    for method in cls['methods']:
                                        st.write(f"  • {method.get('name', '')}")
    
    except Exception as e:
        st.error(f"加载代码数据失败: {str(e)}")


def main():
    """主函数"""
    initialize_session_state()
    show_header()
    show_sidebar()
    
    # 主要内容区域
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 项目分析", "📊 项目概览", "💬 智能问答", "📝 代码查看"])
    
    with tab1:
        show_project_analysis()
    
    with tab2:
        show_project_overview()
    
    with tab3:
        show_chat_interface()
    
    with tab4:
        show_code_viewer()


if __name__ == "__main__":
    main()