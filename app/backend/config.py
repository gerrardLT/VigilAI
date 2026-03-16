"""
VigilAI 配置文件
集中管理所有信息源配置和系统参数
"""

import os
from pathlib import Path

# 加载.env文件
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass  # python-dotenv未安装,使用系统环境变量

# Firecrawl配置
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
FIRECRAWL_ENABLED = bool(FIRECRAWL_API_KEY)

# 详情页抓取配置
FETCH_DETAIL_CONTENT = os.getenv("FETCH_DETAIL_CONTENT", "false").lower() == "true"  # 是否抓取详情页内容
DETAIL_FETCH_MAX_COUNT = int(os.getenv("DETAIL_FETCH_MAX_COUNT", "10"))  # 每个信息源最多抓取多少个详情页
DETAIL_FETCH_DELAY = float(os.getenv("DETAIL_FETCH_DELAY", "2.0"))  # 详情页抓取间隔（秒）

# API配置
API_HOST = "0.0.0.0"
API_PORT = 8000

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# 数据库文件路径
DB_PATH = os.path.join(DATA_DIR, "vigilai.db")

# 优先级对应的更新间隔（秒）
PRIORITY_INTERVALS = {
    "high": 3600,      # 1小时
    "medium": 7200,    # 2小时
    "low": 21600       # 6小时
}

# 请求配置
REQUEST_TIMEOUT = 30  # 请求超时时间（秒）
REQUEST_DELAY = 1.0   # 请求间隔（秒）
MAX_RETRIES = 3       # 最大重试次数

# 日志配置
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# User-Agent列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# 活动相关关键词（用于过滤科技媒体文章）
ACTIVITY_KEYWORDS = [
    # 中文关键词
    "黑客松", "hackathon", "编程大赛", "竞赛", "比赛", "挑战赛",
    "空投", "airdrop", "赏金", "bounty", "奖金",
    "资助", "grant", "基金", "激励计划",
    "开发者大赛", "创新大赛", "创业大赛",
    # 英文关键词
    "competition", "challenge", "contest", "prize",
    "funding", "reward", "incentive"
]

# 信息源配置
SOURCES_CONFIG = {
    # ========== 高优先级 - 每小时更新 ==========
    
    # 黑客松聚合平台
    "devpost": {
        "name": "Devpost",
        "type": "firecrawl",
        "url": "https://devpost.com/hackathons",
        "priority": "high",
        "enabled": True,
        "category": "hackathon",
        "description": "全球黑客松聚合平台"
    },
    "dorahacks": {
        "name": "DoraHacks",
        "type": "firecrawl",
        "url": "https://dorahacks.io/hackathon",
        "priority": "high",
        "enabled": True,
        "category": "hackathon",
        "description": "Web3黑客松和Grant平台"
    },
    "mlh": {
        "name": "Major League Hacking",
        "type": "firecrawl",
        "url": "https://mlh.io/seasons/2025/events",
        "priority": "high",
        "enabled": True,
        "category": "hackathon",
        "description": "学生黑客松组织"
    },
    "hackathon_com": {
        "name": "Hackathon.com",
        "type": "firecrawl",
        "url": "https://www.hackathon.com/",
        "priority": "high",
        "enabled": True,
        "category": "hackathon",
        "description": "全球黑客松索引"
    },
    "hackquest": {
        "name": "HackQuest",
        "type": "firecrawl",
        "url": "https://www.hackquest.io/hackathons",
        "priority": "high",
        "enabled": True,
        "category": "hackathon",
        "description": "Web3黑客松和开发者教育平台"
    },
    "taikai": {
        "name": "Taikai",
        "type": "firecrawl",
        "url": "https://taikai.network/en/hackathons",
        "priority": "high",
        "enabled": True,
        "category": "hackathon",
        "description": "区块链黑客松平台"
    },
    "unstop": {
        "name": "Unstop",
        "type": "firecrawl",
        "url": "https://unstop.com/hackathons",
        "priority": "high",
        "enabled": True,
        "category": "hackathon",
        "description": "印度最大的黑客松和竞赛平台"
    },
    
    # Web3空投聚合（极高ROI）
    "airdrops_io": {
        "name": "Airdrops.io",
        "type": "firecrawl",
        "url": "https://airdrops.io/",
        "priority": "high",
        "enabled": True,
        "category": "airdrop",
        "description": "加密货币空投聚合平台"
    },
    "cmc_airdrops": {
        "name": "CoinMarketCap Airdrops",
        "type": "firecrawl",
        "url": "https://coinmarketcap.com/airdrop/",
        "priority": "high",
        "enabled": True,
        "category": "airdrop",
        "description": "CMC空投板块"
    },
    "galxe": {
        "name": "Galxe",
        "type": "firecrawl",
        "url": "https://galxe.com/",
        "priority": "high",
        "enabled": True,
        "category": "airdrop",
        "description": "Web3任务和空投平台"
    },
    
    # 开源/赏金平台
    "gitcoin": {
        "name": "Gitcoin",
        "type": "firecrawl",
        "url": "https://gitcoin.co/grants",
        "priority": "high",
        "enabled": True,
        "category": "grant",
        "description": "开源项目资助平台"
    },
    "immunefi": {
        "name": "Immunefi",
        "type": "firecrawl",
        "url": "https://immunefi.com/explore/",
        "priority": "high",
        "enabled": True,
        "category": "bounty",
        "description": "Web3漏洞赏金平台"
    },
    
    # Web3 Quest任务平台
    "layer3": {
        "name": "Layer3",
        "type": "firecrawl",
        "url": "https://layer3.xyz/quests",
        "priority": "high",
        "enabled": True,
        "category": "quest",
        "description": "Web3任务平台龙头，做任务赚积分和代币"
    },
    
    # 空投聚合补充
    "airdropalert": {
        "name": "AirdropAlert",
        "type": "firecrawl",
        "url": "https://airdropalert.com/",
        "priority": "high",
        "enabled": True,
        "category": "airdrop",
        "description": "老牌空投聚合平台，2017年成立"
    },
    "dappradar_airdrops": {
        "name": "DappRadar Airdrops",
        "type": "firecrawl",
        "url": "https://dappradar.com/airdrops",
        "priority": "high",
        "enabled": True,
        "category": "airdrop",
        "description": "DeFi数据平台的空投板块"
    },
    
    # Web3漏洞赏金补充
    "hackenproof": {
        "name": "HackenProof",
        "type": "firecrawl",
        "url": "https://hackenproof.com/programs",
        "priority": "high",
        "enabled": True,
        "category": "bounty",
        "description": "Web3漏洞赏金平台"
    },
    
    # L2生态Grant
    "arbitrum_grants": {
        "name": "Arbitrum Grants",
        "type": "firecrawl",
        "url": "https://arbitrum.foundation/grants",
        "priority": "high",
        "enabled": True,
        "category": "grant",
        "description": "Arbitrum生态资助计划"
    },
    "optimism_retropgf": {
        "name": "Optimism RetroPGF",
        "type": "firecrawl",
        "url": "https://app.optimism.io/retropgf",
        "priority": "high",
        "enabled": True,
        "category": "grant",
        "description": "Optimism公共物品追溯资助"
    },
    "base_grants": {
        "name": "Base Builder Grants",
        "type": "firecrawl",
        "url": "https://base.org/grants",
        "priority": "high",
        "enabled": True,
        "category": "grant",
        "description": "Base生态建设者资助"
    },
    
    # 中国本土开发者平台
    "heywhale": {
        "name": "和鲸社区",
        "type": "firecrawl",
        "url": "https://www.heywhale.com/home/competition",
        "priority": "high",
        "enabled": True,
        "category": "data_competition",
        "description": "国内数据科学竞赛社区"
    },
    "baidu_aistudio": {
        "name": "飞桨AI Studio",
        "type": "firecrawl",
        "url": "https://aistudio.baidu.com/competition",
        "priority": "high",
        "enabled": True,
        "category": "data_competition",
        "description": "百度AI竞赛平台"
    },
    "xfyun_challenge": {
        "name": "讯飞开放平台",
        "type": "firecrawl",
        "url": "https://challenge.xfyun.cn/",
        "priority": "high",
        "enabled": True,
        "category": "coding_competition",
        "description": "科大讯飞AI开发者大赛"
    },
    "segmentfault": {
        "name": "SegmentFault思否",
        "type": "firecrawl",
        "url": "https://segmentfault.com/events",
        "priority": "high",
        "enabled": True,
        "category": "dev_event",
        "description": "国内开发者社区活动"
    },
    "juejin_events": {
        "name": "掘金活动",
        "type": "firecrawl",
        "url": "https://juejin.cn/events/all",
        "priority": "high",
        "enabled": True,
        "category": "dev_event",
        "description": "掘金开发者活动和竞赛"
    },
    
    # 国内大厂开发者平台
    "tencent_cloud_dev": {
        "name": "腾讯云开发者",
        "type": "firecrawl",
        "url": "https://cloud.tencent.com/developer/competition",
        "priority": "high",
        "enabled": True,
        "category": "coding_competition",
        "description": "腾讯云开发者竞赛"
    },
    "aliyun_dev": {
        "name": "阿里云开发者",
        "type": "firecrawl",
        "url": "https://developer.aliyun.com/activity",
        "priority": "high",
        "enabled": True,
        "category": "dev_event",
        "description": "阿里云开发者活动"
    },
    "bytedance_dev": {
        "name": "字节跳动开放平台",
        "type": "firecrawl",
        "url": "https://open.douyin.com/",
        "priority": "high",
        "enabled": True,
        "category": "dev_event",
        "description": "字节跳动/抖音开发者活动"
    },
    "oppo_dev": {
        "name": "OPPO开放平台",
        "type": "firecrawl",
        "url": "https://open.oppomobile.com/new/activity",
        "priority": "high",
        "enabled": True,
        "category": "dev_event",
        "description": "OPPO开发者活动"
    },
    "vivo_dev": {
        "name": "vivo开放平台",
        "type": "firecrawl",
        "url": "https://dev.vivo.com.cn/",
        "priority": "high",
        "enabled": True,
        "category": "dev_event",
        "description": "vivo开发者活动"
    },
    "xiaomi_dev": {
        "name": "小米开放平台",
        "type": "firecrawl",
        "url": "https://dev.mi.com/",
        "priority": "high",
        "enabled": True,
        "category": "dev_event",
        "description": "小米开发者活动"
    },
    "honor_dev": {
        "name": "荣耀开发者",
        "type": "firecrawl",
        "url": "https://developer.honor.com/cn/activity",
        "priority": "high",
        "enabled": True,
        "category": "dev_event",
        "description": "荣耀开发者活动"
    },
    
    # 国内竞赛聚合平台
    "nowcoder": {
        "name": "牛客竞赛",
        "type": "firecrawl",
        "url": "https://ac.nowcoder.com/acm/contest/vip-index",
        "priority": "high",
        "enabled": True,
        "category": "coding_competition",
        "description": "牛客网编程竞赛"
    },
    "lanqiao": {
        "name": "蓝桥杯",
        "type": "firecrawl",
        "url": "https://dasai.lanqiao.cn/",
        "priority": "high",
        "enabled": True,
        "category": "coding_competition",
        "description": "蓝桥杯全国软件大赛"
    },
    "csdn_dev": {
        "name": "CSDN活动",
        "type": "firecrawl",
        "url": "https://activity.csdn.net/",
        "priority": "high",
        "enabled": True,
        "category": "dev_event",
        "description": "CSDN开发者活动"
    },
    "oschina": {
        "name": "开源中国",
        "type": "firecrawl",
        "url": "https://www.oschina.net/event",
        "priority": "high",
        "enabled": True,
        "category": "dev_event",
        "description": "开源中国活动"
    },
    "infoq_cn": {
        "name": "InfoQ中国",
        "type": "firecrawl",
        "url": "https://www.infoq.cn/conferences/",
        "priority": "high",
        "enabled": True,
        "category": "dev_event",
        "description": "InfoQ技术大会"
    },
    
    # ========== 中优先级 - 每2小时更新 ==========
    
    # 数据科学竞赛
    "kaggle": {
        "name": "Kaggle",
        "type": "kaggle",
        "url": "https://www.kaggle.com/competitions",
        "priority": "medium",
        "enabled": True,
        "category": "data_competition",
        "description": "数据科学竞赛平台"
    },
    "tianchi": {
        "name": "天池",
        "type": "data_competition",
        "url": "https://tianchi.aliyun.com/competition/activeList",
        "priority": "medium",
        "enabled": True,
        "category": "data_competition",
        "description": "阿里云数据竞赛平台"
    },
    "datafountain": {
        "name": "DataFountain",
        "type": "data_competition",
        "url": "https://www.datafountain.cn/competitions",
        "priority": "medium",
        "enabled": True,
        "category": "data_competition",
        "description": "国内数据科学竞赛平台"
    },
    "datacastle": {
        "name": "DataCastle",
        "type": "data_competition",
        "url": "https://www.datacastle.cn/race/list",
        "priority": "medium",
        "enabled": True,
        "category": "data_competition",
        "description": "数据城堡竞赛平台"
    },
    "drivendata": {
        "name": "DrivenData",
        "type": "data_competition",
        "url": "https://www.drivendata.org/competitions/",
        "priority": "medium",
        "enabled": True,
        "category": "data_competition",
        "description": "公益数据科学竞赛"
    },
    
    # 编程竞赛
    "hackerearth": {
        "name": "HackerEarth",
        "type": "coding_competition",
        "url": "https://www.hackerearth.com/challenges/",
        "priority": "medium",
        "enabled": True,
        "category": "coding_competition",
        "description": "编程挑战平台"
    },
    "topcoder": {
        "name": "TopCoder",
        "type": "coding_competition",
        "url": "https://www.topcoder.com/challenges",
        "priority": "medium",
        "enabled": True,
        "category": "coding_competition",
        "description": "众包竞赛平台"
    },
    "microsoft_imagine": {
        "name": "Microsoft Imagine Cup",
        "type": "firecrawl",
        "url": "https://imaginecup.microsoft.com/",
        "priority": "medium",
        "enabled": True,
        "category": "coding_competition",
        "description": "微软学生技术竞赛"
    },
    
    # 开发者活动
    "huawei_dev": {
        "name": "华为开发者",
        "type": "firecrawl",
        "url": "https://developer.huawei.com/consumer/cn/activity/",
        "priority": "medium",
        "enabled": True,
        "category": "dev_event",
        "description": "华为开发者活动"
    },
    "google_startups": {
        "name": "Google for Startups",
        "type": "firecrawl",
        "url": "https://startup.google.com/programs/",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "Google创业支持计划"
    },
    "aws_activate": {
        "name": "AWS Activate",
        "type": "firecrawl",
        "url": "https://aws.amazon.com/startups/",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "AWS创业支持"
    },
    "microsoft_imagine": {
        "name": "Microsoft Imagine Cup",
        "type": "firecrawl",
        "url": "https://imaginecup.microsoft.com/",
        "priority": "medium",
        "enabled": True,
        "category": "coding_competition",
        "description": "微软学生技术竞赛"
    },
    
    # 漏洞赏金
    "hackerone": {
        "name": "HackerOne",
        "type": "firecrawl",
        "url": "https://hackerone.com/directory/programs",
        "priority": "medium",
        "enabled": True,
        "category": "bounty",
        "description": "漏洞赏金平台"
    },
    "bugcrowd": {
        "name": "Bugcrowd",
        "type": "firecrawl",
        "url": "https://www.bugcrowd.com/bug-bounty-list/",
        "priority": "medium",
        "enabled": True,
        "category": "bounty",
        "description": "漏洞赏金平台"
    },
    "code4rena": {
        "name": "Code4rena",
        "type": "firecrawl",
        "url": "https://code4rena.com/contests",
        "priority": "medium",
        "enabled": True,
        "category": "bounty",
        "description": "智能合约审计竞赛"
    },
    
    # 科技新闻媒体
    "36kr": {
        "name": "36氪",
        "type": "rss",
        "url": "https://36kr.com/feed",
        "priority": "medium",
        "enabled": True,
        "category": "news",
        "description": "科技创业媒体"
    },
    "huxiu": {
        "name": "虎嗅",
        "type": "rss",
        "url": "https://www.huxiu.com/rss/0.xml",
        "priority": "medium",
        "enabled": True,
        "category": "news",
        "description": "科技商业媒体"
    },
    "panews": {
        "name": "PANews",
        "type": "firecrawl",
        "url": "https://www.panewslab.com/",
        "priority": "medium",
        "enabled": True,
        "category": "news",
        "description": "Web3资讯媒体"
    },
    
    # ========== 低优先级 - 每6小时更新 ==========
    
    # 以太坊生态
    "ethglobal": {
        "name": "ETHGlobal",
        "type": "firecrawl",
        "url": "https://ethglobal.com/events",
        "priority": "low",
        "enabled": True,
        "category": "hackathon",
        "description": "以太坊黑客松"
    },
    "ethereum_grants": {
        "name": "Ethereum Foundation Grants",
        "type": "firecrawl",
        "url": "https://ethereum.org/en/community/grants/",
        "priority": "low",
        "enabled": True,
        "category": "grant",
        "description": "以太坊基金会资助"
    },
    
    # 其他公链生态
    "solana": {
        "name": "Solana",
        "type": "firecrawl",
        "url": "https://solana.com/community",
        "priority": "low",
        "enabled": True,
        "category": "dev_event",
        "description": "Solana生态活动"
    },
    
    # Web3其他
    "defillama_airdrops": {
        "name": "DeFiLlama Airdrops",
        "type": "firecrawl",
        "url": "https://defillama.com/airdrops",
        "priority": "low",
        "enabled": True,
        "category": "airdrop",
        "description": "DeFi空投聚合"
    },
    "zealy": {
        "name": "Zealy",
        "type": "firecrawl",
        "url": "https://zealy.io/",
        "priority": "low",
        "enabled": True,
        "category": "airdrop",
        "description": "Web3任务平台"
    },
    
    # 其他竞赛（政府/学术/设计）
    "challenge_gov": {
        "name": "Challenge.gov",
        "type": "government",
        "url": "https://www.challenge.gov/",
        "priority": "low",
        "enabled": True,
        "category": "other_competition",
        "description": "美国政府竞赛平台"
    },
    "cxcyds": {
        "name": "中国创新创业大赛",
        "type": "government",
        "url": "http://www.cxcyds.com/",
        "priority": "low",
        "enabled": True,
        "category": "other_competition",
        "description": "国家级创业大赛"
    },
    "cnmaker": {
        "name": "创客中国",
        "type": "government",
        "url": "https://www.cnmaker.org.cn/",
        "priority": "low",
        "enabled": True,
        "category": "other_competition",
        "description": "中小企业创新创业大赛"
    },
    "shejijingsai": {
        "name": "设计竞赛网",
        "type": "design_competition",
        "url": "https://www.shejijingsai.com/",
        "priority": "low",
        "enabled": True,
        "category": "other_competition",
        "description": "设计竞赛聚合"
    },
    
    # 开源赏金
    "issuehunt": {
        "name": "IssueHunt",
        "type": "bounty",
        "url": "https://issuehunt.io/",
        "priority": "low",
        "enabled": True,
        "category": "bounty",
        "description": "GitHub赏金平台"
    },
    "bountysource": {
        "name": "Bountysource",
        "type": "bounty",
        "url": "https://www.bountysource.com/",
        "priority": "low",
        "enabled": True,
        "category": "bounty",
        "description": "开源项目赏金"
    },
    
    # ========== 新增信息源 ==========
    
    # 国内大厂开发者平台补充
    "baidu_dev": {
        "name": "百度开发者",
        "type": "firecrawl",
        "url": "https://developer.baidu.com/",
        "priority": "medium",
        "enabled": True,
        "category": "dev_event",
        "description": "百度开发者中心"
    },
    "jd_open": {
        "name": "京东开放平台",
        "type": "firecrawl",
        "url": "https://open.jd.com/",
        "priority": "medium",
        "enabled": True,
        "category": "dev_event",
        "description": "京东开放平台"
    },
    "meituan_open": {
        "name": "美团开放平台",
        "type": "firecrawl",
        "url": "https://open.meituan.com/",
        "priority": "medium",
        "enabled": True,
        "category": "dev_event",
        "description": "美团开放平台"
    },
    "netease_open": {
        "name": "网易开发者",
        "type": "firecrawl",
        "url": "https://open.163.com/",
        "priority": "medium",
        "enabled": True,
        "category": "dev_event",
        "description": "网易开放平台"
    },
    "kuaishou_open": {
        "name": "快手开放平台",
        "type": "firecrawl",
        "url": "https://open.kuaishou.com/",
        "priority": "medium",
        "enabled": True,
        "category": "dev_event",
        "description": "快手开放平台"
    },
    "weixin_open": {
        "name": "微信开放平台",
        "type": "firecrawl",
        "url": "https://open.weixin.qq.com/",
        "priority": "medium",
        "enabled": True,
        "category": "dev_event",
        "description": "微信开放平台"
    },
    "alipay_open": {
        "name": "支付宝开放平台",
        "type": "firecrawl",
        "url": "https://open.alipay.com/",
        "priority": "medium",
        "enabled": True,
        "category": "dev_event",
        "description": "支付宝开放平台"
    },
    "dingtalk_open": {
        "name": "钉钉开放平台",
        "type": "firecrawl",
        "url": "https://open.dingtalk.com/",
        "priority": "medium",
        "enabled": True,
        "category": "dev_event",
        "description": "钉钉开放平台"
    },
    "feishu_open": {
        "name": "飞书开放平台",
        "type": "firecrawl",
        "url": "https://open.feishu.cn/",
        "priority": "medium",
        "enabled": True,
        "category": "dev_event",
        "description": "飞书开放平台"
    },
    
    # 手机厂商补充
    "samsung_dev": {
        "name": "三星开发者",
        "type": "firecrawl",
        "url": "https://developer.samsung.com/",
        "priority": "medium",
        "enabled": True,
        "category": "dev_event",
        "description": "三星开发者平台"
    },
    "meizu_open": {
        "name": "魅族开放平台",
        "type": "firecrawl",
        "url": "https://open.flyme.cn/",
        "priority": "medium",
        "enabled": True,
        "category": "dev_event",
        "description": "魅族开放平台"
    },
    
    # 云服务商补充
    "google_cloud_dev": {
        "name": "Google Cloud开发者",
        "type": "firecrawl",
        "url": "https://cloud.google.com/developers",
        "priority": "medium",
        "enabled": True,
        "category": "dev_event",
        "description": "Google Cloud开发者"
    },
    "azure_dev": {
        "name": "Azure开发者",
        "type": "firecrawl",
        "url": "https://azure.microsoft.com/en-us/developer/",
        "priority": "medium",
        "enabled": True,
        "category": "dev_event",
        "description": "微软Azure开发者"
    },
    "qiniu": {
        "name": "七牛云",
        "type": "firecrawl",
        "url": "https://www.qiniu.com/activity",
        "priority": "low",
        "enabled": True,
        "category": "dev_event",
        "description": "七牛云活动"
    },
    "upyun": {
        "name": "又拍云",
        "type": "firecrawl",
        "url": "https://www.upyun.com/",
        "priority": "low",
        "enabled": True,
        "category": "dev_event",
        "description": "又拍云"
    },
    "ucloud": {
        "name": "UCloud",
        "type": "firecrawl",
        "url": "https://www.ucloud.cn/",
        "priority": "low",
        "enabled": True,
        "category": "dev_event",
        "description": "UCloud云服务"
    },
    
    # 国内开发者社区补充
    "v2ex": {
        "name": "V2EX",
        "type": "firecrawl",
        "url": "https://www.v2ex.com/",
        "priority": "low",
        "enabled": True,
        "category": "dev_event",
        "description": "V2EX技术社区"
    },
    "cnblogs": {
        "name": "博客园",
        "type": "firecrawl",
        "url": "https://www.cnblogs.com/",
        "priority": "low",
        "enabled": True,
        "category": "dev_event",
        "description": "博客园"
    },
    "gitcode": {
        "name": "GitCode",
        "type": "firecrawl",
        "url": "https://gitcode.com/",
        "priority": "low",
        "enabled": True,
        "category": "dev_event",
        "description": "CSDN GitCode"
    },
    "gitee": {
        "name": "Gitee",
        "type": "firecrawl",
        "url": "https://gitee.com/events",
        "priority": "low",
        "enabled": True,
        "category": "dev_event",
        "description": "Gitee开源活动"
    },
    
    # 国内竞赛补充
    "huaweicloud_competition": {
        "name": "华为云大赛",
        "type": "firecrawl",
        "url": "https://competition.huaweicloud.com/",
        "priority": "medium",
        "enabled": True,
        "category": "coding_competition",
        "description": "华为云开发者大赛"
    },
    "tencent_algo": {
        "name": "腾讯广告算法大赛",
        "type": "firecrawl",
        "url": "https://algo.qq.com/",
        "priority": "medium",
        "enabled": True,
        "category": "data_competition",
        "description": "腾讯广告算法大赛"
    },
    
    # 国际黑客松补充
    "luma": {
        "name": "Luma",
        "type": "firecrawl",
        "url": "https://lu.ma/",
        "priority": "medium",
        "enabled": True,
        "category": "hackathon",
        "description": "活动发现平台"
    },
    "eventbrite": {
        "name": "Eventbrite",
        "type": "firecrawl",
        "url": "https://www.eventbrite.com/d/online/hackathon/",
        "priority": "low",
        "enabled": True,
        "category": "hackathon",
        "description": "活动平台黑客松"
    },
    
    # Web3空投补充
    "cryptorank_airdrops": {
        "name": "CryptoRank Airdrops",
        "type": "firecrawl",
        "url": "https://cryptorank.io/airdrops",
        "priority": "high",
        "enabled": True,
        "category": "airdrop",
        "description": "CryptoRank空投追踪"
    },
    "earnifi": {
        "name": "Earnifi",
        "type": "firecrawl",
        "url": "https://earni.fi/",
        "priority": "high",
        "enabled": True,
        "category": "airdrop",
        "description": "检查钱包可领取空投"
    },
    "dropstab": {
        "name": "DropStab",
        "type": "firecrawl",
        "url": "https://dropstab.com/",
        "priority": "high",
        "enabled": True,
        "category": "airdrop",
        "description": "空投研究和追踪"
    },
    "airdropbob": {
        "name": "AirdropBob",
        "type": "firecrawl",
        "url": "https://airdropbob.com/",
        "priority": "medium",
        "enabled": True,
        "category": "airdrop",
        "description": "空投追踪器"
    },
    
    # Web3 Quest任务平台补充
    "rabbithole": {
        "name": "RabbitHole",
        "type": "firecrawl",
        "url": "https://rabbithole.gg/",
        "priority": "high",
        "enabled": True,
        "category": "quest",
        "description": "链上任务平台"
    },
    "questn": {
        "name": "QuestN",
        "type": "firecrawl",
        "url": "https://questn.com/",
        "priority": "high",
        "enabled": True,
        "category": "quest",
        "description": "Web3任务聚合"
    },
    "taskon": {
        "name": "TaskOn",
        "type": "firecrawl",
        "url": "https://taskon.xyz/",
        "priority": "high",
        "enabled": True,
        "category": "quest",
        "description": "Web3任务平台"
    },
    "intract": {
        "name": "Intract",
        "type": "firecrawl",
        "url": "https://www.intract.io/",
        "priority": "high",
        "enabled": True,
        "category": "quest",
        "description": "新兴Quest平台"
    },
    "port3": {
        "name": "Port3",
        "type": "firecrawl",
        "url": "https://port3.io/",
        "priority": "medium",
        "enabled": True,
        "category": "quest",
        "description": "Web3社交数据平台"
    },
    
    # 漏洞赏金补充
    "sherlock": {
        "name": "Sherlock",
        "type": "firecrawl",
        "url": "https://www.sherlock.xyz/",
        "priority": "medium",
        "enabled": True,
        "category": "bounty",
        "description": "智能合约审计平台"
    },
    "cantina": {
        "name": "Cantina",
        "type": "firecrawl",
        "url": "https://cantina.xyz/",
        "priority": "medium",
        "enabled": True,
        "category": "bounty",
        "description": "Web3审计竞赛"
    },
    "hats_finance": {
        "name": "Hats Finance",
        "type": "firecrawl",
        "url": "https://hats.finance/",
        "priority": "medium",
        "enabled": True,
        "category": "bounty",
        "description": "去中心化漏洞赏金"
    },
    "secure3": {
        "name": "Secure3",
        "type": "firecrawl",
        "url": "https://secure3.io/",
        "priority": "medium",
        "enabled": True,
        "category": "bounty",
        "description": "Web3安全审计"
    },
    "butian": {
        "name": "补天",
        "type": "firecrawl",
        "url": "https://www.butian.net/",
        "priority": "medium",
        "enabled": True,
        "category": "bounty",
        "description": "国内漏洞响应平台"
    },
    "vulbox": {
        "name": "漏洞盒子",
        "type": "firecrawl",
        "url": "https://www.vulbox.com/",
        "priority": "medium",
        "enabled": True,
        "category": "bounty",
        "description": "国内漏洞赏金平台"
    },
    
    # 开源赏金补充
    "bountyhub": {
        "name": "BountyHub",
        "type": "firecrawl",
        "url": "https://www.bountyhub.dev/",
        "priority": "low",
        "enabled": True,
        "category": "bounty",
        "description": "GitHub赏金平台"
    },
    "codebounty": {
        "name": "CodeBounty",
        "type": "firecrawl",
        "url": "https://www.codebounty.ai/",
        "priority": "low",
        "enabled": True,
        "category": "bounty",
        "description": "AI驱动的代码赏金"
    },
    
    # 公链生态Grant补充
    "polygon_grants": {
        "name": "Polygon Grants",
        "type": "firecrawl",
        "url": "https://polygon.technology/village/grants",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "Polygon生态资助"
    },
    "solana_grants": {
        "name": "Solana Grants",
        "type": "firecrawl",
        "url": "https://solana.org/grants",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "Solana生态资助"
    },
    "sui_grants": {
        "name": "Sui Grants",
        "type": "firecrawl",
        "url": "https://sui.io/grants",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "Sui生态资助"
    },
    "aptos_grants": {
        "name": "Aptos Grants",
        "type": "firecrawl",
        "url": "https://aptosfoundation.org/grants",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "Aptos生态资助"
    },
    "near_grants": {
        "name": "Near Grants",
        "type": "firecrawl",
        "url": "https://near.org/ecosystem/grants",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "Near生态资助"
    },
    "cosmos_grants": {
        "name": "Cosmos Grants",
        "type": "firecrawl",
        "url": "https://interchain.io/grants",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "Cosmos生态资助"
    },
    "polkadot_treasury": {
        "name": "Polkadot Treasury",
        "type": "firecrawl",
        "url": "https://polkadot.network/ecosystem/treasury/",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "Polkadot国库资助"
    },
    "avalanche_grants": {
        "name": "Avalanche Grants",
        "type": "firecrawl",
        "url": "https://www.avax.network/grants",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "Avalanche生态资助"
    },
    "bnb_grants": {
        "name": "BNB Chain Grants",
        "type": "firecrawl",
        "url": "https://www.bnbchain.org/en/bsc-mvb-program",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "BNB Chain生态资助"
    },
    "zksync_grants": {
        "name": "zkSync Grants",
        "type": "firecrawl",
        "url": "https://zksync.io/grants",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "zkSync生态资助"
    },
    "starknet_grants": {
        "name": "Starknet Grants",
        "type": "firecrawl",
        "url": "https://www.starknet.io/grants/",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "Starknet生态资助"
    },
    "scroll_grants": {
        "name": "Scroll Grants",
        "type": "firecrawl",
        "url": "https://scroll.io/grants",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "Scroll生态资助"
    },
    "linea_grants": {
        "name": "Linea Grants",
        "type": "firecrawl",
        "url": "https://linea.build/grants",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "Linea生态资助"
    },
    "mantle_grants": {
        "name": "Mantle Grants",
        "type": "firecrawl",
        "url": "https://www.mantle.xyz/grants",
        "priority": "medium",
        "enabled": True,
        "category": "grant",
        "description": "Mantle生态资助"
    },
    
    # 设计竞赛补充
    "zcool": {
        "name": "站酷",
        "type": "firecrawl",
        "url": "https://www.zcool.com.cn/",
        "priority": "low",
        "enabled": True,
        "category": "design_competition",
        "description": "站酷设计社区"
    },
    "dribbble": {
        "name": "Dribbble",
        "type": "firecrawl",
        "url": "https://dribbble.com/",
        "priority": "low",
        "enabled": True,
        "category": "design_competition",
        "description": "设计师社区"
    },
    "behance": {
        "name": "Behance",
        "type": "firecrawl",
        "url": "https://www.behance.net/",
        "priority": "low",
        "enabled": True,
        "category": "design_competition",
        "description": "Adobe设计社区"
    },
    "99designs": {
        "name": "99designs",
        "type": "firecrawl",
        "url": "https://99designs.com/",
        "priority": "low",
        "enabled": True,
        "category": "design_competition",
        "description": "设计众包平台"
    },
    
    # 创业/孵化平台补充
    "ycombinator": {
        "name": "Y Combinator",
        "type": "firecrawl",
        "url": "https://www.ycombinator.com/",
        "priority": "low",
        "enabled": True,
        "category": "grant",
        "description": "顶级创业孵化器"
    },
    "cyzone": {
        "name": "创业邦",
        "type": "firecrawl",
        "url": "https://www.cyzone.cn/",
        "priority": "low",
        "enabled": True,
        "category": "news",
        "description": "创业媒体"
    },
    "lieyunwang": {
        "name": "猎云网",
        "type": "firecrawl",
        "url": "https://www.lieyunwang.com/",
        "priority": "low",
        "enabled": True,
        "category": "news",
        "description": "创投媒体"
    },
    
    # 政府/学术竞赛补充
    "internet_plus": {
        "name": "互联网+大赛",
        "type": "firecrawl",
        "url": "https://cy.ncss.cn/",
        "priority": "low",
        "enabled": True,
        "category": "other_competition",
        "description": "中国互联网+大学生创新创业大赛"
    },
    "tiaozhanbei": {
        "name": "挑战杯",
        "type": "firecrawl",
        "url": "https://www.tiaozhanbei.net/",
        "priority": "low",
        "enabled": True,
        "category": "other_competition",
        "description": "挑战杯全国大学生课外学术科技作品竞赛"
    },
    
    # 交易所活动
    "binance_activity": {
        "name": "Binance活动",
        "type": "firecrawl",
        "url": "https://www.binance.com/en/activity",
        "priority": "high",
        "enabled": True,
        "category": "airdrop",
        "description": "币安交易所活动"
    },
    "okx_activity": {
        "name": "OKX活动",
        "type": "firecrawl",
        "url": "https://www.okx.com/activities",
        "priority": "high",
        "enabled": True,
        "category": "airdrop",
        "description": "OKX交易所活动"
    },
    "bybit_rewards": {
        "name": "Bybit奖励",
        "type": "firecrawl",
        "url": "https://www.bybit.com/en/promo/rewards-hub/",
        "priority": "high",
        "enabled": True,
        "category": "airdrop",
        "description": "Bybit交易所奖励"
    },
    "gate_activity": {
        "name": "Gate.io活动",
        "type": "firecrawl",
        "url": "https://www.gate.io/activities",
        "priority": "medium",
        "enabled": True,
        "category": "airdrop",
        "description": "Gate.io交易所活动"
    },
    "bitget_activity": {
        "name": "Bitget活动",
        "type": "firecrawl",
        "url": "https://www.bitget.com/activities",
        "priority": "medium",
        "enabled": True,
        "category": "airdrop",
        "description": "Bitget交易所活动"
    },
    "mexc_activity": {
        "name": "MEXC活动",
        "type": "firecrawl",
        "url": "https://www.mexc.com/activity",
        "priority": "medium",
        "enabled": True,
        "category": "airdrop",
        "description": "MEXC交易所活动"
    },
    "kucoin_activity": {
        "name": "KuCoin活动",
        "type": "firecrawl",
        "url": "https://www.kucoin.com/activity",
        "priority": "medium",
        "enabled": True,
        "category": "airdrop",
        "description": "KuCoin交易所活动"
    },
    
    # Testnet/积分农场
    "monad_testnet": {
        "name": "Monad",
        "type": "firecrawl",
        "url": "https://monad.xyz/",
        "priority": "high",
        "enabled": True,
        "category": "testnet",
        "description": "Monad测试网"
    },
    "berachain_testnet": {
        "name": "Berachain",
        "type": "firecrawl",
        "url": "https://berachain.com/",
        "priority": "high",
        "enabled": True,
        "category": "testnet",
        "description": "Berachain测试网"
    },
    "movement_testnet": {
        "name": "Movement",
        "type": "firecrawl",
        "url": "https://movementlabs.xyz/",
        "priority": "high",
        "enabled": True,
        "category": "testnet",
        "description": "Movement测试网"
    },
    "fuel_testnet": {
        "name": "Fuel",
        "type": "firecrawl",
        "url": "https://fuel.network/",
        "priority": "medium",
        "enabled": True,
        "category": "testnet",
        "description": "Fuel模块化执行层"
    },
    "eclipse_testnet": {
        "name": "Eclipse",
        "type": "firecrawl",
        "url": "https://eclipse.xyz/",
        "priority": "medium",
        "enabled": True,
        "category": "testnet",
        "description": "Eclipse SVM L2"
    },
    "hyperliquid": {
        "name": "Hyperliquid",
        "type": "firecrawl",
        "url": "https://hyperliquid.xyz/",
        "priority": "high",
        "enabled": True,
        "category": "testnet",
        "description": "Hyperliquid永续DEX积分"
    },
}


def get_source_config(source_id: str) -> dict:
    """获取指定信息源的配置"""
    return SOURCES_CONFIG.get(source_id)


def get_enabled_sources() -> dict:
    """获取所有启用的信息源"""
    return {k: v for k, v in SOURCES_CONFIG.items() if v.get("enabled", True)}


def get_sources_by_priority(priority: str) -> dict:
    """获取指定优先级的信息源"""
    return {k: v for k, v in SOURCES_CONFIG.items() 
            if v.get("priority") == priority and v.get("enabled", True)}


def get_update_interval(priority: str) -> int:
    """获取指定优先级的更新间隔"""
    return PRIORITY_INTERVALS.get(priority, PRIORITY_INTERVALS["medium"])
