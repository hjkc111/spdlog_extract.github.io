# utils/file_utils.py
import os
import json
import pickle
from typing import Any, Dict

def ensure_dir(directory: str):
    """确保目录存在"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def save_json(data: Any, file_path: str):
    """保存JSON文件"""
    ensure_dir(os.path.dirname(file_path))
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(file_path: str) -> Any:
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_pickle(data: Any, file_path: str):
    """保存pickle文件"""
    ensure_dir(os.path.dirname(file_path))
    with open(file_path, 'wb') as f:
        pickle.dump(data, f)

def load_pickle(file_path: str) -> Any:
    """加载pickle文件"""
    with open(file_path, 'rb') as f:
        return pickle.load(f)

def get_file_hash(file_path: str) -> str:
    """获取文件哈希值"""
    import hashlib
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()