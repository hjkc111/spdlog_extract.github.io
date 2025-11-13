# config/settings.py
import os
import platform
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
KNOWLEDGE_GRAPH_DIR = DATA_DIR / "knowledge_graph"
LOGS_DIR = PROJECT_ROOT / "logs"

# 确保目录存在
for dir_path in [DATA_DIR, PROCESSED_DIR, CACHE_DIR, EMBEDDINGS_DIR, KNOWLEDGE_GRAPH_DIR, LOGS_DIR]:
    dir_path.mkdir(exist_ok=True)


class Settings:
    """应用配置"""
    
    def __init__(self):
        # API配置
        self.qwen_api_key = os.getenv('QWEN_API_KEY', '')
        self.qwen_base_url = os.getenv('QWEN_BASE_URL', 
            'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation')
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        
        # LLVM/Clang配置 - 跨平台支持
        self._setup_clang_config()
        
        # 嵌入模型配置
        self.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        self.embedding_dimension = 384
        self.chunk_size = 512
        self.chunk_overlap = 50
        
        # 向量数据库配置
        self.chroma_persist_directory = str(EMBEDDINGS_DIR / "chroma_db")
        
        # 代码分析配置
        self.max_file_size = 1024 * 1024  # 1MB
        self.supported_extensions = ['.cpp', '.cc', '.cxx', '.c++', '.h', '.hpp', '.hxx', '.h++']
        self.ignore_patterns = ['build/', 'cmake-build-*/', '.git/', '__pycache__/', '*.pyc']
        
        # 并发配置
        self.max_workers = int(os.getenv('MAX_WORKERS', '4'))
        self.batch_size = int(os.getenv('BATCH_SIZE', '100'))
        
        # 缓存配置
        self.cache_ttl = 3600 * 24  # 24小时
        self.enable_cache = True
        
        # 日志配置
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = str(LOGS_DIR / "app.log")
        
        # Web界面配置
        self.web_host = os.getenv('WEB_HOST', '0.0.0.0')
        self.web_port = int(os.getenv('WEB_PORT', '8501'))
        self.api_host = os.getenv('API_HOST', '0.0.0.0')
        self.api_port = int(os.getenv('API_PORT', '8000'))
        
        # 其他配置
        self.max_files_to_parse = int(os.getenv('MAX_FILES_TO_PARSE', '100'))
        self.max_function_complexity = int(os.getenv('MAX_FUNCTION_COMPLEXITY', '50'))
    
    def _setup_clang_config(self):
        """设置Clang配置"""
        system = platform.system()
        
        if system == "Windows":
            # Windows配置
            self.llvm_path = os.getenv('LLVM_PATH', 'C:\\Program Files\\LLVM')
            self.llvm_bin_path = os.getenv('LLVM_BIN_PATH', os.path.join(self.llvm_path, 'bin'))
            self.clang_library_path = os.getenv('CLANG_LIBRARY_PATH', 
                os.path.join(self.llvm_bin_path, 'libclang.dll'))
            
            self.clang_args = [
                '-std=c++17',
                '-I' + os.path.join(self.llvm_path, 'include'),
                '-Wall',
                '-Wextra',
                '-fparse-all-comments'
            ]
        
        elif system == "Darwin":  # macOS
            # macOS配置
            self.llvm_path = os.getenv('LLVM_PATH', '/usr/local/opt/llvm')
            self.llvm_bin_path = os.getenv('LLVM_BIN_PATH', os.path.join(self.llvm_path, 'bin'))
            self.clang_library_path = os.getenv('CLANG_LIBRARY_PATH', 
                os.path.join(self.llvm_path, 'lib', 'libclang.dylib'))
            
            self.clang_args = [
                '-std=c++17',
                '-I/usr/include',
                '-I/usr/local/include',
                '-I/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/include/c++/v1',
                '-Wall',
                '-Wextra',
                '-fparse-all-comments'
            ]
        
        else:  # Linux
            # Linux配置
            self.llvm_path = os.getenv('LLVM_PATH', '/usr')
            self.llvm_bin_path = os.getenv('LLVM_BIN_PATH', '/usr/bin')
            self.clang_library_path = os.getenv('CLANG_LIBRARY_PATH', '/usr/lib/x86_64-linux-gnu/libclang-16.so.1')
            
            # 尝试找到libclang
            possible_paths = [
                '/usr/lib/x86_64-linux-gnu/libclang-16.so.1',
                '/usr/lib/x86_64-linux-gnu/libclang.so.1',
                '/usr/lib/libclang.so',
                '/usr/local/lib/libclang.so'
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    self.clang_library_path = path
                    break
            
            self.clang_args = [
                '-std=c++17',
                '-I/usr/include',
                '-I/usr/local/include',
                '-I/usr/include/c++/11',
                '-I/usr/include/x86_64-linux-gnu/c++/11',
                '-Wall',
                '-Wextra',
                '-fparse-all-comments'
            ]
    
    def print_config(self):
        """打印配置信息（调试用）"""
        print("=== 配置信息 ===")
        print(f"系统: {platform.system()}")
        print(f"LLVM路径: {self.llvm_path}")
        print(f"LLVM Bin路径: {self.llvm_bin_path}")
        print(f"Clang库路径: {self.clang_library_path}")
        print(f"Clang库文件存在: {os.path.exists(self.clang_library_path)}")
        print(f"Qwen API Key: {'已设置' if self.qwen_api_key else '未设置'}")
        print(f"OpenAI API Key: {'已设置' if self.openai_api_key else '未设置'}")
        print("================")


# 全局设置实例
settings = Settings()

# 向后兼容的变量
LLVM_PATH = settings.llvm_path
LLVM_BIN_PATH = settings.llvm_bin_path
CLANG_LIBRARY_PATH = settings.clang_library_path
CLANG_ARGS = settings.clang_args
QWEN_API_KEY = settings.qwen_api_key
QWEN_BASE_URL = settings.qwen_base_url
MAX_FILES_TO_PARSE = settings.max_files_to_parse
MAX_FUNCTION_COMPLEXITY = settings.max_function_complexity

# 向后兼容的函数
def print_config():
    settings.print_config()