# Design Document: VigilAI Core System

## Overview

VigilAI是一个开发者搞钱机会监控系统，采用模块化架构设计。系统由数据采集层、数据处理层、存储层、调度层和API服务层组成。本设计文档详细描述各模块的技术实现方案。

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                  │
│         /api/activities  /api/sources  /api/stats       │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│                   Scheduler (APScheduler)               │
│              定时触发各信息源的数据采集任务                │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│                    Scraper Layer                        │
│  ┌──────────┬──────────┬──────────┬──────────┐         │
│  │   RSS    │   Web    │  Web3    │  Kaggle  │         │
│  │ Scraper  │ Scraper  │ Scraper  │ Scraper  │         │
│  └──────────┴──────────┴──────────┴──────────┘         │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│                   DataManager                           │
│          数据存储、去重、查询、状态管理                    │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│                   Storage Layer                         │
│                   vigilai.db (SQLite)                   │
│            activities表    sources表                    │
└─────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Models (models.py)

数据模型定义，使用Pydantic进行数据验证。

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class Category(str, Enum):
    HACKATHON = "hackathon"
    COMPETITION = "competition"
    AIRDROP = "airdrop"
    BOUNTY = "bounty"
    GRANT = "grant"
    EVENT = "event"

class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class SourceType(str, Enum):
    RSS = "rss"
    WEB = "web"
    API = "api"

class SourceStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"

class Prize(BaseModel):
    amount: Optional[float] = None
    currency: str = "USD"
    description: Optional[str] = None

class ActivityDates(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    deadline: Optional[datetime] = None

class Activity(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    source_id: str
    source_name: str
    url: str
    category: Category
    tags: List[str] = []
    prize: Optional[Prize] = None
    dates: Optional[ActivityDates] = None
    location: Optional[str] = None
    organizer: Optional[str] = None
    status: str = "upcoming"
    created_at: datetime
    updated_at: datetime

class Source(BaseModel):
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
```

### 2. Config (config.py)

集中配置管理，定义所有信息源和系统参数。

```python
# API配置
API_HOST = "0.0.0.0"
API_PORT = 8000

# 数据目录
DATA_DIR = "data"

# 优先级对应的更新间隔（秒）
PRIORITY_INTERVALS = {
    "high": 3600,      # 1小时
    "medium": 7200,    # 2小时
    "low": 21600       # 6小时
}

# 信息源配置
SOURCES_CONFIG = {
    "devpost": {
        "name": "Devpost",
        "type": "rss",
        "url": "https://devpost.com/hackathons.rss",
        "priority": "high",
        "enabled": True
    },
    "dorahacks": {
        "name": "DoraHacks",
        "type": "web",
        "url": "https://dorahacks.io/hackathon",
        "priority": "high",
        "enabled": True
    },
    # ... 更多信息源
}
```

### 3. Base Scraper (scrapers/base.py)

爬虫基类，提供通用功能。

```python
class BaseScraper:
    def __init__(self, source_id: str, source_config: dict):
        self.source_id = source_id
        self.config = source_config
        self.session = None
    
    async def scrape(self) -> List[Activity]:
        """子类实现具体爬取逻辑"""
        raise NotImplementedError
    
    def generate_activity_id(self, url: str) -> str:
        """基于source_id和url生成唯一ID"""
        return hashlib.md5(f"{self.source_id}:{url}".encode()).hexdigest()
    
    async def fetch_url(self, url: str, retries: int = 3) -> str:
        """带重试的URL获取"""
        pass
```

### 4. RSS Scraper (scrapers/rss_scraper.py)

RSS订阅源爬虫。

```python
class RssScraper(BaseScraper):
    async def scrape(self) -> List[Activity]:
        """解析RSS feed并返回活动列表"""
        feed = feedparser.parse(self.config["url"])
        activities = []
        for entry in feed.entries:
            activity = self._parse_entry(entry)
            activities.append(activity)
        return activities
    
    def _parse_entry(self, entry) -> Activity:
        """将RSS entry转换为Activity"""
        pass
    
    def _parse_date(self, date_str: str) -> datetime:
        """将各种日期格式转换为datetime"""
        pass
```

### 5. Web Scraper (scrapers/web_scraper.py)

通用网页爬虫。

```python
class WebScraper(BaseScraper):
    USER_AGENTS = [...]  # User-Agent列表
    REQUEST_DELAY = 1.0  # 请求间隔（秒）
    
    async def fetch_page(self, url: str) -> str:
        """获取网页内容，带User-Agent轮换和延迟"""
        pass
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """解析HTML"""
        return BeautifulSoup(html, 'html.parser')
```

### 6. Web3 Scraper (scrapers/web3_scraper.py)

Web3平台爬虫（DoraHacks、Gitcoin等）。

```python
class Web3Scraper(WebScraper):
    async def scrape_dorahacks(self) -> List[Activity]:
        """爬取DoraHacks黑客松列表"""
        pass
    
    async def scrape_gitcoin(self) -> List[Activity]:
        """爬取Gitcoin Grants"""
        pass
    
    def _extract_prize(self, text: str) -> Prize:
        """从文本中提取奖金信息"""
        pass
```

### 7. DataManager (data_manager.py)

数据管理器，使用SQLite存储，负责CRUD操作和去重。

```python
import sqlite3
from contextlib import contextmanager

class DataManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.db_path = os.path.join(data_dir, "vigilai.db")
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS activities (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    source_id TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags TEXT,
                    prize_amount REAL,
                    prize_currency TEXT,
                    prize_description TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    deadline TEXT,
                    location TEXT,
                    organizer TEXT,
                    status TEXT DEFAULT 'upcoming',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(source_id, url)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    update_interval INTEGER NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    last_run TEXT,
                    last_success TEXT,
                    status TEXT DEFAULT 'idle',
                    error_message TEXT,
                    activity_count INTEGER DEFAULT 0
                )
            ''')
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def add_activity(self, activity: Activity) -> bool:
        """添加活动，自动去重（使用UPSERT）"""
        pass
    
    def get_activities(self, filters: dict = None, 
                       sort_by: str = None,
                       page: int = 1, 
                       page_size: int = 20) -> List[Activity]:
        """查询活动列表"""
        pass
    
    def update_source_status(self, source_id: str, 
                             status: SourceStatus,
                             error_message: str = None):
        """更新信息源状态"""
        pass
```

### 8. Scheduler (scheduler.py)

定时任务调度器。

```python
class TaskScheduler:
    def __init__(self, data_manager: DataManager):
        self.scheduler = AsyncIOScheduler()
        self.data_manager = data_manager
        self.scrapers = {}
    
    def start(self):
        """启动调度器"""
        self._register_jobs()
        self.scheduler.start()
    
    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
    
    def _register_jobs(self):
        """注册所有启用的信息源为定时任务"""
        for source_id, config in SOURCES_CONFIG.items():
            if config.get("enabled", True):
                interval = PRIORITY_INTERVALS[config["priority"]]
                self.scheduler.add_job(
                    self._run_scraper,
                    'interval',
                    seconds=interval,
                    args=[source_id]
                )
    
    async def _run_scraper(self, source_id: str):
        """执行单个爬虫任务"""
        pass
    
    async def refresh_source(self, source_id: str):
        """手动刷新指定信息源"""
        pass
    
    async def refresh_all(self):
        """刷新所有信息源"""
        pass
```

### 9. API (api.py)

FastAPI REST接口。

```python
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="VigilAI API")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/activities")
async def list_activities(
    category: Optional[str] = None,
    source_id: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    page: int = 1,
    page_size: int = 20
):
    """获取活动列表"""
    pass

@app.get("/api/activities/{activity_id}")
async def get_activity(activity_id: str):
    """获取活动详情"""
    pass

@app.get("/api/sources")
async def list_sources():
    """获取所有信息源状态"""
    pass

@app.post("/api/sources/{source_id}/refresh")
async def refresh_source(source_id: str):
    """手动刷新指定信息源"""
    pass

@app.post("/api/sources/refresh-all")
async def refresh_all_sources():
    """刷新所有信息源"""
    pass

@app.get("/api/stats")
async def get_stats():
    """获取统计信息"""
    pass
```

### 10. Main (main.py)

主程序入口。

```python
import asyncio
import uvicorn
from api import app
from data_manager import DataManager
from scheduler import TaskScheduler
from config import API_HOST, API_PORT

async def main():
    # 初始化组件
    data_manager = DataManager()
    scheduler = TaskScheduler(data_manager)
    
    # 注入依赖到API
    app.state.data_manager = data_manager
    app.state.scheduler = scheduler
    
    # 启动调度器
    scheduler.start()
    
    # 触发初始数据采集
    await scheduler.refresh_all()
    
    # 启动API服务
    config = uvicorn.Config(app, host=API_HOST, port=API_PORT)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
```

## Data Models

详见Components部分的Models定义。核心模型包括：
- Activity: 活动实体
- Source: 信息源实体
- Prize: 奖金信息
- ActivityDates: 活动时间信息

## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Activity ID Uniqueness
For any two activities with the same source_id and url combination, the generated id should be identical. For any two activities with different source_id or url, the generated id should be different.
Validates: Requirements 1.3

### Property 2: Model Field Validation
For any Activity or Source object, all required fields defined in the model should be present and have valid types.
Validates: Requirements 1.1, 1.2

### Property 3: Category and Priority Enum Validation
For any Activity, the category field should only accept values from the Category enum (hackathon, competition, airdrop, bounty, grant, event). For any Source, the priority field should only accept values from the Priority enum (high, medium, low).
Validates: Requirements 1.4, 1.5

### Property 4: RSS Parsing Robustness
For any malformed or invalid RSS feed content, the RSS_Scraper should return an empty list without raising an exception.
Validates: Requirements 3.3

### Property 5: RSS Date Normalization
For any valid date string in RSS entries (regardless of format), the RSS_Scraper should convert it to ISO 8601 format.
Validates: Requirements 3.5

### Property 6: Data Persistence Round-Trip
For any valid Activity object, storing it via DataManager and then loading it by id should produce an equivalent object.
Validates: Requirements 8.5, 8.6

### Property 7: Deduplication by URL
For any sequence of activities added to DataManager, if two activities have the same url, only one should exist in storage, and the count should not increase on duplicate addition.
Validates: Requirements 9.1, 9.2

### Property 8: Created Timestamp Preservation
For any activity that is updated (duplicate URL), the original created_at timestamp should be preserved while updated_at should change.
Validates: Requirements 9.4

### Property 9: Scheduler Job Registration
For any set of source configurations, the number of registered scheduler jobs should equal the number of enabled sources.
Validates: Requirements 10.2

### Property 10: Scheduler Fault Tolerance
For any scheduled job that fails with an exception, other scheduled jobs should continue to execute normally.
Validates: Requirements 10.6, 13.4

### Property 11: API Filtering Correctness
For any filter parameters (category, source_id, status) applied to the activities endpoint, all returned activities should match the specified filter criteria.
Validates: Requirements 11.7

### Property 12: API Sorting Correctness
For any sort parameter (created_at, deadline, prize) applied to the activities endpoint, the returned activities should be in the correct order.
Validates: Requirements 11.8

## Error Handling

### Scraper Errors
- 网络请求失败：重试3次，指数退避
- 解析错误：记录日志，返回空列表
- 超时：设置合理超时时间，超时后跳过

### DataManager Errors
- 文件读写错误：使用原子写入，失败时保留旧数据
- JSON解析错误：记录日志，初始化空数据

### Scheduler Errors
- 任务执行失败：记录错误，更新source状态，继续其他任务
- 调度器崩溃：主程序捕获异常，尝试重启

### API Errors
- 资源不存在：返回404
- 参数错误：返回400
- 内部错误：返回500，记录详细日志

## Testing Strategy

### Unit Tests
- 模型验证测试
- 日期解析测试
- ID生成测试
- 过滤和排序逻辑测试

### Property-Based Tests
使用hypothesis库进行属性测试：
- 每个属性测试运行100+次迭代
- 测试标注格式：Feature: vigilai-core, Property N: property_text

### Integration Tests
- RSS爬虫集成测试（使用mock数据）
- API端点集成测试
- 调度器集成测试

### Test Configuration
- 测试框架：pytest
- 属性测试：hypothesis
- Mock：pytest-mock, responses
- 异步测试：pytest-asyncio
