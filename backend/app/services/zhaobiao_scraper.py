"""
zhaobiao.cn 预算自动抓取器

优势：
  - 详情页有独立 URL（可直接访问，无需搜索点击）
  - 已保存登录 session（zhaobiao_profile/state.json）
  - 页面结构简单（非 SPA），内容可直接提取

流程：
  1. 用保存的 session 打开浏览器
  2. 对每个有 zhaobiao URL 且无预算的公告，访问详情页
  3. 提取页面正文 → LLM 提取预算 → 更新数据库
"""
import asyncio
import logging
import os
import sys
from typing import Optional, Dict, Any

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

PROFILE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zhaobiao_profile")
os.makedirs(PROFILE_DIR, exist_ok=True)
STATE_FILE = os.path.join(PROFILE_DIR, "state.json")


def _extract_page_text(page) -> str:
    """从 zhaobiao 详情页提取正文"""
    page.wait_for_timeout(3000)
    # zhaobiao 页面内容在 article 或 .detail-content 中
    for sel in ["article", ".detail-content", ".content", ".main-content", "body"]:
        try:
            el = page.query_selector(sel)
            if el and len(el.inner_text()) > 300:
                return el.inner_text()
        except Exception:
            continue
    return page.evaluate("() => document.body.innerText")


def _scrape_zhaobiao_sync(db_url: str, limit: int = 10) -> list[Dict[str, Any]]:
    """同步抓取 zhaobiao.cn 公告预算"""
    import sqlite3
    import httpx

    # 查找有 zhaobiao URL 但无预算的公告
    conn = sqlite3.connect(db_url)
    rows = conn.execute("""
        SELECT id, title, source_url FROM announcements
        WHERE source_url LIKE '%zhaobiao%'
        AND (budget IS NULL OR budget = 0)
        ORDER BY announce_date DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()

    if not rows:
        logger.info("所有有 zhaobiao URL 的公告已有预算")
        return []

    logger.info(f"找到 {len(rows)} 条待抓取公告")
    results = []

    with sync_playwright() as pw:
        # 用 saved session（state.json）创建上下文
        storage_state = STATE_FILE if os.path.exists(STATE_FILE) else None
        browser = pw.chromium.launch(channel="msedge", headless=False)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            storage_state=storage_state,
        )
        page = ctx.new_page()

        # 直接用 saved session 访问，不检查登录状态
        # 如果 session 过期，详情页会显示"仅对会员开放"之类的内容，LLM 提取会检测到
        for ann_id, title, url in rows:
            if not url:
                continue

            print(f"\n📄 [{ann_id}] {title[:60]}...")
            print(f"   URL: {url[:80]}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                content = _extract_page_text(page)

                if not content or len(content) < 200:
                    logger.warning(f"   内容不足: {len(content) if content else 0} 字符")
                    results.append({"id": ann_id, "status": "no_content"})
                    continue

                print(f"   ✅ 提取 {len(content)} 字符")

                # 用 LLM 提取预算
                budget_data = _llm_extract(title, content)
                if budget_data.get("budget_wan"):
                    print(f"   💰 预算: {budget_data['budget_wan']} 万")
                    print(f"   📝 原文: {budget_data.get('budget_raw', '')[:100]}")
                else:
                    print(f"   ⚠️ LLM 未提取到预算")

                # 更新数据库
                _update_db(db_url, ann_id, budget_data)
                results.append({
                    "id": ann_id,
                    "status": "extracted",
                    "budget_wan": budget_data.get("budget_wan"),
                    "confidence": budget_data.get("confidence"),
                })

            except Exception as e:
                logger.error(f"   ❌ 抓取失败: {e}")
                results.append({"id": ann_id, "status": "error", "reason": str(e)[:200]})

        ctx.close()

    return results


def _llm_extract(title: str, content: str) -> Dict[str, Any]:
    """用 LLM 从正文提取预算（同步版，用 httpx 直接调 API）"""
    from app.core.config import settings
    import json as _json

    if not settings.LLM_API_KEY:
        return {"budget_wan": None, "confidence": 0}

    # 复用 llm_budget_extractor 的 prompt 构建逻辑
    from app.services.llm_budget_extractor import _build_extraction_prompt, _parse_llm_response, _extract_focused_sections
    focused = _extract_focused_sections(content, title)
    if not focused:
        return {"budget_wan": None, "confidence": 0}
    prompt = _build_extraction_prompt(title, focused)

    try:
        resp = httpx.post(
            f"{settings.LLM_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": """你是一个专业的招标公告数据提取助手。从公告正文中精确提取预算金额。
规则：预算→万元，报名费→元，保证金→元。只提取公告中的预算/限价，不提取中标金额。找不到填null。只返回JSON。"""},
                    {"role": "user", "content": prompt},
                ],
                "temperature": settings.LLM_TEMPERATURE,
                "max_tokens": settings.LLM_MAX_TOKENS,
            },
            timeout=60,
        )
        if resp.status_code == 200:
            data = resp.json()
            answer = data["choices"][0]["message"]["content"]
            return _parse_llm_response(answer)
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")

    return {"budget_wan": None, "confidence": 0}


def _update_db(db_url: str, ann_id: int, data: Dict[str, Any]):
    """更新数据库"""
    import sqlite3
    conn = sqlite3.connect(db_url)
    updates = {}
    if data.get("budget_wan") is not None:
        updates["budget"] = data["budget_wan"]
    if data.get("registration_fee") is not None:
        updates["registration_fee"] = data["registration_fee"]
    if data.get("deposit") is not None:
        updates["deposit"] = data["deposit"]
    if data.get("bid_date"):
        updates["bid_date"] = data["bid_date"]

    if updates:
        sets = ", ".join(f"{k}=?" for k in updates)
        vals = list(updates.values()) + [ann_id]
        conn.execute(f"UPDATE announcements SET {sets} WHERE id=?", vals)
        conn.commit()
    conn.close()


async def scrape_zhaobiao_budget(limit: int = 10) -> list[Dict[str, Any]]:
    """异步入口"""
    db_url = "biaozhongbao.db"  # 相对于 backend/ 目录
    return await asyncio.to_thread(_scrape_zhaobiao_sync, db_url, limit)
