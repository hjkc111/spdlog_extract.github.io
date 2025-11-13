#!/usr/bin/env python3
# run_app.py
"""
C++ 代码理解智能体启动脚本
支持多种运行模式：Web界面、API服务器、命令行
"""

import os
import sys
import argparse
import subprocess
import threading
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings


def run_web_app():
    """运行Web应用"""
    print("🚀 启动Web界面...")
    print(f"📍 访问地址: http://{settings.web_host}:{settings.web_port}")
    
    cmd = [
        sys.executable, "-m", "streamlit", "run", "web_app.py",
        "--server.address", settings.web_host,
        "--server.port", str(settings.web_port),
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false"
    ]
    
    subprocess.run(cmd)


def run_api_server():
    """运行API服务器"""
    print("🚀 启动API服务器...")
    print(f"📍 API地址: http://{settings.api_host}:{settings.api_port}")
    print(f"📖 API文档: http://{settings.api_host}:{settings.api_port}/docs")
    
    cmd = [
        sys.executable, "api_server.py"
    ]
    
    subprocess.run(cmd)


def run_cli_mode():
    """运行命令行模式"""
    print("🚀 启动命令行模式...")
    
    cmd = [
        sys.executable, "main.py"
    ]
    
    subprocess.run(cmd)


def run_full_stack():
    """运行完整堆栈（API + Web）"""
    print("🚀 启动完整堆栈...")
    print(f"📍 API地址: http://{settings.api_host}:{settings.api_port}")
    print(f"📍 Web地址: http://{settings.web_host}:{settings.web_port}")
    
    # 启动API服务器
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    
    # 等待API服务器启动
    time.sleep(3)
    
    # 启动Web应用
    run_web_app()


def check_dependencies():
    """检查依赖"""
    print("🔍 检查依赖...")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ Python版本需要3.8或更高")
        return False
    
    # 检查必要的包
    required_packages = [
        'streamlit', 'fastapi', 'uvicorn', 'clang', 'sentence_transformers',
        'chromadb', 'requests', 'loguru', 'plotly', 'networkx'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少以下包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    # 检查Clang
    if not os.path.exists(settings.clang_library_path):
        print(f"⚠️  Clang库未找到: {settings.clang_library_path}")
        print("代码解析功能可能受限")
    
    # 检查API配置
    if not settings.qwen_api_key:
        print("⚠️  未配置Qwen API Key")
        print("智能问答功能将使用模拟响应")
    
    print("✅ 依赖检查完成")
    return True


def install_dependencies():
    """安装依赖"""
    print("📦 安装依赖...")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    if not requirements_file.exists():
        print("❌ requirements.txt文件不存在")
        return False
    
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False


def show_config():
    """显示配置信息"""
    print("⚙️  当前配置:")
    print(f"  系统: {settings.llvm_path}")
    print(f"  Clang库: {settings.clang_library_path}")
    print(f"  Clang可用: {'✅' if os.path.exists(settings.clang_library_path) else '❌'}")
    print(f"  Qwen API: {'✅ 已配置' if settings.qwen_api_key else '❌ 未配置'}")
    print(f"  嵌入模型: {settings.embedding_model}")
    print(f"  Web端口: {settings.web_port}")
    print(f"  API端口: {settings.api_port}")
    print(f"  最大工作线程: {settings.max_workers}")
    print(f"  数据目录: {settings.DATA_DIR}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="C++ 代码理解智能体",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
运行模式:
  web       启动Web界面 (默认)
  api       启动API服务器
  cli       启动命令行模式
  full      启动完整堆栈 (API + Web)

示例:
  python run_app.py web          # 启动Web界面
  python run_app.py api          # 启动API服务器
  python run_app.py full         # 启动完整堆栈
  python run_app.py --install    # 安装依赖
  python run_app.py --config     # 显示配置
        """
    )
    
    parser.add_argument(
        'mode',
        nargs='?',
        choices=['web', 'api', 'cli', 'full'],
        default='web',
        help='运行模式 (默认: web)'
    )
    
    parser.add_argument(
        '--install',
        action='store_true',
        help='安装依赖包'
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='检查依赖'
    )
    
    parser.add_argument(
        '--config',
        action='store_true',
        help='显示配置信息'
    )
    
    parser.add_argument(
        '--no-check',
        action='store_true',
        help='跳过依赖检查'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🤖 C++ 代码理解智能体")
    print("=" * 60)
    
    # 处理特殊命令
    if args.install:
        install_dependencies()
        return
    
    if args.check:
        check_dependencies()
        return
    
    if args.config:
        show_config()
        return
    
    # 检查依赖（除非跳过）
    if not args.no_check:
        if not check_dependencies():
            print("\n❌ 依赖检查失败，请先解决依赖问题")
            print("提示: 运行 'python run_app.py --install' 安装依赖")
            return
    
    # 显示配置
    show_config()
    print()
    
    # 根据模式运行
    try:
        if args.mode == 'web':
            run_web_app()
        elif args.mode == 'api':
            run_api_server()
        elif args.mode == 'cli':
            run_cli_mode()
        elif args.mode == 'full':
            run_full_stack()
    except KeyboardInterrupt:
        print("\n👋 再见!")
    except Exception as e:
        print(f"\n❌ 运行失败: {e}")


if __name__ == "__main__":
    main()