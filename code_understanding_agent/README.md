# C++ 代码理解智能体

一个基于AI的C++代码分析和问答系统，能够深度理解大型C++项目的代码结构、语义和关系，并提供智能的代码问答服务。

## 🎯 项目特点

### 核心功能
- **深度代码分析**：基于Clang AST的精确C++代码解析
- **语义理解**：使用大语言模型进行代码语义分析
- **智能问答**：基于RAG（检索增强生成）的代码理解和问答
- **向量搜索**：使用ChromaDB进行高效的语义相似度搜索
- **可视化展示**：代码结构和关系的图形化展示
- **多界面支持**：Web界面、API服务和命令行界面

### 技术架构
- **前端**：Streamlit Web界面 + FastAPI REST API
- **后端**：Python 3.8+ 多阶段处理管道
- **AI模型**：Qwen大语言模型 + Sentence Transformers嵌入模型
- **向量数据库**：ChromaDB持久化存储
- **代码解析**：Clang/LLVM AST分析
- **知识图谱**：NetworkX图结构表示

## 🚀 快速开始

### 环境要求
- Python 3.8+
- LLVM/Clang (用于C++代码解析)
- 8GB+ RAM (推荐)
- Qwen API Key (可选，用于智能问答)

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd code_understanding_agent
```

2. **安装依赖**
```bash
# 自动安装所有依赖
python run_app.py --install

# 或手动安装
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
# 创建 .env 文件
cp .env.example .env

# 编辑配置
QWEN_API_KEY=your_qwen_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
```

4. **检查环境**
```bash
python run_app.py --check
```

### 运行应用

#### Web界面模式（推荐）
```bash
python run_app.py web
# 访问 http://localhost:8501
```

#### API服务模式
```bash
python run_app.py api
# API文档: http://localhost:8000/docs
```

#### 完整堆栈模式
```bash
python run_app.py full
# 同时启动Web界面和API服务
```

#### 命令行模式
```bash
python run_app.py cli
```

## 📋 使用指南

### 1. 项目分析

在Web界面中：
1. 输入C++项目路径
2. 点击"开始分析"
3. 等待分析完成（包含7个处理阶段）

### 2. 智能问答

分析完成后，可以提问：
- "这个项目的主要功能是什么？"
- "Logger类是如何实现的？"
- "有哪些重要的函数？"
- "如何使用这个库？"

### 3. API调用

```python
import requests

# 分析项目
response = requests.post("http://localhost:8000/analyze", json={
    "project_path": "/path/to/cpp/project"
})

# 查询代码
response = requests.post("http://localhost:8000/query", json={
    "question": "如何使用Logger类？"
})
```

## 🏗️ 系统架构

### 处理管道（7个阶段）

#### 阶段1：项目解析 (Project Parser)
**功能**：扫描和解析C++项目文件结构
- 递归扫描项目目录
- 识别C++源文件（.cpp, .h, .hpp等）
- 过滤构建目录和临时文件
- 生成文件清单和基本统计信息

**输出**：项目文件列表和元数据

#### 阶段2：符号提取 (Symbol Extractor)
**功能**：使用Clang AST提取代码符号
- 解析每个源文件的AST
- 提取函数、类、变量、宏定义
- 分析函数参数、返回类型
- 提取注释和文档字符串
- 计算代码复杂度指标

**核心技术**：
```python
def extract_functions(self, cursor):
    """提取函数信息"""
    if cursor.kind == CursorKind.FUNCTION_DECL:
        return {
            'name': cursor.spelling,
            'return_type': cursor.result_type.spelling,
            'parameters': self.extract_parameters(cursor),
            'location': cursor.location,
            'complexity': self.calculate_complexity(cursor)
        }
```

**输出**：结构化的代码符号数据

#### 阶段3：关系构建 (Relation Builder)
**功能**：分析代码实体间的关系
- 函数调用关系
- 类继承关系
- 包含依赖关系
- 变量使用关系
- 模块间依赖

**关系类型**：
- `CALLS`：函数调用
- `INHERITS`：类继承
- `INCLUDES`：文件包含
- `USES`：变量使用
- `DEFINES`：定义关系

**输出**：关系图数据结构

#### 阶段4：知识图谱 (Knowledge Graph)
**功能**：构建代码知识图谱
- 整合符号和关系数据
- 构建图结构表示
- 计算图的拓扑属性
- 识别关键节点和路径

**图结构**：
```python
knowledge_graph = {
    "nodes": {
        "node_id": {
            "type": "function|class|file",
            "name": "entity_name",
            "properties": {...},
            "semantic": {...}
        }
    },
    "edges": [
        {
            "source": "node_id1",
            "target": "node_id2", 
            "type": "relation_type",
            "properties": {...}
        }
    ]
}
```

**输出**：完整的知识图谱

#### 阶段5：语义嵌入 (Semantic Embedder)
**功能**：生成代码的语义向量表示
- 使用Sentence Transformers生成嵌入
- 代码块分割和预处理
- 存储到ChromaDB向量数据库
- 构建语义搜索索引

**嵌入策略**：
```python
def prepare_text_content(self, chunk):
    """准备嵌入文本"""
    content_parts = []
    
    # 添加上下文信息
    if chunk.get('file_path'):
        content_parts.append(f"File: {chunk['file_path']}")
    
    if chunk.get('function_name'):
        content_parts.append(f"Function: {chunk['function_name']}")
    
    # 添加代码内容
    content_parts.append(f"Code:\n{chunk['content']}")
    
    return "\n\n".join(content_parts)
```

**输出**：向量数据库和搜索索引

#### 阶段6：查询处理 (Query Processor)
**功能**：处理用户查询并检索相关代码
- 查询意图识别
- 语义相似度搜索
- 结果排序和过滤
- 上下文构建

**查询流程**：
```python
def process_query(self, user_query):
    # 1. 意图识别
    intent = self.identify_intent(user_query)
    
    # 2. 向量搜索
    search_results = vector_db.search_similar_code(
        query=user_query,
        n_results=10
    )
    
    # 3. 结果排序
    ranked_results = self.rank_results(search_results, intent)
    
    return ranked_results
```

**输出**：排序的相关代码片段

#### 阶段7：答案生成 (Answer Generator)
**功能**：基于检索结果生成智能答案
- 使用Qwen API生成答案
- 结合代码上下文
- 提供代码示例和导航信息
- 生成结构化响应

**答案结构**：
```python
answer = {
    "answer": "详细的文本答案",
    "key_points": ["关键要点1", "关键要点2"],
    "code_examples": [
        {
            "description": "示例描述",
            "code": "示例代码"
        }
    ],
    "related_functions": ["函数1", "函数2"],
    "navigation": [
        {
            "name": "函数名",
            "type": "function",
            "location": "文件:行号"
        }
    ]
}
```

**输出**：结构化的智能答案

### 核心组件

#### 配置管理 (config/settings.py)
- 跨平台Clang配置
- API密钥管理
- 向量数据库配置
- 日志和缓存设置

#### 向量数据库 (utils/vector_db.py)
- ChromaDB集成
- 语义搜索功能
- 代码块分割策略
- 相似度计算

#### API客户端 (utils/qwen_api.py)
- Qwen API封装
- 流式响应支持
- 错误处理和重试
- 模拟响应（测试用）

#### Web界面 (web_app.py)
- Streamlit多页面应用
- 实时分析进度
- 交互式问答界面
- 代码查看器

#### API服务 (api_server.py)
- FastAPI REST API
- WebSocket实时通信
- 后台任务处理
- 完整的API文档

## 🔧 配置选项

### 环境变量
```bash
# API配置
QWEN_API_KEY=your_api_key
QWEN_BASE_URL=api_endpoint

# 系统配置
LLVM_PATH=/usr/local/opt/llvm
CLANG_LIBRARY_PATH=/usr/lib/libclang.so

# 性能配置
MAX_WORKERS=4
BATCH_SIZE=100
CHUNK_SIZE=512
```

### 高级配置
```python
# config/settings.py
class Settings:
    # 嵌入模型配置
    embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension = 384
    
    # 代码分析配置
    max_file_size = 1024 * 1024  # 1MB
    supported_extensions = ['.cpp', '.h', '.hpp']
    
    # 向量数据库配置
    chroma_persist_directory = "data/embeddings/chroma_db"
```

## 📊 性能优化

### 内存优化
- 分批处理大型项目
- 智能缓存机制
- 向量数据库持久化

### 速度优化
- 并行文件处理
- 增量分析支持
- 预计算常用查询

### 准确性优化
- 多层次语义分析
- 上下文感知搜索
- 意图识别优化

## 🐛 故障排除

### 常见问题

#### 1. Clang库未找到
```bash
# Ubuntu/Debian
sudo apt-get install libclang-dev

# macOS
brew install llvm

# 设置环境变量
export CLANG_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libclang.so.1
```

#### 2. 内存不足
```bash
# 减少并发数
export MAX_WORKERS=2
export BATCH_SIZE=50
```

#### 3. API调用失败
- 检查API密钥配置
- 验证网络连接
- 查看日志文件：`logs/app.log`

### 调试模式
```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
python run_app.py web
```

## 🤝 贡献指南

### 开发环境设置
```bash
# 克隆项目
git clone <repository-url>
cd code_understanding_agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 代码规范
- 使用Black进行代码格式化
- 遵循PEP 8编码规范
- 添加类型注解
- 编写单元测试

### 提交流程
1. Fork项目
2. 创建功能分支
3. 提交代码
4. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Clang/LLVM](https://clang.llvm.org/) - C++代码解析
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [Streamlit](https://streamlit.io/) - Web界面框架
- [FastAPI](https://fastapi.tiangolo.com/) - API框架
- [Sentence Transformers](https://www.sbert.net/) - 文本嵌入模型

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue
- 发送邮件
- 参与讨论

---

**注意**：本项目仍在积极开发中，功能和API可能会发生变化。建议在生产环境使用前进行充分测试。