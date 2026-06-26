"""
应用配置模块 — 标中宝 V1 集成版
"""

import os
from typing import List


class Settings:
    """应用配置（支持环境变量覆盖）"""

    PROJECT_NAME: str = os.getenv("BZB_PROJECT_NAME", "标中宝 - 广东移动招标情报系统")
    VERSION: str = os.getenv("BZB_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("BZB_DEBUG", "false").lower() == "true"

    # 数据库配置
    DATABASE_URL: str = os.getenv(
        "BZB_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@db:5432/biaozhongbao",
    )

    # Redis（可选，用于缓存）
    REDIS_URL: str = os.getenv("BZB_REDIS_URL", "")

    # CORS 允许的来源
    ALLOWED_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv(
            "BZB_ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:5173",
        ).split(",")
    ]

    # API 前缀
    API_V1_PREFIX: str = "/api/v1"

    # 爬虫配置
    CRAWLER_ENABLED: bool = os.getenv("BZB_CRAWLER_ENABLED", "true").lower() == "true"
    CRAWLER_MIN_INTERVAL: float = float(os.getenv("BZB_CRAWLER_MIN_INTERVAL", "60"))
    CRAWLER_MAX_PAGES: int = int(os.getenv("BZB_CRAWLER_MAX_PAGES", "3"))

    # 日志配置
    LOG_LEVEL: str = os.getenv("BZB_LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv(
        "BZB_LOG_FORMAT",
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 定时任务
    SCHEDULER_ENABLED: bool = os.getenv("BZB_SCHEDULER_ENABLED", "false").lower() == "true"
    ALERT_BATCH_INTERVAL: int = int(os.getenv("BZB_ALERT_BATCH_INTERVAL", "3600"))


settings = Settings()

