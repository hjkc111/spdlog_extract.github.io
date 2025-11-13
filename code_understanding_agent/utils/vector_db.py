# utils/vector_db.py
import os
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
import numpy as np
from loguru import logger

from config.settings import settings


class VectorDatabase:
    """向量数据库管理器"""
    
    def __init__(self):
        self.embedding_model = None
        self.chroma_client = None
        self.collection = None
        self._initialize()
    
    def _initialize(self):
        """初始化向量数据库"""
        try:
            # 初始化嵌入模型
            logger.info(f"加载嵌入模型: {settings.embedding_model}")
            self.embedding_model = SentenceTransformer(settings.embedding_model)
            
            # 初始化ChromaDB
            logger.info(f"初始化ChromaDB: {settings.chroma_persist_directory}")
            self.chroma_client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # 获取或创建集合
            self.collection = self.chroma_client.get_or_create_collection(
                name="code_embeddings",
                metadata={"description": "C++ code embeddings for semantic search"}
            )
            
            logger.info("向量数据库初始化完成")
            
        except Exception as e:
            logger.error(f"向量数据库初始化失败: {e}")
            raise
    
    def add_code_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """添加代码块到向量数据库"""
        try:
            if not chunks:
                return True
            
            # 准备数据
            texts = []
            metadatas = []
            ids = []
            
            for chunk in chunks:
                # 生成唯一ID
                chunk_id = self._generate_chunk_id(chunk)
                
                # 检查是否已存在
                if self._chunk_exists(chunk_id):
                    continue
                
                # 准备文本内容
                text_content = self._prepare_text_content(chunk)
                
                texts.append(text_content)
                metadatas.append({
                    'file_path': chunk.get('file_path', ''),
                    'function_name': chunk.get('function_name', ''),
                    'class_name': chunk.get('class_name', ''),
                    'chunk_type': chunk.get('type', 'code'),
                    'line_start': chunk.get('line_start', 0),
                    'line_end': chunk.get('line_end', 0),
                    'complexity': chunk.get('complexity', 0),
                    'language': 'cpp'
                })
                ids.append(chunk_id)
            
            if not texts:
                logger.info("没有新的代码块需要添加")
                return True
            
            # 生成嵌入
            logger.info(f"为 {len(texts)} 个代码块生成嵌入...")
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            
            # 添加到数据库
            self.collection.add(
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"成功添加 {len(texts)} 个代码块到向量数据库")
            return True
            
        except Exception as e:
            logger.error(f"添加代码块到向量数据库失败: {e}")
            return False
    
    def search_similar_code(self, query: str, n_results: int = 10, 
                           filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """搜索相似代码"""
        try:
            # 生成查询嵌入
            query_embedding = self.embedding_model.encode([query])
            
            # 构建过滤条件
            where_clause = {}
            if filters:
                for key, value in filters.items():
                    if key in ['file_path', 'function_name', 'class_name', 'chunk_type']:
                        where_clause[key] = value
            
            # 执行搜索
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=n_results,
                where=where_clause if where_clause else None,
                include=['documents', 'metadatas', 'distances']
            )
            
            # 格式化结果
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'similarity': 1 - results['distances'][0][i],  # 转换为相似度
                    'distance': results['distances'][0][i]
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"搜索相似代码失败: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            count = self.collection.count()
            return {
                'total_chunks': count,
                'embedding_model': settings.embedding_model,
                'embedding_dimension': settings.embedding_dimension
            }
        except Exception as e:
            logger.error(f"获取集合统计信息失败: {e}")
            return {}
    
    def clear_collection(self) -> bool:
        """清空集合"""
        try:
            # 删除现有集合
            self.chroma_client.delete_collection("code_embeddings")
            
            # 重新创建集合
            self.collection = self.chroma_client.get_or_create_collection(
                name="code_embeddings",
                metadata={"description": "C++ code embeddings for semantic search"}
            )
            
            logger.info("向量数据库已清空")
            return True
            
        except Exception as e:
            logger.error(f"清空向量数据库失败: {e}")
            return False
    
    def _generate_chunk_id(self, chunk: Dict[str, Any]) -> str:
        """生成代码块唯一ID"""
        content = f"{chunk.get('file_path', '')}{chunk.get('content', '')}{chunk.get('line_start', 0)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _chunk_exists(self, chunk_id: str) -> bool:
        """检查代码块是否已存在"""
        try:
            result = self.collection.get(ids=[chunk_id])
            return len(result['ids']) > 0
        except:
            return False
    
    def _prepare_text_content(self, chunk: Dict[str, Any]) -> str:
        """准备用于嵌入的文本内容"""
        content_parts = []
        
        # 添加上下文信息
        if chunk.get('file_path'):
            content_parts.append(f"File: {chunk['file_path']}")
        
        if chunk.get('function_name'):
            content_parts.append(f"Function: {chunk['function_name']}")
        
        if chunk.get('class_name'):
            content_parts.append(f"Class: {chunk['class_name']}")
        
        # 添加代码内容
        if chunk.get('content'):
            content_parts.append(f"Code:\n{chunk['content']}")
        
        # 添加注释
        if chunk.get('comments'):
            content_parts.append(f"Comments: {chunk['comments']}")
        
        return "\n\n".join(content_parts)


class CodeChunker:
    """代码分块器"""
    
    def __init__(self):
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
    
    def chunk_function(self, function_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """对函数进行分块"""
        chunks = []
        
        # 如果函数较小，作为一个整体块
        if len(function_info.get('content', '')) <= self.chunk_size:
            chunks.append({
                'type': 'function',
                'content': function_info.get('content', ''),
                'file_path': function_info.get('file_path', ''),
                'function_name': function_info.get('name', ''),
                'class_name': function_info.get('class_name', ''),
                'line_start': function_info.get('line_start', 0),
                'line_end': function_info.get('line_end', 0),
                'complexity': function_info.get('complexity', 0),
                'comments': function_info.get('comments', '')
            })
        else:
            # 对大函数进行分块
            content = function_info.get('content', '')
            lines = content.split('\n')
            
            current_chunk = []
            current_size = 0
            start_line = function_info.get('line_start', 0)
            
            for i, line in enumerate(lines):
                current_chunk.append(line)
                current_size += len(line)
                
                if current_size >= self.chunk_size:
                    # 创建块
                    chunk_content = '\n'.join(current_chunk)
                    chunks.append({
                        'type': 'function_part',
                        'content': chunk_content,
                        'file_path': function_info.get('file_path', ''),
                        'function_name': function_info.get('name', ''),
                        'class_name': function_info.get('class_name', ''),
                        'line_start': start_line + i - len(current_chunk) + 1,
                        'line_end': start_line + i,
                        'complexity': function_info.get('complexity', 0),
                        'part_index': len(chunks)
                    })
                    
                    # 重置，保留重叠
                    overlap_lines = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                    current_chunk = overlap_lines
                    current_size = sum(len(line) for line in overlap_lines)
            
            # 处理剩余内容
            if current_chunk:
                chunk_content = '\n'.join(current_chunk)
                chunks.append({
                    'type': 'function_part',
                    'content': chunk_content,
                    'file_path': function_info.get('file_path', ''),
                    'function_name': function_info.get('name', ''),
                    'class_name': function_info.get('class_name', ''),
                    'line_start': start_line + len(lines) - len(current_chunk),
                    'line_end': function_info.get('line_end', 0),
                    'complexity': function_info.get('complexity', 0),
                    'part_index': len(chunks)
                })
        
        return chunks
    
    def chunk_class(self, class_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """对类进行分块"""
        chunks = []
        
        # 类声明块
        if class_info.get('declaration'):
            chunks.append({
                'type': 'class_declaration',
                'content': class_info['declaration'],
                'file_path': class_info.get('file_path', ''),
                'class_name': class_info.get('name', ''),
                'line_start': class_info.get('line_start', 0),
                'line_end': class_info.get('declaration_end', 0),
                'comments': class_info.get('comments', '')
            })
        
        # 成员变量块
        if class_info.get('members'):
            members_content = '\n'.join([f"{m['type']} {m['name']};" for m in class_info['members']])
            chunks.append({
                'type': 'class_members',
                'content': members_content,
                'file_path': class_info.get('file_path', ''),
                'class_name': class_info.get('name', ''),
                'line_start': class_info.get('line_start', 0),
                'line_end': class_info.get('line_end', 0)
            })
        
        return chunks


# 全局实例
vector_db = VectorDatabase()
code_chunker = CodeChunker()