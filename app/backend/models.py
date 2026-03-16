"""
VigilAI 数据模型定义
使用Pydantic进行数据验证
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import hashlib


class Category(str, Enum):
    """活动类型枚举"""
    HACKATHON = "hackathon"  # 黑客松
    DATA_COMPETITION = "data_competition"  # 数据竞赛
    CODING_COMPETITION = "coding_competition"  # 编程竞赛
    OTHER_COMPETITION = "other_competition"  # 其他竞赛（设计、政府等）
    AIRDROP = "airdrop"  # 空投
    BOUNTY = "bounty"  # 赏金
    GRANT = "grant"  # 资助
    DEV_EVENT = "dev_event"  # 开发者活动
    NEWS = "news"  # 科技新闻


class Priority(str, Enum):
    """信息源优先级枚举"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceType(str, Enum):
    """信息源类型枚举"""
    RSS = "rss"
    WEB = "web"
    API = "api"
    FIRECRAWL = "firecrawl"
    KAGGLE = "kaggle"
    TECH_MEDIA = "tech_media"
    AIRDROP = "airdrop"
    DATA_COMPETITION = "data_competition"
    HACKATHON_AGGREGATOR = "hackathon_aggregator"
    BOUNTY = "bounty"
    ENTERPRISE = "enterprise"
    GOVERNMENT = "government"
    DESIGN_COMPETITION = "design_competition"
    CODING_COMPETITION = "coding_competition"
    UNIVERSAL = "universal"


class SourceStatus(str, Enum):
    """信息源状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class Prize(BaseModel):
    """奖金信息模型"""
    amount: Optional[float] = None
    currency: str = "USD"
    description: Optional[str] = None


class ActivityDates(BaseModel):
    """活动时间信息模型"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    deadline: Optional[datetime] = None


class Activity(BaseModel):
    """活动实体模型"""
    id: str
    title: str
    description: Optional[str] = None
    full_content: Optional[str] = None  # 活动详细内容（从详情页抓取）
    source_id: str
    source_name: str
    url: str
    category: Category
    tags: List[str] = Field(default_factory=list)
    prize: Optional[Prize] = None
    dates: Optional[ActivityDates] = None
    location: Optional[str] = None
    organizer: Optional[str] = None
    image_url: Optional[str] = None  # 活动封面图片URL
    status: str = "upcoming"
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def generate_id(source_id: str, url: str) -> str:
        """基于source_id和url生成唯一ID"""
        return hashlib.md5(f"{source_id}:{url}".encode()).hexdigest()


class Source(BaseModel):
    """信息源实体模型"""
    id: str
    name: str
    type: SourceType
    url: str
    priority: Priority
    update_interval: int
    enabled: bool = True
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    status: SourceStatus = SourceStatus.IDLE
    error_message: Optional[str] = None
    activity_count: int = 0


class ActivityListResponse(BaseModel):
    """活动列表响应模型"""
    items: List[Activity]
    total: int
    page: int
    page_size: int
    total_pages: int


class StatsResponse(BaseModel):
    """统计信息响应模型"""
    total_activities: int
    total_sources: int
    activities_by_category: dict
    activities_by_source: dict
    recent_activities: int
