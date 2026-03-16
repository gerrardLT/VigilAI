# Implementation Plan: VigilAI Core System

## Overview

本实现计划将VigilAI核心系统分解为可执行的编码任务。采用自底向上的方式，先实现基础模块，再逐步构建上层功能。使用Python作为后端开发语言。

## Tasks

- [x] 1. 项目初始化和依赖配置
  - 创建conda虚拟环境：conda create -n vigilai python=3.11
  - 激活环境：conda activate vigilai
  - 创建requirements.txt，包含所有Python依赖
  - 依赖包括：fastapi, uvicorn, pydantic, apscheduler, feedparser, httpx, beautifulsoup4, pytest, hypothesis, pytest-asyncio, lxml, aiosqlite
  - 安装依赖：pip install -r requirements.txt
  - 创建data目录用于存储JSON文件
  - Requirements: 2.1, 2.4

- [x] 2. 数据模型实现
  - [x] 2.1 实现models.py核心数据模型
    - 实现Category, Priority, SourceType, SourceStatus枚举
    - 实现Prize, ActivityDates嵌套模型
    - 实现Activity模型，包含所有必需字段
    - 实现Source模型，包含所有必需字段
    - Requirements: 1.1, 1.2, 1.4, 1.5
  - [x] 2.2 编写模型字段验证属性测试
    - Property 2: Model Field Validation
    - Property 3: Category and Priority Enum Validation
    - Validates: Requirements 1.1, 1.2, 1.4, 1.5

- [x] 3. 配置模块实现
  - [x] 3.1 实现config.py配置文件
    - 定义API_HOST, API_PORT常量
    - 定义DATA_DIR路径
    - 定义PRIORITY_INTERVALS字典
    - 定义SOURCES_CONFIG，包含devpost, dorahacks, gitcoin, 36kr, huxiu等信息源配置
    - 定义LOG_LEVEL, LOG_FORMAT日志配置
    - Requirements: 2.1, 2.2, 2.3, 2.4

- [x] 4. 数据管理模块实现
  - [x] 4.1 实现data_manager.py基础功能
    - 实现DataManager类初始化和数据目录创建
    - 实现_init_db方法创建SQLite数据库和表结构
    - 实现_get_connection上下文管理器，支持事务
    - 实现generate_activity_id静态方法（基于source_id和url生成MD5）
    - 创建activities表和sources表
    - Requirements: 8.1, 8.2, 8.3, 8.4
  - [x] 4.2 实现数据管理CRUD操作
    - 实现add_activity方法，使用INSERT OR REPLACE实现去重
    - 实现get_activities方法，支持SQL过滤、排序、分页
    - 实现get_activity_by_id方法
    - 实现update_source_status方法
    - 实现get_sources_status方法
    - 实现get_stats方法返回统计信息（使用SQL聚合）
    - Requirements: 8.5, 8.6, 9.1, 9.2, 9.3, 9.4
  - [x] 4.3 编写数据管理属性测试
    - Property 1: Activity ID Uniqueness
    - Property 6: Data Persistence Round-Trip
    - Property 7: Deduplication by URL
    - Property 8: Created Timestamp Preservation
    - Validates: Requirements 1.3, 8.5, 8.6, 9.1, 9.2, 9.4

- [x] 5. Checkpoint - 基础模块验证
  - 确保所有测试通过，如有问题请询问用户

- [x] 6. 爬虫基类实现
  - [x] 6.1 实现scrapers/base.py爬虫基类
    - 实现BaseScraper类，包含source_id和config属性
    - 实现generate_activity_id方法
    - 实现抽象scrape方法
    - 实现fetch_url方法，带重试和指数退避
    - 实现User-Agent轮换逻辑
    - Requirements: 4.1, 4.2, 4.3, 4.4

- [x] 7. RSS爬虫实现
  - [x] 7.1 实现scrapers/rss_scraper.py
    - 继承BaseScraper实现RssScraper类
    - 实现scrape方法，使用feedparser解析RSS
    - 实现_parse_entry方法，提取title, description, link, published_date
    - 实现_parse_date方法，支持多种日期格式转换为ISO 8601
    - 实现错误处理，解析失败返回空列表
    - Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
  - [x] 7.2 编写RSS爬虫属性测试
    - Property 4: RSS Parsing Robustness
    - Property 5: RSS Date Normalization
    - Validates: Requirements 3.3, 3.5

- [x] 8. 网页爬虫实现
  - [x] 8.1 实现scrapers/web_scraper.py
    - 继承BaseScraper实现WebScraper类
    - 实现fetch_page方法，带请求延迟
    - 实现parse_html方法，返回BeautifulSoup对象
    - 定义USER_AGENTS列表和REQUEST_DELAY常量
    - Requirements: 4.1, 4.2, 4.3, 4.5

- [x] 9. Web3平台爬虫实现
  - [x] 9.1 实现scrapers/web3_scraper.py
    - 继承WebScraper实现Web3Scraper类
    - 实现scrape_dorahacks方法，爬取DoraHacks黑客松列表
    - 实现scrape_gitcoin方法，爬取Gitcoin Grants
    - 实现_extract_prize方法，从文本提取奖金信息
    - 实现scrape方法，根据source_id调用对应爬取方法
    - Requirements: 5.1, 5.2, 5.3, 5.4

- [x] 10. Kaggle爬虫实现
  - [x] 10.1 实现scrapers/kaggle_scraper.py
    - 继承BaseScraper实现KaggleScraper类
    - 实现scrape方法，使用Kaggle API获取竞赛列表
    - 实现_check_credentials方法，检查API凭证
    - 实现竞赛状态过滤，只返回active和upcoming
    - 无凭证时记录警告并返回空列表
    - Requirements: 6.1, 6.2, 6.3, 6.4

- [x] 11. 科技媒体爬虫实现
  - [x] 11.1 实现scrapers/tech_media_scraper.py
    - 继承RssScraper实现TechMediaScraper类
    - 实现36kr RSS解析
    - 实现Huxiu RSS解析
    - 实现关键词过滤逻辑
    - 实现从文章内容提取活动日期
    - Requirements: 7.1, 7.2, 7.3, 7.4

- [x] 12. Checkpoint - 爬虫模块验证
  - 所有53个测试通过

- [x] 13. 调度器实现
  - [x] 13.1 实现scheduler.py定时调度
    - 实现TaskScheduler类，初始化APScheduler
    - 实现start和stop方法
    - 实现_register_jobs方法，根据配置注册定时任务
    - 实现_run_scraper方法，执行单个爬虫并更新状态
    - 实现refresh_source方法，手动刷新单个信息源
    - 实现refresh_all方法，刷新所有信息源
    - 实现错误处理，任务失败不影响其他任务
    - Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7

- [x] 14. API服务实现
  - [x] 14.1 实现api.py REST接口
    - 创建FastAPI应用实例
    - 配置CORS中间件
    - 实现GET /api/activities端点，支持过滤、排序、分页
    - 实现GET /api/activities/{id}端点
    - 实现GET /api/sources端点
    - 实现POST /api/sources/{id}/refresh端点
    - 实现POST /api/sources/refresh-all端点
    - 实现GET /api/stats端点
    - 实现GET /api/categories端点
    - 实现GET /api/health端点
    - Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9

- [x] 15. 主程序实现
  - [x] 15.1 实现main.py入口程序
    - 实现main异步函数
    - 初始化DataManager
    - 初始化TaskScheduler并注入DataManager
    - 将依赖注入到FastAPI app.state
    - 启动调度器
    - 触发初始数据采集
    - 启动uvicorn服务器
    - 实现信号处理，优雅关闭
    - Requirements: 12.1, 12.2, 12.3, 12.4, 12.5

- [x] 16. 日志配置
  - [x] 16.1 配置日志系统
    - 在config.py添加LOG_LEVEL, LOG_FORMAT配置
    - 在main.py配置日志处理器（控制台+文件）
    - 各模块使用logging.getLogger(__name__)
    - API请求日志中间件记录method, path, status, duration
    - Requirements: 13.1, 13.2, 13.3, 13.5

- [x] 17. Final Checkpoint - 系统集成验证
  - [x] 确保所有测试通过（53个测试全部通过）
  - [x] 验证系统可以正常启动
  - [x] 所有模块导入成功

## Notes

- 所有任务均为必需任务，包括属性测试
- 每个属性测试应运行100+次迭代
- 测试使用pytest和hypothesis框架
- 所有异步代码使用pytest-asyncio测试
