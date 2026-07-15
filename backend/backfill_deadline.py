"""
回填关键截止日期 — 使用改进的 extract_deadline
用法: cd d:\bzb\backend && python backfill_deadline.py
"""
import logging
import re
import ssl
import sys
import time as _time
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import httpx
from bs4 import BeautifulSoup
from sqlalchemy import update

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("backfill_deadline")

DETAIL_API = "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryDetail"


def parse_html_content(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n")


def _normalize_date(raw: str) -> str:
    m = re.match(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", raw)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return raw


def extract_deadline(content: str) -> str:
    """从公告正文中提取关键截止日期，按优先级：投标截止 > 应答递交截止 > 反馈截止 > 其他"""
    if not content:
        return ""

    patterns_priority = [
        # P0: 明确的投标/应答截止时间（最高优先级）
        r"(?:投标(?:文件)?|应答(?:文件)?|申请(?:文件)?|响应(?:文件)?|参选(?:文件)?)\s*(?:截止|递交|提交).*?(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})\s*(?:日)?\s*\d{1,2}[：:]\d{2}",
        # P0b: 时间在前
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})\s*(?:日)?\s*\d{1,2}[：:]\d{2}.*?(?:投标|应答|申请|响应|参选).*?截止",

        # P1: 纸质/电子 应答文件递交截止时间
        r"(?:纸质|电子)?\s*(?:应答|投标|申请|响应|参选)\s*(?:文件)?\s*(?:递交|提交|送达).*?截止.*?(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}).*?(?:纸质|电子)?\s*(?:应答|投标|申请|响应|参选)\s*(?:文件)?\s*(?:递交|提交|送达).*?截止",

        # P2: 截标/开标时间
        r"(?:截标|开标).*?时间[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}).*?(?:截标|开标)",

        # P3: 反馈/意见截止时间
        r"(?:于|在)\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})\s*(?:日)?\s*(?:前|之前|截止).*?(?:反馈|提交|意见)",
        r"(?:反馈|意见).*?(?:截止|于|在)\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
        r"请.*?(?:于|在)\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}).*?(?:前|之前).*?(?:提交|反馈)",

        # P4: 通用截止时间
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})\s*(?:日)?\s*(?:前|截止|之前)?.*?(?:递交|提交|应答)",
        r"(?:递交|提交|应答).*?截止.*?(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
        r"截止时间[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
        r"(?:应答|递交|提交).*?时间[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",

        # P5: 兜底——任何日期+截止的组合
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}).*?截止",
        r"截止.*?(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
    ]

    for pat in patterns_priority:
        m = re.search(pat, content)
        if m:
            return _normalize_date(m.group(1))
    return ""


def _build_client():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.options |= 0x4
    return httpx.Client(
        transport=httpx.HTTPTransport(verify=ctx),
        timeout=httpx.Timeout(30),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )


async def run():
    from app.db.session import AsyncSessionLocal
    from app.models.announcement import Announcement
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Announcement).where(
                (Announcement.deadline == None) | (Announcement.deadline < "2000-01-01")
            )
        )
        anns = result.scalars().all()

    total = len(anns)
    logger.info(f"需要回填截止日期: {total} 条")

    if total == 0:
        logger.info("无需回填")
        return

    client = _build_client()
    updated = 0
    skipped = 0
    failed = 0

    for i, ann in enumerate(anns):
        if (i + 1) % 20 == 0:
            logger.info(f"进度: {i+1}/{total} (已更新 {updated})")

        source_url = getattr(ann, 'source_url', '') or ''
        publish_id = ""
        puid_match = re.search(r'publishId=(\d+)', source_url)
        if puid_match:
            publish_id = puid_match.group(1)

        if not publish_id:
            # 尝试从 API 的 structured field 获取
            skipped += 1
            continue

        try:
            body = {"publishId": publish_id, "publishType": "PROCUREMENT", "sfactApplColumn5": "PC"}
            puid_match2 = re.search(r'publishUuid=([^&]+)', source_url)
            if puid_match2:
                body["publishUuid"] = puid_match2.group(1)

            resp = client.post(DETAIL_API, json=body)
            if resp.status_code != 200:
                failed += 1
                continue

            data = resp.json()
            if data.get("code") != 0:
                failed += 1
                continue

            detail = data.get("data", {}) or {}

            # 优先用 API 结构化字段
            api_deadline = detail.get("tenderSaleDeadline", "") or ""
            if api_deadline and not api_deadline.startswith("1900"):
                deadline_date = _normalize_date(api_deadline)
                source = "API"
            else:
                notice_html = detail.get("noticeContent", "") or ""
                if not notice_html:
                    skipped += 1
                    continue
                content_text = parse_html_content(notice_html)
                deadline_date = extract_deadline(content_text)
                source = "text"

            if deadline_date:
                d = None
                m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", deadline_date)
                if m:
                    from datetime import date
                    d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

                if d:
                    async with AsyncSessionLocal() as db:
                        stmt = update(Announcement).where(Announcement.id == ann.id).values(deadline=d)
                        await db.execute(stmt)
                        await db.commit()
                    logger.info(f"  [{i+1}] ID={ann.id} ✅ 截止日期={deadline_date} ({source})")
                    updated += 1
                else:
                    skipped += 1
            else:
                skipped += 1

            _time.sleep(1.0)

        except Exception as e:
            logger.error(f"  [{i+1}] ID={ann.id} ❌ {e}")
            failed += 1

    client.close()
    logger.info(f"\n===== 完成 =====")
    logger.info(f"  总计: {total}, 已更新: {updated}, 跳过: {skipped}, 失败: {failed}")


if __name__ == "__main__":
    asyncio.run(run())
