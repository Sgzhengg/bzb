"""
快速回填资格要求 — 只提取公告正文中的「资格要求」章节
用法: cd d:\bzb\backend && python backfill_qual.py
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
logger = logging.getLogger("backfill_qual")

DETAIL_API = "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryDetail"

# ── 资格提取 ──

def parse_html_content(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n")


def extract_qualification(content: str) -> str:
    if not content:
        return ""

    qual_headers = [
        r"资格要求", r"资格条件", r"投标人资格要求", r"投标人资格条件",
        r"供应商资格要求", r"申请人资格要求", r"应答人资格要求",
        r"资质要求", r"资质条件", r"投标人资质要求", r"资格证明文件",
        r"(?:二|三|四|五|六|七|八|九|十)[、.]?\s*投标人资格",
        r"(?:二|三|四|五|六|七|八|九|十)[、.]?\s*资格",
    ]

    end_headers = [
        r"(?:三|四|五|六|七|八|九|十)[、.]",
        r"获取(?:招标|采购|比选|询价|谈判|磋商)文件",
        r"项目(?:概况|需求|内容)",
        r"技术(?:规范|要求|需求)",
        r"评审(?:办法|标准|方法)",
        r"投标(?:文件|须知)",
        r"联系(?:方式|人)",
        r"发布(?:公告|媒体)",
        r"监督(?:部门|电话)",
        r"采购(?:需求|内容|范围)",
        r"合同(?:条款|期限)",
        r"附件[：:]",
        r"招标(?:内容|范围)",
    ]

    header_pattern = "|".join(qual_headers)
    end_pattern = "|".join(end_headers)

    match = re.search(rf"({header_pattern})", content, re.IGNORECASE)
    if not match:
        return ""

    rest = content[match.end():]
    end_match = re.search(rf"(?:^|\n)\s*({end_pattern})", rest, re.IGNORECASE)
    if end_match:
        qual_text = rest[:end_match.start()].strip()
    else:
        qual_text = rest[:2000].strip()

    qual_text = re.sub(r"\n{3,}", "\n\n", qual_text)
    qual_text = qual_text[:2000]

    if len(qual_text) < 20:
        return ""
    return qual_text


# ── 主流程 ──

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
                (Announcement.qualification_requirements == None) |
                (Announcement.qualification_requirements == "")
            )
        )
        anns = result.scalars().all()

    total = len(anns)
    logger.info(f"需要回填资格要求: {total} 条")

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
            notice_html = detail.get("noticeContent", "") or ""
            if not notice_html:
                skipped += 1
                continue

            content_text = parse_html_content(notice_html)
            qual = extract_qualification(content_text)

            if qual:
                async with AsyncSessionLocal() as db:
                    stmt = update(Announcement).where(Announcement.id == ann.id).values(qualification_requirements=qual)
                    await db.execute(stmt)
                    await db.commit()
                logger.info(f"  [{i+1}] ID={ann.id} ✅ 资格要求 ({len(qual)}字)")
                updated += 1
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
