"""
应用配置模块 — 标中宝 V1 集成版
"""

import os
from pathlib import Path
from typing import List

# 自动加载 .env 文件
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass


class Settings:
    """应用配置（支持环境变量覆盖）"""

    PROJECT_NAME: str = os.getenv("BZB_PROJECT_NAME", "标中宝 - 全国移动招标情报系统")
    VERSION: str = os.getenv("BZB_VERSION", "2.0.0")
    DEBUG: bool = os.getenv("BZB_DEBUG", "false").lower() == "true"

    # 数据库配置
    # 默认路径基于 config.py 所在位置（app/core/）向上两级到 backend/ 目录
    # 这样无论从哪个目录启动 uvicorn，都能正确找到数据库文件
    _DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
    _DEFAULT_DB_PATH = (_DEFAULT_DB_DIR / "biaozhongbao.db").as_posix()
    DATABASE_URL: str = os.getenv(
        "BZB_DATABASE_URL",
        f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}",
    )

    # Redis（可选，用于缓存）
    REDIS_URL: str = os.getenv("BZB_REDIS_URL", "")

    # CORS 允许的来源
    ALLOWED_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv(
            "BZB_ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:3001,http://localhost:3005,http://localhost:5173",
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
    LOG_FILE: str = os.getenv("BZB_LOG_FILE", "")
    LOG_MAX_BYTES: int = int(os.getenv("BZB_LOG_MAX_BYTES", "10485760"))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv("BZB_LOG_BACKUP_COUNT", "5"))

    # LLM 配置
    LLM_ENABLED: bool = os.getenv("BZB_LLM_ENABLED", "true").lower() == "true"
    LLM_API_BASE: str = os.getenv("BZB_LLM_API_BASE", "https://api.deepseek.com/v1")
    LLM_API_KEY: str = os.getenv("BZB_LLM_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))
    LLM_MODEL: str = os.getenv("BZB_LLM_MODEL", "deepseek-chat")
    LLM_TEMPERATURE: float = float(os.getenv("BZB_LLM_TEMPERATURE", "0.3"))
    LLM_MAX_TOKENS: int = int(os.getenv("BZB_LLM_MAX_TOKENS", "2000"))

    # 定时任务
    SCHEDULER_ENABLED: bool = os.getenv("BZB_SCHEDULER_ENABLED", "false").lower() == "true"
    ALERT_BATCH_INTERVAL: int = int(os.getenv("BZB_ALERT_BATCH_INTERVAL", "3600"))

    # 钉钉机器人通知
    DINGTALK_WEBHOOK_URL: str = os.getenv("BZB_DINGTALK_WEBHOOK_URL", "")
    SITE_URL: str = os.getenv("BZB_SITE_URL", "http://localhost:3000")


settings = Settings()

