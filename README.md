# VigilAI - 开发者搞钱机会监控系统

VigilAI是一个自动化监控系统，帮助开发者追踪各类赚钱机会，包括黑客松、编程竞赛、Web3空投、漏洞赏金、开源资助等。

## 功能特性

- 多源数据采集：支持RSS、网页爬取、API等多种数据源
- 智能去重：基于URL自动去重，避免重复信息
- 定时更新：根据信息源优先级自动调度采集任务
- REST API：提供完整的数据查询和管理接口
- 分类过滤：支持按类别、来源、状态等多维度筛选

## 支持的信息源

- Devpost - 全球黑客松聚合平台
- DoraHacks - Web3黑客松和Grant平台
- Gitcoin - 开源项目资助平台
- Kaggle - 数据科学竞赛平台
- 36氪 - 科技创业媒体
- 虎嗅 - 科技商业媒体

## 技术栈

- Python 3.11+
- FastAPI - Web框架
- SQLite - 数据存储
- APScheduler - 任务调度
- feedparser - RSS解析
- httpx - HTTP客户端
- BeautifulSoup4 - HTML解析

## 快速开始

### 环境准备

```bash
# 创建conda虚拟环境
conda create -n vigilai python=3.11
conda activate vigilai

# 安装依赖
cd app/backend
pip install -r requirements.txt
```

### 启动服务

```bash
cd app/backend
python main.py
```

服务启动后，API将在 http://localhost:8000 可用。

### API端点

- GET /api/activities - 获取活动列表（支持过滤、排序、分页）
- GET /api/activities/{id} - 获取活动详情
- GET /api/sources - 获取信息源状态
- POST /api/sources/{id}/refresh - 刷新指定信息源
- POST /api/sources/refresh-all - 刷新所有信息源
- GET /api/stats - 获取统计信息
- GET /api/categories - 获取活动类别列表
- GET /api/health - 健康检查

### 运行测试

```bash
cd app/backend
python -m pytest tests/ -v
```

## 项目结构

```
app/backend/
├── api.py              # REST API服务
├── config.py           # 配置文件
├── data_manager.py     # 数据管理模块
├── main.py             # 主程序入口
├── models.py           # 数据模型
├── scheduler.py        # 任务调度器
├── requirements.txt    # Python依赖
├── data/               # 数据目录
│   └── vigilai.db      # SQLite数据库
├── scrapers/           # 爬虫模块
│   ├── base.py         # 爬虫基类
│   ├── rss_scraper.py  # RSS爬虫
│   ├── web_scraper.py  # 网页爬虫
│   ├── web3_scraper.py # Web3平台爬虫
│   ├── kaggle_scraper.py    # Kaggle爬虫
│   └── tech_media_scraper.py # 科技媒体爬虫
└── tests/              # 测试目录
    ├── test_models.py
    ├── test_data_manager.py
    └── test_rss_scraper.py
```

## 活动类别

- hackathon - 黑客松
- competition - 编程竞赛
- airdrop - 空投活动
- bounty - 漏洞赏金
- grant - 开源资助
- event - 其他活动

## 配置说明

信息源配置位于 config.py 的 SOURCES_CONFIG 字典中，每个信息源包含：

- name: 显示名称
- type: 类型（rss/web/api）
- url: 数据源URL
- priority: 优先级（high/medium/low）
- enabled: 是否启用
- category: 默认活动类别

优先级对应的更新间隔：
- high: 1小时
- medium: 2小时
- low: 6小时

## 开发计划

- 前端界面开发
- 邮件/微信通知
- 更多信息源支持
- 活动推荐算法
