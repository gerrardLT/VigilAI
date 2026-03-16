"""
VigilAI 数据管理模块
使用SQLite进行数据存储，负责CRUD操作和去重
"""

import os
import sqlite3
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from models import (
    Activity, Source, Prize, ActivityDates,
    Category, Priority, SourceType, SourceStatus,
    ActivityListResponse, StatsResponse
)
from config import DATA_DIR, DB_PATH, SOURCES_CONFIG, PRIORITY_INTERVALS

logger = logging.getLogger(__name__)


class DataManager:
    """数据管理器，使用SQLite存储"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._ensure_data_dir()
        self._init_db()
        self._init_sources()
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        data_dir = os.path.dirname(self.db_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            # 创建activities表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS activities (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    full_content TEXT,
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
                    image_url TEXT,
                    status TEXT DEFAULT 'upcoming',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(source_id, url)
                )
            ''')
            
            # 检查并添加image_url列（兼容旧数据库）
            try:
                conn.execute('ALTER TABLE activities ADD COLUMN image_url TEXT')
                logger.info("Added image_url column to activities table")
            except sqlite3.OperationalError:
                pass  # 列已存在
            
            # 检查并添加full_content列（兼容旧数据库）
            try:
                conn.execute('ALTER TABLE activities ADD COLUMN full_content TEXT')
                logger.info("Added full_content column to activities table")
            except sqlite3.OperationalError:
                pass  # 列已存在
            
            # 创建sources表
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
            
            # 创建索引
            conn.execute('CREATE INDEX IF NOT EXISTS idx_activities_source_id ON activities(source_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_activities_category ON activities(category)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_activities_created_at ON activities(created_at)')
    
    def _init_sources(self):
        """初始化信息源配置到数据库"""
        with self._get_connection() as conn:
            for source_id, config in SOURCES_CONFIG.items():
                # 检查是否已存在
                existing = conn.execute(
                    'SELECT id FROM sources WHERE id = ?', (source_id,)
                ).fetchone()
                
                if not existing:
                    conn.execute('''
                        INSERT INTO sources (id, name, type, url, priority, update_interval, enabled, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        source_id,
                        config['name'],
                        config['type'],
                        config['url'],
                        config['priority'],
                        PRIORITY_INTERVALS.get(config['priority'], 7200),
                        1 if config.get('enabled', True) else 0,
                        'idle'
                    ))
    
    @staticmethod
    def generate_activity_id(source_id: str, url: str) -> str:
        """基于source_id和url生成唯一ID"""
        return hashlib.md5(f"{source_id}:{url}".encode()).hexdigest()

    def add_activity(self, activity: Activity) -> bool:
        """
        添加活动，使用INSERT OR REPLACE实现去重
        如果是更新，保留原始created_at
        返回True表示新增，False表示更新
        """
        with self._get_connection() as conn:
            # 检查是否已存在
            existing = conn.execute(
                'SELECT id, created_at FROM activities WHERE source_id = ? AND url = ?',
                (activity.source_id, activity.url)
            ).fetchone()
            
            is_new = existing is None
            created_at = activity.created_at.isoformat() if is_new else existing['created_at']
            updated_at = datetime.now().isoformat()
            
            # 序列化tags为JSON
            tags_json = json.dumps(activity.tags) if activity.tags else '[]'
            
            # 提取prize信息
            prize_amount = activity.prize.amount if activity.prize else None
            prize_currency = activity.prize.currency if activity.prize else None
            prize_description = activity.prize.description if activity.prize else None
            
            # 提取dates信息
            start_date = activity.dates.start_date.isoformat() if activity.dates and activity.dates.start_date else None
            end_date = activity.dates.end_date.isoformat() if activity.dates and activity.dates.end_date else None
            deadline = activity.dates.deadline.isoformat() if activity.dates and activity.dates.deadline else None
            
            conn.execute('''
                INSERT OR REPLACE INTO activities 
                (id, title, description, full_content, source_id, source_name, url, category, tags,
                 prize_amount, prize_currency, prize_description,
                 start_date, end_date, deadline, location, organizer, image_url, status,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                activity.id,
                activity.title,
                activity.description,
                activity.full_content,
                activity.source_id,
                activity.source_name,
                activity.url,
                activity.category.value,
                tags_json,
                prize_amount,
                prize_currency,
                prize_description,
                start_date,
                end_date,
                deadline,
                activity.location,
                activity.organizer,
                activity.image_url,
                activity.status,
                created_at,
                updated_at
            ))
            
            logger.info(f"{'Added' if is_new else 'Updated'} activity: {activity.title}")
            return is_new
    
    def _row_to_activity(self, row: sqlite3.Row) -> Activity:
        """将数据库行转换为Activity对象"""
        # 解析tags
        tags = json.loads(row['tags']) if row['tags'] else []
        
        # 构建Prize对象
        prize = None
        if row['prize_amount'] is not None or row['prize_currency'] or row['prize_description']:
            prize = Prize(
                amount=row['prize_amount'],
                currency=row['prize_currency'] or 'USD',
                description=row['prize_description']
            )
        
        # 构建ActivityDates对象
        dates = None
        if row['start_date'] or row['end_date'] or row['deadline']:
            dates = ActivityDates(
                start_date=datetime.fromisoformat(row['start_date']) if row['start_date'] else None,
                end_date=datetime.fromisoformat(row['end_date']) if row['end_date'] else None,
                deadline=datetime.fromisoformat(row['deadline']) if row['deadline'] else None
            )
        
        return Activity(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            full_content=row['full_content'] if 'full_content' in row.keys() else None,
            source_id=row['source_id'],
            source_name=row['source_name'],
            url=row['url'],
            category=Category(row['category']),
            tags=tags,
            prize=prize,
            dates=dates,
            location=row['location'],
            organizer=row['organizer'],
            image_url=row['image_url'] if 'image_url' in row.keys() else None,
            status=row['status'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )
    
    def get_activity_by_id(self, activity_id: str) -> Optional[Activity]:
        """根据ID获取活动"""
        with self._get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM activities WHERE id = ?', (activity_id,)
            ).fetchone()
            
            if row:
                return self._row_to_activity(row)
            return None
    
    def get_activities(
        self,
        filters: dict = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20
    ) -> tuple:
        """查询活动列表，支持过滤、排序、分页
        
        Returns:
            (activities, total) 元组
        """
        with self._get_connection() as conn:
            # 构建WHERE子句
            conditions = []
            params = []
            
            if filters:
                if filters.get('category'):
                    conditions.append("category = ?")
                    params.append(filters['category'])
                if filters.get('source_id'):
                    conditions.append("source_id = ?")
                    params.append(filters['source_id'])
                if filters.get('status'):
                    conditions.append("status = ?")
                    params.append(filters['status'])
                if filters.get('search'):
                    conditions.append("(title LIKE ? OR description LIKE ?)")
                    search_term = f"%{filters['search']}%"
                    params.extend([search_term, search_term])
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 验证排序字段
            valid_sort_fields = ["created_at", "updated_at", "deadline", "prize_amount", "title"]
            if sort_by not in valid_sort_fields:
                sort_by = "created_at"
            
            sort_order = "DESC" if sort_order.lower() == "desc" else "ASC"
            
            # 获取总数
            count_query = f"SELECT COUNT(*) as total FROM activities WHERE {where_clause}"
            total = conn.execute(count_query, params).fetchone()['total']
            
            # 计算分页
            offset = (page - 1) * page_size
            
            # 获取数据
            query = f'''
                SELECT * FROM activities 
                WHERE {where_clause}
                ORDER BY {sort_by} {sort_order}
                LIMIT ? OFFSET ?
            '''
            params.extend([page_size, offset])
            
            rows = conn.execute(query, params).fetchall()
            activities = [self._row_to_activity(row) for row in rows]
            
            return activities, total
    
    def get_activities_count(self) -> int:
        """获取活动总数"""
        with self._get_connection() as conn:
            result = conn.execute('SELECT COUNT(*) as count FROM activities').fetchone()
            return result['count']

    def update_source_status(
        self,
        source_id: str,
        status: SourceStatus,
        error_message: str = None,
        activity_count: int = None
    ):
        """更新信息源状态"""
        with self._get_connection() as conn:
            now = datetime.now().isoformat()
            
            updates = ["status = ?", "last_run = ?"]
            params = [status.value, now]
            
            if status == SourceStatus.SUCCESS:
                updates.append("last_success = ?")
                params.append(now)
                updates.append("error_message = NULL")
            
            if status == SourceStatus.ERROR and error_message:
                updates.append("error_message = ?")
                params.append(error_message)
            
            if activity_count is not None:
                updates.append("activity_count = ?")
                params.append(activity_count)
            
            params.append(source_id)
            
            query = f"UPDATE sources SET {', '.join(updates)} WHERE id = ?"
            conn.execute(query, params)
            
            logger.info(f"Updated source {source_id} status to {status.value}")
    
    def get_sources_status(self) -> List[Source]:
        """获取所有信息源状态"""
        with self._get_connection() as conn:
            rows = conn.execute('SELECT * FROM sources ORDER BY priority, name').fetchall()
            
            sources = []
            for row in rows:
                source = Source(
                    id=row['id'],
                    name=row['name'],
                    type=SourceType(row['type']),
                    url=row['url'],
                    priority=Priority(row['priority']),
                    update_interval=row['update_interval'],
                    enabled=bool(row['enabled']),
                    last_run=datetime.fromisoformat(row['last_run']) if row['last_run'] else None,
                    last_success=datetime.fromisoformat(row['last_success']) if row['last_success'] else None,
                    status=SourceStatus(row['status']),
                    error_message=row['error_message'],
                    activity_count=row['activity_count']
                )
                sources.append(source)
            
            return sources
    
    def get_source_by_id(self, source_id: str) -> Optional[Source]:
        """根据ID获取信息源"""
        with self._get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM sources WHERE id = ?', (source_id,)
            ).fetchone()
            
            if row:
                return Source(
                    id=row['id'],
                    name=row['name'],
                    type=SourceType(row['type']),
                    url=row['url'],
                    priority=Priority(row['priority']),
                    update_interval=row['update_interval'],
                    enabled=bool(row['enabled']),
                    last_run=datetime.fromisoformat(row['last_run']) if row['last_run'] else None,
                    last_success=datetime.fromisoformat(row['last_success']) if row['last_success'] else None,
                    status=SourceStatus(row['status']),
                    error_message=row['error_message'],
                    activity_count=row['activity_count']
                )
            return None
    
    def get_enabled_sources(self) -> List[Source]:
        """获取所有启用的信息源"""
        with self._get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM sources WHERE enabled = 1 ORDER BY priority, name'
            ).fetchall()
            
            sources = []
            for row in rows:
                source = Source(
                    id=row['id'],
                    name=row['name'],
                    type=SourceType(row['type']),
                    url=row['url'],
                    priority=Priority(row['priority']),
                    update_interval=row['update_interval'],
                    enabled=True,
                    last_run=datetime.fromisoformat(row['last_run']) if row['last_run'] else None,
                    last_success=datetime.fromisoformat(row['last_success']) if row['last_success'] else None,
                    status=SourceStatus(row['status']),
                    error_message=row['error_message'],
                    activity_count=row['activity_count']
                )
                sources.append(source)
            
            return sources
    
    def get_stats(self) -> StatsResponse:
        """获取统计信息"""
        with self._get_connection() as conn:
            # 总活动数
            total_activities = conn.execute(
                'SELECT COUNT(*) as count FROM activities'
            ).fetchone()['count']
            
            # 总信息源数
            total_sources = conn.execute(
                'SELECT COUNT(*) as count FROM sources'
            ).fetchone()['count']
            
            # 按类别统计
            category_rows = conn.execute('''
                SELECT category, COUNT(*) as count 
                FROM activities 
                GROUP BY category
            ''').fetchall()
            activities_by_category = {row['category']: row['count'] for row in category_rows}
            
            # 按信息源统计
            source_rows = conn.execute('''
                SELECT source_id, COUNT(*) as count 
                FROM activities 
                GROUP BY source_id
            ''').fetchall()
            activities_by_source = {row['source_id']: row['count'] for row in source_rows}
            
            # 最近24小时新增
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            recent_activities = conn.execute(
                'SELECT COUNT(*) as count FROM activities WHERE created_at > ?',
                (yesterday,)
            ).fetchone()['count']
            
            return StatsResponse(
                total_activities=total_activities,
                total_sources=total_sources,
                activities_by_category=activities_by_category,
                activities_by_source=activities_by_source,
                recent_activities=recent_activities
            )
    
    def delete_activity(self, activity_id: str) -> bool:
        """删除活动"""
        with self._get_connection() as conn:
            result = conn.execute(
                'DELETE FROM activities WHERE id = ?', (activity_id,)
            )
            return result.rowcount > 0
    
    def clear_all_activities(self):
        """清空所有活动（用于测试）"""
        with self._get_connection() as conn:
            conn.execute('DELETE FROM activities')
