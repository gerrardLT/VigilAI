"""
VigilAI 配置管理 - 基于 pydantic-settings 的类型安全配置

使用 pydantic-settings BaseSettings 提供：
- 类型安全的环境变量读取
- 启动时验证（fail-fast）
- 必需 vs 可选配置的明确区分
- .env 文件自动加载

所有字段均有默认值，确保现有部署不会因缺少环境变量而中断。
"""

import os
from functools import cached_property

import yaml
from pydantic_settings import BaseSettings
from pydantic import Field


class DuplicateKeyError(ValueError):
    """YAML 配置文件中检测到重复键时抛出。"""
    pass


def _check_duplicate_keys(loader, node):
    """自定义 YAML 构造器，检测并拒绝重复键。"""
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in mapping:
            raise DuplicateKeyError(f"Duplicate key in sources config: '{key}'")
        mapping[key] = loader.construct_object(value_node)
    return mapping


class Settings(BaseSettings):
    """VigilAI 应用配置，从环境变量和 .env 文件加载。"""

    # ─── Security ───────────────────────────────────────────────────────
    # 逗号分隔的 API 密钥列表，为空表示禁用认证
    api_keys: str = ""
    # 逗号分隔的允许 CORS 来源
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:8000"
    # 标准端点速率限制（每分钟请求数）
    rate_limit_standard: int = 60
    # Agent 端点速率限制（每分钟请求数）
    rate_limit_agent: int = 10
    # Agent 消息最大字符数
    max_input_length: int = 10000
    # 请求体最大字节数（1MB）
    max_body_size: int = 1048576

    # ─── Database ───────────────────────────────────────────────────────
    db_path: str = "data/vigilai.db"
    db_pool_size: int = 5
    db_idle_timeout: int = 300

    # ─── API Server ─────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ─── Firecrawl (optional) ──────────────────────────────────────────
    firecrawl_api_key: str = ""
    firecrawl_api_keys: str = ""

    # ─── OpenAI (optional) ─────────────────────────────────────────────
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    # ─── DashScope (optional) ──────────────────────────────────────────
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # ─── AI Filter ─────────────────────────────────────────────────────
    ai_filter_enabled: bool = False
    ai_filter_model: str = "gpt-4.1-mini"
    ai_filter_max_candidates: int = 200
    ai_filter_timeout_seconds: float = 30.0

    # ─── Reward Agent ──────────────────────────────────────────────────
    reward_agent_provider: str = "openai"
    reward_agent_model: str = "gpt-4.1-mini"
    reward_agent_timeout_seconds: float = 30.0
    reward_agent_allow_baseline_fallback: bool = False
    reward_agent_allow_mock_documents: bool = False
    reward_agent_browser_enabled: bool = True
    reward_agent_langsmith_enabled: bool = False

    # ─── Scheduler ─────────────────────────────────────────────────────
    app_scheduler_enabled: bool = False
    enable_reward_scheduler: bool = False

    # ─── Analysis ──────────────────────────────────────────────────────
    analysis_provider: str = "mock"
    analysis_scheduler_enabled: bool = False
    analysis_schedule_max_items: int = 25
    analysis_schedule_stale_hours: int = 72

    # ─── Product Selection ─────────────────────────────────────────────
    product_selection_live_enabled: bool = True
    product_selection_live_result_limit: int = 6
    product_selection_live_timeout_seconds: float = 20.0

    # ─── Sources Config ────────────────────────────────────────────────
    sources_config_path: str = "sources.yaml"

    # ─── Logging ───────────────────────────────────────────────────────
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def parsed_api_keys(self) -> list[str]:
        """解析逗号分隔的 API 密钥为列表。"""
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    @property
    def parsed_cors_origins(self) -> list[str]:
        """解析逗号分隔的 CORS 来源为列表。"""
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @cached_property
    def sources_config(self) -> dict:
        """加载并验证 YAML 信息源配置文件，检测重复键。"""
        path = self.sources_config_path

        if not os.path.exists(path):
            # 尝试相对于本文件目录查找
            alt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
            if os.path.exists(alt_path):
                path = alt_path
            else:
                raise ValueError(f"Sources config file not found: {self.sources_config_path}")

        # 创建自定义 SafeLoader，检测重复键
        class SafeLoaderNoDuplicates(yaml.SafeLoader):
            pass

        SafeLoaderNoDuplicates.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            _check_duplicate_keys,
        )

        with open(path, encoding="utf-8") as f:
            try:
                data = yaml.load(f, Loader=SafeLoaderNoDuplicates)
            except yaml.YAMLError as e:
                raise ValueError(f"Malformed sources config: {e}") from e

        if not isinstance(data, dict) or "sources" not in data:
            raise ValueError("Sources config must contain a 'sources' key")

        return data["sources"]


# Singleton 实例 - 在模块导入时创建，提供 fail-fast 启动验证
settings = Settings()
