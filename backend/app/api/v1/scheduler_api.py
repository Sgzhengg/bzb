"""
定时任务调度器 — 控制 API

端点:
  GET  /api/v1/scheduler/status     获取调度器状态
  POST /api/v1/scheduler/start      启动调度器
  POST /api/v1/scheduler/stop       停止调度器
  POST /api/v1/scheduler/trigger/{job_id}  手动触发指定任务
"""

from fastapi import APIRouter, HTTPException

from app.services.scheduler import (
    get_scheduler_status,
    start_scheduler,
    stop_scheduler,
    get_scheduler,
)

router = APIRouter(prefix="/scheduler", tags=["定时任务"])


@router.get("/status", summary="获取调度器状态")
async def scheduler_status():
    """获取当前调度器运行状态和已注册任务列表。"""
    return get_scheduler_status()


@router.post("/start", summary="启动调度器")
async def scheduler_start():
    """启动定时任务调度器（注册所有任务并开始执行）。"""
    try:
        start_scheduler()
        return {"status": "started", "message": "调度器已启动"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动失败: {e}")


@router.post("/stop", summary="停止调度器")
async def scheduler_stop():
    """停止定时任务调度器。"""
    stop_scheduler()
    return {"status": "stopped", "message": "调度器已停止"}


@router.post("/trigger/{job_id}", summary="手动触发任务")
async def scheduler_trigger(job_id: str):
    """
    手动触发指定任务（用于调试或补采）。

    可用的 job_id:
    - fetch_morning / fetch_evening: 抓取公告
    - alert_check: 客情关联检查
    - weekly_report: 生成周报
    """
    sched = get_scheduler()
    if not sched.running:
        raise HTTPException(status_code=400, detail="调度器未运行，请先启动")

    try:
        job = sched.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"任务 {job_id} 不存在")

        job.modify(next_run_time=None)  # 立即触发
        return {"status": "triggered", "job_id": job_id, "job_name": job.name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {e}")
