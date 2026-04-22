"""
VigilAI 任务调度器
使用APScheduler实现定时数据采集

增强功能:
- 动态爬虫注册
- 爬虫状态维护
- 告警机制（连续失败3次触发告警，暂停30分钟）

Validates: Requirements 13.1, 13.2, 13.4, 13.5, 11.5, 12.5
"""

import asyncio
import logging
from typing import Dict, Optional, Any, Type
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from analysis.run_manager import AnalysisRunManager
from config import (
    ANALYSIS_SCHEDULE_MAX_ITEMS,
    ANALYSIS_SCHEDULE_STALE_HOURS,
    ANALYSIS_SCHEDULER_ENABLED,
    SOURCES_CONFIG,
    PRIORITY_INTERVALS,
)
from data_manager import DataManager
from models import SourceStatus
from scrapers import (
    BaseScraper, RssScraper, WebScraper, 
    Web3Scraper, KaggleScraper, TechMediaScraper,
    AirdropScraper, DataCompetitionScraper, HackathonAggregatorScraper,
    BountyScraper, EnterpriseScraper, GovernmentScraper,
    DesignCompetitionScraper, CodingCompetitionScraper,
    UniversalScraper
)

logger = logging.getLogger(__name__)


@dataclass
class ScraperState:
    """
    爬虫状态数据类
    Validates: Requirements 13.5
    """
    source_id: str
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    error_count: int = 0
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    last_activity_count: int = 0
    total_activities: int = 0
    is_paused: bool = False
    pause_until: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'source_id': self.source_id,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'last_success': self.last_success.isoformat() if self.last_success else None,
            'error_count': self.error_count,
            'consecutive_failures': self.consecutive_failures,
            'last_error': self.last_error,
            'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None,
            'last_activity_count': self.last_activity_count,
            'total_activities': self.total_activities,
            'is_paused': self.is_paused,
            'pause_until': self.pause_until.isoformat() if self.pause_until else None,
        }


class TaskScheduler:
    """
    任务调度器，管理所有信息源的定时采集
    
    增强功能:
    - 动态爬虫注册 (Validates: Requirements 13.4)
    - 爬虫状态维护 (Validates: Requirements 13.5)
    - 告警机制 (Validates: Requirements 11.5, 12.5)
    """
    
    # 告警阈值：连续失败次数
    FAILURE_ALERT_THRESHOLD = 3
    # 暂停时间（分钟）
    PAUSE_DURATION_MINUTES = 30
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.scheduler = AsyncIOScheduler()
        self.scrapers: Dict[str, BaseScraper] = {}
        self._running = False
        self.analysis_run_manager = AnalysisRunManager(data_manager=data_manager)
        
        # 爬虫状态维护 (Validates: Requirements 13.5)
        self.scraper_states: Dict[str, ScraperState] = {}
        
        # 动态爬虫类型映射 (Validates: Requirements 13.4)
        self._scraper_classes: Dict[str, Type[BaseScraper]] = {
            'rss': RssScraper,
            'web': WebScraper,
            'web3': Web3Scraper,
            'kaggle': KaggleScraper,
            'api': KaggleScraper,
            'tech_media': TechMediaScraper,
            'airdrop': AirdropScraper,
            'data_competition': DataCompetitionScraper,
            'hackathon_aggregator': HackathonAggregatorScraper,
            'bounty': BountyScraper,
            'enterprise': EnterpriseScraper,
            'government': GovernmentScraper,
            'design_competition': DesignCompetitionScraper,
            'coding_competition': CodingCompetitionScraper,
            'universal': UniversalScraper,  # Firecrawl通用爬虫
            'firecrawl': UniversalScraper,  # Firecrawl类型别名
        }
        
        # 告警回调函数列表
        self._alert_callbacks = []
    
    def register_scraper_type(self, scraper_type: str, scraper_class: Type[BaseScraper]) -> None:
        """
        动态注册新的爬虫类型
        Validates: Requirements 13.4
        
        Args:
            scraper_type: 爬虫类型标识
            scraper_class: 爬虫类
        """
        if not issubclass(scraper_class, BaseScraper):
            raise ValueError(f"scraper_class must be a subclass of BaseScraper")
        
        self._scraper_classes[scraper_type] = scraper_class
        logger.info(f"Registered new scraper type: {scraper_type} -> {scraper_class.__name__}")
    
    def unregister_scraper_type(self, scraper_type: str) -> bool:
        """
        注销爬虫类型
        
        Args:
            scraper_type: 爬虫类型标识
            
        Returns:
            是否成功注销
        """
        if scraper_type in self._scraper_classes:
            del self._scraper_classes[scraper_type]
            logger.info(f"Unregistered scraper type: {scraper_type}")
            return True
        return False
    
    def get_registered_types(self) -> Dict[str, str]:
        """获取所有已注册的爬虫类型"""
        return {k: v.__name__ for k, v in self._scraper_classes.items()}
    
    def register_alert_callback(self, callback) -> None:
        """
        注册告警回调函数
        
        Args:
            callback: 回调函数，签名为 callback(source_id: str, state: ScraperState, message: str)
        """
        self._alert_callbacks.append(callback)
    
    def _send_alert(self, source_id: str, state: ScraperState, message: str) -> None:
        """
        发送告警通知
        Validates: Requirements 11.5, 12.5
        
        Args:
            source_id: 信息源ID
            state: 爬虫状态
            message: 告警消息
        """
        # 记录告警日志
        logger.critical(
            f"ALERT: Scraper {source_id} - {message}. "
            f"Consecutive failures: {state.consecutive_failures}, "
            f"Last error: {state.last_error}"
        )
        
        # 调用所有注册的告警回调
        for callback in self._alert_callbacks:
            try:
                callback(source_id, state, message)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def _get_or_create_state(self, source_id: str) -> ScraperState:
        """获取或创建爬虫状态"""
        if source_id not in self.scraper_states:
            self.scraper_states[source_id] = ScraperState(source_id=source_id)
        return self.scraper_states[source_id]
    
    def _check_and_unpause(self, state: ScraperState) -> bool:
        """
        检查是否应该解除暂停
        
        Returns:
            True如果爬虫可以运行，False如果仍在暂停中
        """
        if not state.is_paused:
            return True
        
        now = datetime.utcnow()
        if state.pause_until and now >= state.pause_until:
            # 暂停时间已过，解除暂停
            state.is_paused = False
            state.pause_until = None
            state.consecutive_failures = 0
            logger.info(f"Scraper {state.source_id} unpaused after cooldown period")
            return True
        
        logger.warning(
            f"Scraper {state.source_id} is paused until "
            f"{state.pause_until.isoformat() if state.pause_until else 'unknown'}"
        )
        return False
    
    def _handle_scraper_success(self, source_id: str, activity_count: int) -> None:
        """
        处理爬虫成功
        Validates: Requirements 13.5
        """
        state = self._get_or_create_state(source_id)
        now = datetime.utcnow()
        
        state.last_run = now
        state.last_success = now
        state.consecutive_failures = 0
        state.last_activity_count = activity_count
        state.total_activities += activity_count
        state.is_paused = False
        state.pause_until = None
    
    def _handle_scraper_failure(self, source_id: str, error: str) -> None:
        """
        处理爬虫失败
        Validates: Requirements 11.5, 12.5, 13.5
        """
        state = self._get_or_create_state(source_id)
        now = datetime.utcnow()
        
        state.last_run = now
        state.error_count += 1
        state.consecutive_failures += 1
        state.last_error = error
        state.last_error_time = now
        
        # 检查是否达到告警阈值
        if state.consecutive_failures >= self.FAILURE_ALERT_THRESHOLD:
            # 发送告警
            self._send_alert(
                source_id, 
                state, 
                f"Scraper has failed {state.consecutive_failures} consecutive times"
            )
            
            # 暂停爬虫
            state.is_paused = True
            state.pause_until = now + timedelta(minutes=self.PAUSE_DURATION_MINUTES)
            
            logger.warning(
                f"Scraper {source_id} paused for {self.PAUSE_DURATION_MINUTES} minutes "
                f"due to {state.consecutive_failures} consecutive failures"
            )
    
    def get_scraper_state(self, source_id: str) -> Optional[ScraperState]:
        """获取爬虫状态"""
        return self.scraper_states.get(source_id)
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """获取所有爬虫状态"""
        return {k: v.to_dict() for k, v in self.scraper_states.items()}
    
    def reset_scraper_state(self, source_id: str) -> bool:
        """
        重置爬虫状态
        
        Returns:
            是否成功重置
        """
        if source_id in self.scraper_states:
            self.scraper_states[source_id] = ScraperState(source_id=source_id)
            logger.info(f"Reset state for scraper: {source_id}")
            return True
        return False
    
    def force_unpause(self, source_id: str) -> bool:
        """
        强制解除爬虫暂停
        
        Returns:
            是否成功解除
        """
        state = self.scraper_states.get(source_id)
        if state and state.is_paused:
            state.is_paused = False
            state.pause_until = None
            state.consecutive_failures = 0
            logger.info(f"Force unpaused scraper: {source_id}")
            return True
        return False
    
    def _create_scraper(self, source_id: str, config: dict) -> Optional[BaseScraper]:
        """
        根据配置创建对应类型的爬虫实例
        Validates: Requirements 13.1, 13.2
        """
        source_type = config.get('type', 'rss')
        
        scraper_class = self._scraper_classes.get(source_type)
        if not scraper_class:
            logger.warning(f"Unknown scraper type: {source_type} for {source_id}")
            return None
        
        return scraper_class(source_id, config)
    
    def _register_jobs(self):
        """
        注册所有启用的信息源为定时任务
        """
        for source_id, config in SOURCES_CONFIG.items():
            if not config.get('enabled', True):
                logger.info(f"Skipping disabled source: {source_id}")
                continue
            
            # 创建爬虫实例
            scraper = self._create_scraper(source_id, config)
            if not scraper:
                continue
            
            self.scrapers[source_id] = scraper
            
            # 初始化状态
            self._get_or_create_state(source_id)
            
            # 获取更新间隔
            priority = config.get('priority', 'medium')
            interval = PRIORITY_INTERVALS.get(priority, 7200)
            
            # 注册定时任务
            self.scheduler.add_job(
                self._run_scraper,
                trigger=IntervalTrigger(seconds=interval),
                args=[source_id],
                id=f"scraper_{source_id}",
                name=f"Scrape {config.get('name', source_id)}",
                replace_existing=True
            )
            
            logger.info(
                f"Registered job for {source_id} with interval {interval}s "
                f"(priority: {priority})"
            )
        
        logger.info(f"Registered {len(self.scrapers)} scraper jobs")
    
    async def _run_scraper(self, source_id: str):
        """
        执行单个爬虫任务
        """
        scraper = self.scrapers.get(source_id)
        if not scraper:
            logger.error(f"Scraper not found: {source_id}")
            return
        
        # 检查是否在暂停中
        state = self._get_or_create_state(source_id)
        if not self._check_and_unpause(state):
            return
        
        logger.info(f"Starting scraper: {source_id}")
        
        # 更新状态为运行中
        self.data_manager.update_source_status(
            source_id, 
            SourceStatus.RUNNING
        )
        
        try:
            # 执行爬取
            activities = await scraper.run()
            
            # 保存活动
            added_count = 0
            for activity in activities:
                if self.data_manager.add_activity(activity):
                    added_count += 1
            
            # 更新状态为成功
            self.data_manager.update_source_status(
                source_id,
                SourceStatus.SUCCESS,
                activity_count=len(activities)
            )
            
            # 更新爬虫状态
            self._handle_scraper_success(source_id, len(activities))
            
            logger.info(
                f"Scraper {source_id} completed: "
                f"{len(activities)} activities found, {added_count} new"
            )
            
        except Exception as e:
            # 更新状态为错误
            error_msg = str(e)
            logger.error(f"Scraper {source_id} failed: {error_msg}")
            
            self.data_manager.update_source_status(
                source_id,
                SourceStatus.ERROR,
                error_message=error_msg
            )
            
            # 更新爬虫状态并检查告警
            self._handle_scraper_failure(source_id, error_msg)
    
    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        logger.info("Starting task scheduler...")
        self._register_jobs()
        self.scheduler.start()
        self._running = True
        logger.info("Task scheduler started")
    
    def stop(self):
        """停止调度器"""
        if not self._running:
            return
        
        logger.info("Stopping task scheduler...")
        self.scheduler.shutdown(wait=False)
        self._running = False
        logger.info("Task scheduler stopped")
    
    async def refresh_source(self, source_id: str) -> bool:
        """
        手动刷新指定信息源
        
        Returns:
            是否成功触发刷新
        """
        if source_id not in self.scrapers:
            # 尝试从配置创建爬虫
            config = SOURCES_CONFIG.get(source_id)
            if not config:
                logger.error(f"Source not found: {source_id}")
                return False
            
            scraper = self._create_scraper(source_id, config)
            if not scraper:
                return False
            
            self.scrapers[source_id] = scraper
        
        await self._run_scraper(source_id)
        return True
    
    async def refresh_all(self):
        """刷新所有信息源"""
        logger.info("Refreshing all sources...")
        
        tasks = []
        for source_id in SOURCES_CONFIG.keys():
            config = SOURCES_CONFIG[source_id]
            if config.get('enabled', True):
                # 确保爬虫实例存在
                if source_id not in self.scrapers:
                    scraper = self._create_scraper(source_id, config)
                    if scraper:
                        self.scrapers[source_id] = scraper
                    else:
                        logger.warning(f"Failed to create scraper for {source_id}")
                        continue
                tasks.append(self._run_scraper(source_id))
        
        # 并发执行所有爬虫，但捕获异常避免一个失败影响其他
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 记录失败的任务
        source_ids = [sid for sid in SOURCES_CONFIG.keys() if SOURCES_CONFIG[sid].get('enabled', True) and sid in self.scrapers]
        for source_id, result in zip(source_ids, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to refresh {source_id}: {result}")
        
        logger.info("All sources refresh completed")

    async def run_scheduled_agent_analysis(self):
        """Run scheduled batch agent-analysis when the feature flag is enabled."""
        if not ANALYSIS_SCHEDULER_ENABLED:
            logger.info("Scheduled agent-analysis is disabled by configuration")
            return None

        return self.analysis_run_manager.run_batch_job(
            trigger_type="scheduled",
            max_items=ANALYSIS_SCHEDULE_MAX_ITEMS,
            stale_before_hours=ANALYSIS_SCHEDULE_STALE_HOURS,
        )
    
    def get_job_count(self) -> int:
        """获取已注册的任务数量"""
        return len(self.scheduler.get_jobs())
    
    def get_enabled_source_count(self) -> int:
        """获取启用的信息源数量"""
        return sum(
            1 for config in SOURCES_CONFIG.values() 
            if config.get('enabled', True)
        )
    
    def get_paused_scrapers(self) -> list:
        """获取所有暂停中的爬虫"""
        return [
            state.to_dict() 
            for state in self.scraper_states.values() 
            if state.is_paused
        ]
    
    def get_failed_scrapers(self, min_failures: int = 1) -> list:
        """获取失败次数超过阈值的爬虫"""
        return [
            state.to_dict() 
            for state in self.scraper_states.values() 
            if state.consecutive_failures >= min_failures
        ]
