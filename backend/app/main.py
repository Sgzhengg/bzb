"""
标中宝 V1 — 广东移动招标情报系统
FastAPI 集成主程序入口

启动方式:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

环境变量（可选）:
    BZB_DATABASE_URL       数据库连接串
    BZB_DEBUG              调试模式 true/false
    BZB_CRAWLER_ENABLED    爬虫开关 true/false
    BZB_LOG_LEVEL          日志级别
    BZB_ALLOWED_ORIGINS    CORS 来源（逗号分隔）
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.v1.health import router as health_router
from app.api.v1.relations import router as relations_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.purchasers import router as purchasers_router
from app.api.v1.announcements import router as announcements_router
from app.api.v1.scheduler_api import router as scheduler_router
from app.api.v1.charts import router as charts_router
from app.api.v1.preferences import router as preferences_router

# ============================================================
# 日志配置
# ============================================================

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format=settings.LOG_FORMAT,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


# ============================================================
# 应用生命周期
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期管理（FastAPI 0.95+ 风格）。"""
    logger.info("=" * 55)
    logger.info(f"  🚀 {settings.PROJECT_NAME} V{settings.VERSION}")
    logger.info(f"  📡 API 文档: http://0.0.0.0:8000/docs")
    logger.info(f"  🗄️ 数据库:   {_mask_url(settings.DATABASE_URL)}")
    logger.info(f"  🔧 调试模式: {'ON' if settings.DEBUG else 'OFF'}")
    logger.info(f"  🕷️ 爬虫:     {'启用' if settings.CRAWLER_ENABLED else '禁用'}")
    logger.info(f"  📋 日志级别: {settings.LOG_LEVEL}")
    logger.info("=" * 55)

    if settings.SCHEDULER_ENABLED:
        from app.services.scheduler import start_scheduler
        start_scheduler()

    # 确保所有表已创建（包括 user_preferences）
    from app.models.base import Base
    from app.db.session import engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    logger.info(f"👋 {settings.PROJECT_NAME} 正在关闭...")


def _mask_url(url: str) -> str:
    import re
    return re.sub(r"://[^:]+:[^@]+@", "://***:***@", url)


# ============================================================
# 创建 FastAPI 应用
# ============================================================

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "广东移动广告招标信息收集、分析及筛选系统。\n\n"
        "## 功能模块\n"
        "- 📋 **招标公告管理** — 列表/详情/采集触发\n"
        "- 👤 **客情管理** — CRUD + 评级排序 + 今日提醒\n"
        "- 🔔 **关联提醒** — 公告入库自动关联客情\n"
        "- 🏦 **采购方画像** — 竞争格局分析报告\n"
        "- 📍 **地市对比** — 21地市横向对比看板\n"
        "- ⚖️ **机会评分** — 6维度加权评分引擎"
    ),
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ============================================================
# CORS 中间件
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)


# ============================================================
# 统一错误处理
# ============================================================

@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception(f"未捕获异常: {request.method} {request.url.path}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "服务器内部错误",
                "error": str(exc) if settings.DEBUG else "请查看服务端日志",
            },
        )


# ============================================================
# 注册全部 API 路由
# ============================================================

API_PREFIX = settings.API_V1_PREFIX

app.include_router(health_router, prefix=API_PREFIX)
app.include_router(relations_router, prefix=API_PREFIX)
app.include_router(alerts_router, prefix=API_PREFIX)
app.include_router(purchasers_router, prefix=API_PREFIX)
app.include_router(announcements_router, prefix=API_PREFIX)
app.include_router(scheduler_router, prefix=API_PREFIX)
app.include_router(charts_router, prefix=API_PREFIX)
app.include_router(preferences_router, prefix=API_PREFIX)

logger.info("已注册路由: health/relations/alerts/purchasers/announcements/scheduler/charts/preferences")


# ============================================================
# 根路径
# ============================================================

@app.get("/", tags=["系统"])
async def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
    }


# 定时任务调度器已迁移至 app/services/scheduler.py
# 通过 BZB_SCHEDULER_ENABLED=true 环境变量启用
# 控制接口: GET/POST /api/v1/scheduler/*
