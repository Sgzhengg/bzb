"""
健康检查接口
"""

from fastapi import APIRouter

router = APIRouter(tags=["健康检查"])


@router.get("/health")
async def health_check():
    """
    健康检查接口，用于监控服务运行状态
    """
    return {
        "status": "ok",
        "message": "标中宝服务运行正常",
        "version": "1.0.0",
    }
