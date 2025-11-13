# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

# 项目配置
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
CACHE_DIR = os.path.join(DATA_DIR, "cache")

# LLVM/Clang配置 - 从环境变量读取
LLVM_PATH = os.getenv('LLVM_PATH', 'C:\\Program Files\\LLVM')
LLVM_BIN_PATH = os.getenv('LLVM_BIN_PATH', os.path.join(LLVM_PATH, 'bin'))
CLANG_LIBRARY_PATH = os.getenv('CLANG_LIBRARY_PATH', os.path.join(LLVM_BIN_PATH, 'libclang.dll'))

# 其他配置
QWEN_API_KEY = os.getenv('QWEN_API_KEY')
QWEN_BASE_URL = os.getenv('QWEN_BASE_URL')
MAX_FILES_TO_PARSE = int(os.getenv('MAX_FILES_TO_PARSE', 100))
MAX_FUNCTION_COMPLEXITY = int(os.getenv('MAX_FUNCTION_COMPLEXITY', 50))

# 确保目录存在
for directory in [DATA_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR, CACHE_DIR]:
    os.makedirs(directory, exist_ok=True)

# 打印配置信息（调试用）
def print_config():
    print("=== 配置信息 ===")
    print(f"LLVM路径: {LLVM_PATH}")
    print(f"LLVM Bin路径: {LLVM_BIN_PATH}")
    print(f"Clang库路径: {CLANG_LIBRARY_PATH}")
    print(f"Clang库文件存在: {os.path.exists(CLANG_LIBRARY_PATH)}")
    print("================")