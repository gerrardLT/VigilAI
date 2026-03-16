"""
VigilAI 主程序入口
启动API服务和任务调度器
"""

import asyncio
import os
import signal
import sys
import logging
from datetime import datetime

import uvicorn

from api import app
from config import API_HOST, API_PORT, DATA_DIR, LOG_LEVEL, LOG_FORMAT
from data_manager import DataManager
from scheduler import TaskScheduler

# 确保数据目录存在（必须在配置日志之前）
os.makedirs(DATA_DIR, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f"{DATA_DIR}/vigilai.log",
            encoding='utf-8'
        )
    ]
)

logger = logging.getLogger(__name__)


class VigilAI:
    """VigilAI应用主类"""
    
    def __init__(self):
        self.data_manager: DataManager = None
        self.scheduler: TaskScheduler = None
        self._shutdown_event = asyncio.Event()
    
    async def startup(self):
        """初始化并启动所有组件"""
        logger.info("=" * 50)
        logger.info("VigilAI - 开发者搞钱机会监控系统")
        logger.info("=" * 50)
        logger.info(f"Starting at {datetime.now().isoformat()}")
        
        # 初始化数据管理器
        logger.info("Initializing DataManager...")
        self.data_manager = DataManager()
        
        # 初始化调度器
        logger.info("Initializing TaskScheduler...")
        self.scheduler = TaskScheduler(self.data_manager)
        
        # 注入依赖到FastAPI
        app.state.data_manager = self.data_manager
        app.state.scheduler = self.scheduler
        
        # 暂时禁用定时任务调度器，仅支持手动刷新
        # logger.info("Starting scheduler...")
        # self.scheduler.start()
        logger.info("Scheduler disabled - manual refresh only")
        
        # 不再自动触发初始数据采集，改为前端手动触发
        # asyncio.create_task(self._initial_refresh())
        
        logger.info(f"VigilAI started successfully")
        logger.info(f"API available at http://{API_HOST}:{API_PORT}")
    
    async def _initial_refresh(self):
        """初始数据采集"""
        try:
            await asyncio.sleep(2)  # 等待服务完全启动
            await self.scheduler.refresh_all()
        except Exception as e:
            logger.error(f"Initial refresh failed: {e}")
    
    async def shutdown(self):
        """优雅关闭所有组件"""
        logger.info("Shutting down VigilAI...")
        
        # 停止调度器
        if self.scheduler:
            self.scheduler.stop()
        
        logger.info("VigilAI shutdown complete")
    
    def handle_signal(self, sig):
        """处理系统信号"""
        logger.info(f"Received signal {sig}, initiating shutdown...")
        self._shutdown_event.set()


async def main():
    """主函数"""
    vigilai = VigilAI()
    
    # 设置信号处理（仅Unix系统）
    if sys.platform != 'win32':
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig, 
                lambda s=sig: vigilai.handle_signal(s)
            )
    
    try:
        # 启动应用
        await vigilai.startup()
        
        # 配置uvicorn
        config = uvicorn.Config(
            app,
            host=API_HOST,
            port=API_PORT,
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)
        
        # 启动服务器
        await server.serve()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise
    finally:
        await vigilai.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nVigilAI stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
