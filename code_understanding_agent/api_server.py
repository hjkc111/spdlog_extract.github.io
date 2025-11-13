# api_server.py
import os
import sys
import json
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from loguru import logger

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


# 创建FastAPI应用
app = FastAPI(
    title="C++ 代码理解智能体 API",
    description="基于AI的C++代码分析和问答系统",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局状态
analysis_status = {}
active_connections: List[WebSocket] = []


# 请求模型
class AnalysisRequest(BaseModel):
    project_path: str
    options: Optional[Dict[str, Any]] = {}


class QueryRequest(BaseModel):
    question: str
    project_id: Optional[str] = None
    context_limit: Optional[int] = 10


class StreamQueryRequest(BaseModel):
    question: str
    project_id: Optional[str] = None
    context_limit: Optional[int] = 10


# 响应模型
class AnalysisResponse(BaseModel):
    success: bool
    message: str
    project_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    success: bool
    answer: Dict[str, Any]
    context: List[Dict[str, Any]]
    processing_time: float


class StatusResponse(BaseModel):
    status: str
    progress: float
    message: str
    data: Optional[Dict[str, Any]] = None


# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "C++ 代码理解智能体 API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "qwen_api": "configured" if settings.qwen_api_key else "not_configured",
        "clang": "available" if os.path.exists(settings.clang_library_path) else "not_available",
        "vector_db": "initialized"
    }


@app.get("/config")
async def get_config():
    """获取配置信息"""
    return {
        "embedding_model": settings.embedding_model,
        "supported_extensions": settings.supported_extensions,
        "max_file_size": settings.max_file_size,
        "chunk_size": settings.chunk_size,
        "max_workers": settings.max_workers
    }


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_project(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """分析项目"""
    try:
        project_path = request.project_path
        
        # 验证项目路径
        if not os.path.exists(project_path):
            raise HTTPException(status_code=400, detail="项目路径不存在")
        
        # 生成项目ID
        project_id = Path(project_path).name
        
        # 初始化分析状态
        analysis_status[project_id] = {
            "status": "starting",
            "progress": 0.0,
            "message": "开始分析...",
            "project_path": project_path
        }
        
        # 在后台运行分析
        background_tasks.add_task(run_analysis_pipeline, project_path, project_id)
        
        return AnalysisResponse(
            success=True,
            message="分析已开始",
            project_id=project_id
        )
        
    except Exception as e:
        logger.error(f"分析项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analysis/{project_id}/status", response_model=StatusResponse)
async def get_analysis_status(project_id: str):
    """获取分析状态"""
    if project_id not in analysis_status:
        raise HTTPException(status_code=404, detail="项目未找到")
    
    status = analysis_status[project_id]
    return StatusResponse(
        status=status["status"],
        progress=status["progress"],
        message=status["message"],
        data=status.get("data")
    )


@app.post("/query", response_model=QueryResponse)
async def query_code(request: QueryRequest):
    """查询代码"""
    try:
        import time
        start_time = time.time()
        
        # 查找项目数据
        project_data_file = None
        if request.project_id:
            # 查找特定项目的数据文件
            processed_dir = settings.PROCESSED_DIR
            for file in processed_dir.glob(f"*{request.project_id}*stage5*.json"):
                project_data_file = str(file)
                break
        else:
            # 查找最新的数据文件
            processed_dir = settings.PROCESSED_DIR
            stage5_files = list(processed_dir.glob("*stage5*.json"))
            if stage5_files:
                project_data_file = str(sorted(stage5_files)[-1])
        
        if not project_data_file or not os.path.exists(project_data_file):
            raise HTTPException(status_code=404, detail="项目数据未找到，请先分析项目")
        
        # 执行查询
        query_result = run_stage6_query(project_data_file, request.question)
        answer = run_stage7_answer(project_data_file, query_result, request.question)
        
        processing_time = time.time() - start_time
        
        return QueryResponse(
            success=True,
            answer=answer,
            context=query_result.get('context', []),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query/stream")
async def stream_query(request: StreamQueryRequest):
    """流式查询"""
    try:
        # 查找项目数据
        project_data_file = None
        if request.project_id:
            processed_dir = settings.PROCESSED_DIR
            for file in processed_dir.glob(f"*{request.project_id}*stage5*.json"):
                project_data_file = str(file)
                break
        else:
            processed_dir = settings.PROCESSED_DIR
            stage5_files = list(processed_dir.glob("*stage5*.json"))
            if stage5_files:
                project_data_file = str(sorted(stage5_files)[-1])
        
        if not project_data_file or not os.path.exists(project_data_file):
            raise HTTPException(status_code=404, detail="项目数据未找到")
        
        # 执行查询获取上下文
        query_result = run_stage6_query(project_data_file, request.question)
        context = query_result.get('context', [])
        
        # 流式生成答案
        async def generate_stream():
            try:
                # 发送上下文信息
                yield f"data: {json.dumps({'type': 'context', 'data': context})}\n\n"
                
                # 流式生成答案
                for chunk in qwen_api.stream_query(
                    request.question,
                    system_prompt="你是一个专业的C++代码助手，基于提供的代码上下文回答问题。"
                ):
                    yield f"data: {json.dumps({'type': 'answer', 'content': chunk})}\n\n"
                
                # 发送完成信号
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"流式查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects")
async def list_projects():
    """列出所有项目"""
    try:
        projects = []
        processed_dir = settings.PROCESSED_DIR
        
        for file in processed_dir.glob("*stage5*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                project_info = {
                    "id": file.stem,
                    "name": data.get('project_name', file.stem),
                    "path": data.get('project_path', ''),
                    "file_count": len(data.get('files', [])),
                    "analysis_time": data.get('analysis_time', ''),
                    "data_file": str(file)
                }
                projects.append(project_info)
                
            except Exception as e:
                logger.warning(f"读取项目文件失败 {file}: {e}")
                continue
        
        return {"projects": projects}
        
    except Exception as e:
        logger.error(f"列出项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vector-db/stats")
async def get_vector_db_stats():
    """获取向量数据库统计信息"""
    try:
        stats = vector_db.get_collection_stats()
        return stats
    except Exception as e:
        logger.error(f"获取向量数据库统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/vector-db/clear")
async def clear_vector_db():
    """清空向量数据库"""
    try:
        success = vector_db.clear_collection()
        if success:
            return {"message": "向量数据库已清空"}
        else:
            raise HTTPException(status_code=500, detail="清空失败")
    except Exception as e:
        logger.error(f"清空向量数据库失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """WebSocket端点，用于实时状态更新"""
    await manager.connect(websocket)
    try:
        while True:
            # 发送当前状态
            if project_id in analysis_status:
                status = analysis_status[project_id]
                await websocket.send_text(json.dumps(status))
            
            await asyncio.sleep(1)  # 每秒更新一次
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def run_analysis_pipeline(project_path: str, project_id: str):
    """运行分析管道"""
    try:
        # 更新状态
        def update_status(stage: str, progress: float, message: str, data: Dict[str, Any] = None):
            analysis_status[project_id] = {
                "status": stage,
                "progress": progress,
                "message": message,
                "project_path": project_path,
                "data": data or {}
            }
        
        # 阶段1: 项目解析
        update_status("stage1", 0.1, "项目解析中...")
        stage1_output = run_stage1(project_path)
        
        # 阶段2: 符号提取
        update_status("stage2", 0.3, "符号提取中...")
        stage2_output = run_stage2(stage1_output)
        
        # 阶段3: 关系构建
        update_status("stage3", 0.5, "关系构建中...")
        stage3_output = run_stage3(stage2_output)
        
        # 阶段4: 知识图谱
        update_status("stage4", 0.7, "知识图谱构建中...")
        stage4_output = run_stage4(stage3_output)
        
        # 阶段5: 语义嵌入
        update_status("stage5", 0.9, "语义嵌入中...")
        stage5_output = run_stage5(stage4_output)
        
        # 完成
        update_status("completed", 1.0, "分析完成", {
            "output_file": stage5_output,
            "project_id": project_id
        })
        
        logger.info(f"项目 {project_id} 分析完成")
        
    except Exception as e:
        logger.error(f"分析管道失败 {project_id}: {e}")
        analysis_status[project_id] = {
            "status": "failed",
            "progress": 0.0,
            "message": f"分析失败: {str(e)}",
            "project_path": project_path,
            "error": str(e)
        }


if __name__ == "__main__":
    # 配置日志
    logger.add(
        settings.log_file,
        rotation="10 MB",
        retention="7 days",
        level=settings.log_level
    )
    
    logger.info("启动API服务器...")
    
    # 启动服务器
    uvicorn.run(
        "api_server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )