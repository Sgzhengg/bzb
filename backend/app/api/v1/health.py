"""
健康检查接口
"""

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["健康检查"])


@router.get("/health")
async def health_check():
    """
    健康检查接口，返回服务运行状态、LLM配置、爬虫状态等。
    """
    llm_available = bool(settings.LLM_API_KEY)

    return {
        "status": "ok",
        "message": "标中宝服务运行正常",
        "version": "1.0.0",
        "llm": {
            "enabled": settings.LLM_ENABLED,
            "available": llm_available,
            "model": settings.LLM_MODEL,
            "provider": "DeepSeek" if "deepseek" in settings.LLM_API_BASE else "OpenAI",
        },
        "crawler": {
            "enabled": settings.CRAWLER_ENABLED,
            "scheduler": settings.SCHEDULER_ENABLED,
        },
        "database": _mask_url(settings.DATABASE_URL),
    }


def _mask_url(url: str) -> str:
    import re
    return re.sub(r"://[^:]+:[^@]+@", "://***:***@", url)
