"""
历史中标结果 API 接口

端点:
  GET    /api/v1/awards              中标结果列表（筛选/分页）
  GET    /api/v1/awards/{id}         单条详情
  DELETE /api/v1/awards/{id}         删除单条记录
  GET    /api/v1/awards/stats        中标统计概览
"""

import logging
import uuid
import asyncio
import os
import sys
import json
import re
from datetime import datetime, date
from typing import Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, AsyncSessionLocal
from app.models.historical_award import HistoricalAward
from app.models.client_relation import Purchaser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/awards", tags=["中标结果"])

# ── 采集进度追踪（内存中，重启丢失） ──
_fetch_tasks: Dict[str, dict] = {}  # {task_id: {status, progress, message, ...}}


async def _import_to_db(backend_dir: str, adapter: str, province: str = "") -> int:
    """将 crawl_winning_results.py 输出的 JSON 导入 historical_awards 表。

    Returns:
        成功导入的记录数。
    """
    output_dir = os.path.join(backend_dir, "output")
    province_slug = province.replace(",", "_") if province else "quanguo"
    json_path = os.path.join(output_dir, f"winning_results_{adapter}_{province_slug}.json")

    if not os.path.exists(json_path):
        logger.warning(f"⚠️ 采集结果文件不存在: {json_path}")
        return 0

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 提取所有 items
    all_items = []
    adapters_data = data.get("adapters", [])
    for adp_data in adapters_data:
        all_items.extend(adp_data.get("items", []))

    if not all_items:
        logger.info("📭 没有可导入的中标结果")
        return 0

    imported = 0
    async with AsyncSessionLocal() as session:
        # 确保默认采购方存在
        from sqlalchemy import select as sa_select
        existing = await session.execute(
            sa_select(Purchaser).where(Purchaser.id == 1)
        )
        if not existing.scalar_one_or_none():
            session.add(Purchaser(
                id=1,
                name="中国移动通信集团广东有限公司",
                level="省公司",
                region="广州",
            ))
            await session.flush()

        for item in all_items:
            title = (item.get("title") or "").strip()
            if not title:
                continue

            source_url = (item.get("source_url") or "").strip()

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 修复：提前提取 winner_name，供后续去重检查使用
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            winner_name = item.get("winner_name", "").strip()
            if not winner_name:
                winner_name = _extract_winner_from_title(title)

            # 检查重复：同一公告同一中标方只入库一次
            if source_url and winner_name:
                dup_check = await session.execute(
                    sa_select(HistoricalAward).where(
                        HistoricalAward.source_url == source_url,
                        HistoricalAward.winner_name == winner_name,
                    )
                )
                if dup_check.scalar_one_or_none():
                    continue
            elif source_url:
                dup_check = await session.execute(
                    sa_select(HistoricalAward).where(
                        HistoricalAward.source_url == source_url
                    )
                )
                if dup_check.scalar_one_or_none():
                    continue
            elif winner_name:
                dup_check = await session.execute(
                    sa_select(HistoricalAward).where(
                        HistoricalAward.project_name == title[:500],
                        HistoricalAward.winner_name == winner_name,
                    )
                )
                if dup_check.scalar_one_or_none():
                    continue

            # 解析日期
            pub_date_str = item.get("publish_date", "")
            bid_open_date = date.today()
            if pub_date_str:
                for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"):
                    try:
                        bid_open_date = datetime.strptime(pub_date_str[:10], fmt).date()
                        break
                    except ValueError:
                        continue

            # 解析折扣率：优先使用爬虫提取的
            discount_rate = item.get("discount_rate")
            if discount_rate is not None:
                try:
                    discount_rate = float(discount_rate)
                except (ValueError, TypeError):
                    discount_rate = 0
            else:
                discount_rate = 0

            # 确定数据来源
            data_source = item.get("data_source", "") or item.get("adapter", "") or adapter

            # 确定项目类别
            project_category = _guess_category(title)

            try:
                award = HistoricalAward(
                    project_name=title[:500],
                    purchaser_id=1,  # 默认采购方
                    winner_name=winner_name or "未知中标方",
                    winner_type="头部常客",
                    bid_amount=0,
                    budget_amount=0,
                    discount_rate=discount_rate,
                    project_category=project_category,
                    bid_open_date=bid_open_date,
                    is_continuous=False,
                    continuous_count=0,
                    source_url=source_url,
                    data_source=data_source,
                )
                session.add(award)
                imported += 1
            except Exception as e:
                logger.warning(f"  ⚠️ 导入失败 [{title[:60]}]: {e}")

        await session.commit()

    logger.info(f"✅ 已导入 {imported} 条中标结果到 historical_awards")
    return imported


def _extract_winner_from_title(title: str) -> str:
    """从标题中提取中标方名称。"""
    patterns = [
        r'[（(]([^）)]+)[）)]\s*中标',
        r'中标(?:候选)?人?[：:]\s*([^\s，,。.]{2,30})',
        r'([^\s，,。.]{2,30}?(?:有限公司|有限责任公司|公司|集团))\s*(?:中标|中选|成交)',
        r'(?:拟|确定)\s*([^\s，,。.]{2,30}?(?:有限公司|有限责任公司|公司))\s*为',
    ]
    for pat in patterns:
        m = re.search(pat, title)
        if m:
            return m.group(1).strip()
    # 无中标方时尝试从标题提取公司名
    company_match = re.search(r'([^\s，,。.]{2,20}(?:有限公司|有限责任公司|公司|集团))', title)
    if company_match:
        return company_match.group(1).strip()
    return ""


def _guess_category(title: str) -> str:
    """根据标题推测项目类别。"""
    category_map = {
        "广告": "广告类",
        "活动": "活动会展类",
        "渠道": "渠道营销类",
        "触点": "渠道营销类",
        "新媒体": "新媒体运营类",
        "运营": "新媒体运营类",
        "内容": "内容制作类",
        "制作": "内容制作类",
        "设计": "创意设计类",
        "投放": "媒介投放类",
        "媒介": "媒介投放类",
        "品牌": "品牌策略类",
        "策略": "品牌策略类",
        "传播": "政企传播类",
        "政企": "政企传播类",
        "IT": "IT信息化",
        "信息化": "IT信息化",
        "软件": "IT信息化",
        "系统": "IT信息化",
        "网络": "网络建设",
        "基站": "网络建设",
        "设备": "设备采购",
        "采购": "设备采购",
        "工程": "工程建设",
        "施工": "工程建设",
        "维护": "运维服务",
        "维保": "运维服务",
        "物业": "物业服务",
        "保安": "物业服务",
        "保洁": "物业服务",
        "咨询": "咨询服务",
        "监理": "咨询服务",
    }
    for kw, cat in category_map.items():
        if kw in title:
            return cat
    return "其他"


@router.get("", summary="获取中标结果列表")
async def list_awards(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    project_category: Optional[str] = Query(None, description="项目类别筛选"),
    winner_type: Optional[str] = Query(None, description="中标方类型"),
    purchaser_id: Optional[int] = Query(None, description="采购方ID"),
    search: Optional[str] = Query(None, description="项目名称/中标方搜索"),
    data_source: Optional[str] = Query(None, description="数据来源: b2b_10086(移动)/telecom(电信)/unicom(联通)/gd_zbtb/gd_ygp"),
    db: AsyncSession = Depends(get_db),
):
    """获取历史中标结果列表，支持筛选和分页。"""
    conditions = []

    if project_category:
        conditions.append(HistoricalAward.project_category == project_category)
    if winner_type:
        conditions.append(HistoricalAward.winner_type == winner_type)
    if purchaser_id:
        conditions.append(HistoricalAward.purchaser_id == purchaser_id)
    if data_source:
        conditions.append(HistoricalAward.data_source == data_source)
    if search:
        conditions.append(
            HistoricalAward.project_name.ilike(f"%{search}%")
            | HistoricalAward.winner_name.ilike(f"%{search}%")
        )

    # 总数
    count_q = select(func.count()).select_from(HistoricalAward)
    if conditions:
        count_q = count_q.where(and_(*conditions))
    total = (await db.execute(count_q)).scalar() or 0

    # 列表
    list_q = (
        select(HistoricalAward)
        .order_by(desc(HistoricalAward.bid_open_date))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if conditions:
        list_q = list_q.where(and_(*conditions))

    result = await db.execute(list_q)
    awards = result.scalars().all()

    items = [
        {
            "id": a.id,
            "project_name": a.project_name,
            "purchaser_id": a.purchaser_id,
            "purchaser_name": a.purchaser.name if a.purchaser else "",
            "winner_name": a.winner_name,
            "winner_type": a.winner_type,
            "bid_amount": float(a.bid_amount) if a.bid_amount else None,
            "budget_amount": float(a.budget_amount) if a.budget_amount else None,
            "discount_rate": float(a.discount_rate) if a.discount_rate else None,
            "project_category": a.project_category,
            "bid_open_date": a.bid_open_date.isoformat() if a.bid_open_date else None,
            "contract_start": a.contract_start.isoformat() if a.contract_start else None,
            "contract_end": a.contract_end.isoformat() if a.contract_end else None,
            "is_continuous": a.is_continuous,
            "continuous_count": a.continuous_count,
            "source_url": a.source_url or "",
            "data_source": a.data_source or "",
        }
        for a in awards
    ]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.get("/stats", summary="中标统计概览")
async def award_stats(
    db: AsyncSession = Depends(get_db),
):
    """获取中标结果统计数据。"""
    # 总数
    total_q = select(func.count()).select_from(HistoricalAward)
    total = (await db.execute(total_q)).scalar() or 0

    # 总金额
    amount_q = select(func.sum(HistoricalAward.bid_amount)).select_from(HistoricalAward)
    total_amount = (await db.execute(amount_q)).scalar() or 0

    # 去重中标方数
    from sqlalchemy import distinct
    winner_count_q = select(func.count(distinct(HistoricalAward.winner_name))).select_from(HistoricalAward)
    winner_count = (await db.execute(winner_count_q)).scalar() or 0

    # 按项目类别统计
    cat_q = (
        select(
            HistoricalAward.project_category,
            func.count().label("count"),
        )
        .group_by(HistoricalAward.project_category)
        .order_by(desc("count"))
    )
    cat_result = await db.execute(cat_q)
    cat_stats = [
        {"category": row.project_category, "count": row.count}
        for row in cat_result.fetchall()
    ]

    return {
        "total": total,
        "total_amount": round(float(total_amount), 1),
        "winner_count": winner_count,
        "categories": cat_stats,
    }


@router.get("/export", summary="导出中标结果为Excel")
async def export_awards(
    db: AsyncSession = Depends(get_db),
):
    """将所有中标结果导出为 Excel 文件。"""
    from io import BytesIO
    from datetime import date
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    from fastapi.responses import StreamingResponse
    from urllib.parse import quote

    result = await db.execute(
        select(HistoricalAward).order_by(desc(HistoricalAward.bid_open_date))
    )
    awards = result.scalars().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "中标结果"

    header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center")
    data_font = Font(name="微软雅黑", size=10)
    data_align = Alignment(vertical="center")
    data_align_center = Alignment(horizontal="center", vertical="center")
    link_font = Font(name="微软雅黑", size=10, color="0563C1", underline="single")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    even_fill = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")

    headers = ["序号", "项目名称", "中标方", "中标份额(%)", "项目类别", "公示日期", "公告链接"]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    ws.freeze_panes = "A2"

    for row_idx, award in enumerate(awards, 2):
        row_data = [
            row_idx - 1,
            award.project_name or "",
            award.winner_name or "",
            float(award.discount_rate) if award.discount_rate else "",
            award.project_category or "",
            award.bid_open_date.strftime("%Y-%m-%d") if award.bid_open_date else "",
            award.source_url or "",
        ]
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font = data_font
            cell.border = thin_border
            if col_idx in (1, 4, 5, 6):
                cell.alignment = data_align_center
            elif col_idx == 7 and value:
                cell.value = "打开链接"
                cell.hyperlink = value
                cell.font = link_font
                cell.alignment = data_align_center
            elif col_idx == 2:
                cell.alignment = Alignment(vertical="center", wrap_text=True)
            if row_idx % 2 == 0:
                cell.fill = even_fill

    col_widths = [6, 55, 20, 14, 14, 13, 14]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 28
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(awards) + 1}"

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"中标结果_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/{award_id}", summary="获取中标结果详情")
async def get_award_detail(
    award_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取单条中标结果的详细信息。"""
    award = await db.get(HistoricalAward, award_id)
    if not award:
        raise HTTPException(status_code=404, detail=f"中标记录 {award_id} 不存在")

    return award.to_dict()


@router.post("/fetch", summary="手动触发中标结果采集")
async def fetch_awards(
    background_tasks: BackgroundTasks,
    province: Optional[str] = Query(None, description="目标省份，空为全国"),
    adapter: Optional[str] = Query(None, description="运营商: b2b_10086(移动)/telecom(电信)/unicom(联通)/all(全部)"),
    skip: Optional[bool] = Query(False, description="跳过爬虫，直接导入现有数据"),
):
    """后台触发中标结果数据采集（b2b.10086.cn），返回 task_id 用于轮询进度。"""
    task_id = str(uuid.uuid4())[:8]
    province_name = province or "全国"
    adapter_name = adapter or "b2b_10086"

    adapter_label_map = {
        "all": "全部运营商（移动+电信+联通）",
        "b2b_10086": "中国移动",
        "telecom": "中国电信",
        "unicom": "中国联通",
    }
    adapter_label = adapter_label_map.get(adapter_name, adapter_name)

    _fetch_tasks[task_id] = {
        "status": "starting",
        "progress": 0,
        "message": f"正在启动中标结果采集引擎（{adapter_label} × {province_name}）...",
        "province": province_name,
        "adapter": adapter_name,
        "started_at": datetime.now().isoformat(),
        "result_count": 0,
        "error": None,
    }

    async def _run():
        logger.info(f"🕷️ 中标结果采集开始 (adapter={adapter_name}, province={province_name}, task={task_id})...")
        try:
            import subprocess
            cwd = os.path.dirname(os.path.abspath(__file__))
            cwd = os.path.dirname(os.path.dirname(os.path.dirname(cwd)))  # -> backend/
            env = os.environ.copy()
            if sys.platform == "win32":
                env["PYTHONASYNCIODEFAULTLOOPPOLICY"] = "WindowsProactorEventLoopPolicy"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 检查是否有最近采集的 JSON 文件，如有则直接导入
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            province_slug = province.replace(",", "_") if province else "quanguo"
            json_path = os.path.join(cwd, "output", f"winning_results_{adapter_name}_{province_slug}.json")
            logger.info(f"[SKIP] 检查文件: {json_path}")

            skip_crawl = False
            file_age = 999999  # 默认值，表示文件不存在
            if os.path.exists(json_path):
                import time
                file_age = time.time() - os.path.getmtime(json_path)
                logger.info(f"[SKIP] 文件存在，年龄: {int(file_age/60)} 分钟")
                # 如果文件在 2 小时内生成，跳过爬虫直接导入
                if file_age < 7200:
                    skip_crawl = True
                    logger.info(f"[SKIP] 发现最近采集文件 ({int(file_age/60)} 分钟前)，跳过爬虫直接导入")
                else:
                    logger.info(f"[SKIP] 文件过旧 ({int(file_age/60)} 分钟)，需要重新采集")
            else:
                logger.info(f"[SKIP] 文件不存在，需要爬虫采集")

            if skip_crawl:
                _fetch_tasks[task_id].update(
                    status="running", progress=50,
                    message=f"发现最近数据，正在导入...",
                )
            else:
                _fetch_tasks[task_id].update(
                    status="running", progress=10,
                    message=f"正在搜索 {adapter_label} × {province_name} 中标公告...",
                )

                cmd = [sys.executable, "crawl_winning_results.py",
                       "--adapter", adapter_name]
                if province and province.strip():
                    cmd.extend(["--province", province])

                _fetch_tasks[task_id].update(
                    progress=30,
                    message=f"正在爬取 {adapter_label} × {province_name} 中标数据...",
                )

                proc = await asyncio.to_thread(
                    subprocess.run,
                    cmd,
                    capture_output=True, text=True, cwd=cwd, timeout=1200, env=env,
                )

                if proc.returncode != 0:
                    err_msg = proc.stderr[:500] if proc.stderr else f"退出码: {proc.returncode}"
                    _fetch_tasks[task_id].update(
                        status="failed", progress=0,
                        message=f"采集失败",
                        error=err_msg,
                    )
                    logger.error(f"❌ 中标结果采集失败 (task={task_id}): {err_msg}")
                    return

            _fetch_tasks[task_id].update(
                progress=70,
                message="正在将采集结果导入数据库...",
            )

            imported_count = await _import_to_db(cwd, adapter_name, province)

            _fetch_tasks[task_id].update(
                status="completed", progress=100,
                message=f"{adapter_label} × {province_name} 中标结果采集完成！共导入 {imported_count} 条",
                result_count=imported_count,
            )
            logger.info(f"✅ 中标结果采集完成 (task={task_id}): 导入 {imported_count} 条")

        except subprocess.TimeoutExpired as e:
            logger.error(f"❌ 中标结果采集超时 (task={task_id})")
            _fetch_tasks[task_id].update(
                status="failed", progress=0,
                message="采集超时（数据量较大，请稍后重试或使用现有数据）",
                error=f"超时: {str(e)}",
            )
        except Exception as e:
            logger.error(f"❌ 中标结果采集失败 (task={task_id}): {e}")
            _fetch_tasks[task_id].update(
                status="failed", progress=0,
                message=f"采集失败: {str(e)}",
                error=str(e),
            )

    background_tasks.add_task(_run)

    return {
        "status": "started",
        "task_id": task_id,
        "message": f"中标结果采集已在后台启动（{adapter_label} × {province_name}）",
    }


@router.get("/fetch/status/{task_id}", summary="查询中标采集进度")
async def get_fetch_status(task_id: str):
    """查询采集任务的实时进度。"""
    task = _fetch_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在或已过期")
    return task


@router.delete("/{award_id}", summary="删除中标结果")
async def delete_award(
    award_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除单条中标结果记录。"""
    award = await db.get(HistoricalAward, award_id)
    if not award:
        raise HTTPException(status_code=404, detail=f"中标记录 {award_id} 不存在")

    await db.delete(award)
    await db.commit()
    logger.info(f"已删除中标记录: id={award_id}, project={award.project_name}, winner={award.winner_name}")

    return {"ok": True, "message": f"已删除中标记录 {award_id}"}
