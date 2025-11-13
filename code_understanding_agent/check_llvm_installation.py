# check_llvm_installation.py
import os
import sys
from config.settings import LLVM_PATH, LLVM_BIN_PATH, CLANG_LIBRARY_PATH, print_config


def check_llvm_installation():
    """检查LLVM安装"""
    print("检查LLVM安装...")
    print_config()

    # 检查关键文件
    critical_files = [
        (CLANG_LIBRARY_PATH, "libclang.dll"),
        (os.path.join(LLVM_BIN_PATH, "clang.exe"), "clang.exe"),
        (os.path.join(LLVM_BIN_PATH, "clang++.exe"), "clang++.exe"),
    ]

    all_ok = True
    for file_path, file_name in critical_files:
        exists = os.path.exists(file_path)
        status = "✅ 存在" if exists else "❌ 不存在"
        print(f"{file_name}: {status} ({file_path})")
        if not exists:
            all_ok = False

    # 检查环境变量
    print(f"\n环境变量LLVM_PATH: {os.getenv('LLVM_PATH', '未设置')}")
    print(f"环境变量PATH中包含LLVM: {'LLVM' in os.getenv('PATH', '')}")

    # 测试libclang
    print(f"\n测试libclang...")
    try:
        import clang.cindex
        clang.cindex.Config.set_library_file(CLANG_LIBRARY_PATH)
        index = clang.cindex.Index.create()
        print("✅ libclang功能正常")
    except Exception as e:
        print(f"❌ libclang测试失败: {e}")
        all_ok = False

    if all_ok:
        print(f"\n🎉 LLVM安装验证通过！")
        return True
    else:
        print(f"\n⚠️ LLVM安装存在问题，请检查配置。")
        return False


if __name__ == "__main__":
    check_llvm_installation()