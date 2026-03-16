"""
VigilAI REST API服务
使用FastAPI提供数据查询和管理接口
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import API_HOST, API_PORT
from models import Activity, Category, Priority

logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="VigilAI API",
    description="开发者搞钱机会监控系统API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 响应模型
class ActivityListResponse(BaseModel):
    """活动列表响应"""
    total: int
    page: int
    page_size: int
    items: List[dict]


class SourceStatusResponse(BaseModel):
    """信息源状态响应"""
    id: str
    name: str
    type: str
    category: str
    status: str
    last_run: Optional[str]
    last_success: Optional[str]
    activity_count: int
    error_message: Optional[str]


class StatsResponse(BaseModel):
    """统计信息响应"""
    total_activities: int
    total_sources: int
    activities_by_category: dict
    activities_by_source: dict
    last_update: Optional[str]


class RefreshResponse(BaseModel):
    """刷新响应"""
    success: bool
    message: str


# API端点
@app.get("/api/activities", response_model=ActivityListResponse)
async def list_activities(
    request: Request,
    category: Optional[str] = Query(None, description="按类别过滤"),
    source_id: Optional[str] = Query(None, description="按信息源过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取活动列表
    
    支持按类别、信息源、状态过滤
    支持按创建时间、截止日期、奖金排序
    支持分页
    """
    data_manager = request.app.state.data_manager
    
    # 构建过滤条件
    filters = {}
    if category:
        filters['category'] = category
    if source_id:
        filters['source_id'] = source_id
    if status:
        filters['status'] = status
    if search:
        filters['search'] = search
    
    # 查询活动
    activities, total = data_manager.get_activities(
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )
    
    # 转换为字典列表
    items = [act.model_dump() for act in activities]
    
    # 处理datetime序列化
    for item in items:
        for key, value in item.items():
            if isinstance(value, datetime):
                item[key] = value.isoformat()
            elif isinstance(value, dict):
                for k, v in value.items():
                    if isinstance(v, datetime):
                        item[key][k] = v.isoformat()
    
    return ActivityListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items
    )


@app.get("/api/activities/{activity_id}")
async def get_activity(request: Request, activity_id: str):
    """获取活动详情"""
    data_manager = request.app.state.data_manager
    
    activity = data_manager.get_activity_by_id(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    result = activity.model_dump()
    
    # 处理datetime序列化
    for key, value in result.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, datetime):
                    result[key][k] = v.isoformat()
    
    return result


@app.get("/api/sources", response_model=List[SourceStatusResponse])
async def list_sources(request: Request):
    """获取所有信息源状态"""
    from config import SOURCES_CONFIG
    
    data_manager = request.app.state.data_manager
    
    sources = data_manager.get_sources_status()
    
    return [
        SourceStatusResponse(
            id=s.id,
            name=s.name,
            type=s.type.value if hasattr(s.type, 'value') else s.type,
            category=SOURCES_CONFIG.get(s.id, {}).get('category', 'event'),
            status=s.status.value if hasattr(s.status, 'value') else s.status,
            last_run=s.last_run.isoformat() if s.last_run else None,
            last_success=s.last_success.isoformat() if s.last_success else None,
            activity_count=s.activity_count,
            error_message=s.error_message
        )
        for s in sources
    ]


@app.post("/api/sources/{source_id}/refresh", response_model=RefreshResponse)
async def refresh_source(request: Request, source_id: str):
    """手动刷新指定信息源"""
    scheduler = request.app.state.scheduler
    
    try:
        success = await scheduler.refresh_source(source_id)
        if success:
            return RefreshResponse(
                success=True,
                message=f"Source {source_id} refresh started"
            )
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"Source {source_id} not found"
            )
    except Exception as e:
        logger.error(f"Error refreshing source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sources/refresh-all", response_model=RefreshResponse)
async def refresh_all_sources(request: Request):
    """刷新所有信息源"""
    scheduler = request.app.state.scheduler
    
    try:
        await scheduler.refresh_all()
        return RefreshResponse(
            success=True,
            message="All sources refresh started"
        )
    except Exception as e:
        logger.error(f"Error refreshing all sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(request: Request):
    """获取统计信息"""
    data_manager = request.app.state.data_manager
    
    stats = data_manager.get_stats()
    
    return StatsResponse(
        total_activities=stats.get('total_activities', 0),
        total_sources=stats.get('total_sources', 0),
        activities_by_category=stats.get('activities_by_category', {}),
        activities_by_source=stats.get('activities_by_source', {}),
        last_update=stats.get('last_update')
    )


@app.get("/api/categories")
async def list_categories():
    """获取所有活动类别"""
    return [
        {"value": c.value, "label": c.value.title()}
        for c in Category
    ]


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录API请求日志"""
    start_time = datetime.now()
    
    response = await call_next(request)
    
    duration = (datetime.now() - start_time).total_seconds()
    logger.info(
        f"{request.method} {request.url.path} "
        f"status={response.status_code} duration={duration:.3f}s"
    )
    
    return response
