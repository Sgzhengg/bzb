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
import uuid
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.api.v1.health import router as health_router
from app.api.v1.relations import router as relations_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.purchasers import router as purchasers_router
from app.api.v1.announcements import router as announcements_router
from app.api.v1.scheduler_api import router as scheduler_router
from app.api.v1.charts import router as charts_router
from app.api.v1.preferences import router as preferences_router
from app.api.v1.awards import router as awards_router
from app.api.v1.overview import router as overview_router

# ============================================================
# 日志配置（支持文件轮转）
# ============================================================

log_handlers = [logging.StreamHandler(sys.stdout)]

if settings.LOG_FILE:
    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(settings.LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))
    log_handlers.append(file_handler)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format=settings.LOG_FORMAT,
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=log_handlers,
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

    # 初始化 Redis 缓存
    from app.services.cache_service import init_cache
    await init_cache()

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

    # 关闭 Redis 缓存
    from app.services.cache_service import close_cache
    await close_cache()


def _mask_url(url: str) -> str:
    import re
    return re.sub(r"://[^:]+:[^@]+@", "://***:***@", url)


# ============================================================
# 创建 FastAPI 应用
# ============================================================

# 限流器
limiter = Limiter(key_func=get_remote_address)

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
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ============================================================
# CORS 中间件
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 请求追踪中间件
# ============================================================

@app.middleware("http")
async def request_tracking_middleware(request: Request, call_next):
    """添加请求 ID 并记录请求日志"""
    import time

    # 生成或获取请求 ID
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    # 记录请求开始
    logger.info(f"[{request_id}] {request.method} {request.url.path} START")

    # 处理请求
    start_time = time.time()
    response = await call_next(request)

    # 添加请求 ID 到响应头
    response.headers["X-Request-ID"] = request_id

    # 记录请求结束
    process_time = (time.time() - start_time) * 1000  # 毫秒
    logger.info(f"[{request_id}] {request.method} {request.url.path} END - {response.status_code} - {process_time:.2f}ms")

    return response


# ============================================================
# 统一错误处理
# ============================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 异常处理器"""
    logger.warning(f"HTTP {exc.status_code}: {request.method} {request.url.path} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "path": str(request.url.path),
            "method": request.method,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理器"""
    logger.warning(f"验证失败: {request.method} {request.url.path} - {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "请求参数验证失败",
            "errors": exc.errors(),
            "path": str(request.url.path),
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """数据库异常处理器"""
    logger.error(f"数据库错误: {request.method} {request.url.path} - {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "数据库操作失败",
            "path": str(request.url.path),
        },
    )


@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """全局异常处理中间件"""
    try:
        return await call_next(request)
    except HTTPException:
        # HTTP 异常由上面的处理器处理
        raise
    except RequestValidationError:
        # 验证异常由上面的处理器处理
        raise
    except SQLAlchemyError:
        # 数据库异常由上面的处理器处理
        raise
    except Exception as exc:
        # 未捕获的异常
        logger.exception(f"未捕获异常: {request.method} {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "服务器内部错误",
                "error": str(exc) if settings.DEBUG else "请查看服务端日志",
                "path": str(request.url.path),
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
app.include_router(awards_router, prefix=API_PREFIX)
app.include_router(overview_router, prefix=API_PREFIX)

logger.info("已注册路由: health/relations/alerts/purchasers/announcements/scheduler/charts/preferences/awards/overview")


# ============================================================
# 根路径
# ============================================================

@app.get("/", tags=["系统"])
@limiter.limit("30/minute")  # 限流：每分钟30次
async def root(request: Request):
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
        "cache_enabled": settings.REDIS_URL != "",
    }


# 定时任务调度器已迁移至 app/services/scheduler.py
# 通过 BZB_SCHEDULER_ENABLED=true 环境变量启用
# 控制接口: GET/POST /api/v1/scheduler/*
