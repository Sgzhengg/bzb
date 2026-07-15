"""
回填公告缺失字段脚本 V2

修复：
  1. 从 source_url 提取 publishUuid
  2. noticeContent 是 HTML，非 PDF → 用 BeautifulSoup 提取文本
  3. 也利用 API 返回的结构化字段（如 companyName）

用法:
  cd d:\bzb\backend
  python backfill_details.py
"""

import asyncio
import logging
import os
import re
import ssl
import sys
import time as _time
from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("backfill")

DETAIL_API = "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryDetail"


def _build_client():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.options |= 0x4
    return httpx.Client(
        transport=httpx.HTTPTransport(verify=ctx),
        timeout=httpx.Timeout(30),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )


def extract_purchaser(title: str, content: str, company_name: str = "") -> str:
    """提取招标单位 - 优先用 companyName，否则正则提取"""
    if company_name and company_name.strip():
        return company_name.strip()
    m = re.search(r"(中国移动通信集团[^，。；\n]{0,40}(?:有限公司|分公司))", title + content)
    return m.group(1) if m else ""


def extract_budget(content: str) -> float | None:
    patterns = [
        r"采购?预算[总]?[金额]?[约]?[：:为]?\s*(\d+(?:\.\d+)?)\s*万",
        r"项目预算[：:]?\s*(\d+(?:\.\d+)?)\s*万",
        r"预算金额[：:]?\s*(\d+(?:\.\d+)?)\s*万",
        r"采购?总?金?额[：:]?\s*(\d+(?:\.\d+)?)\s*万",
        r"最高限价[：:]?\s*(\d+(?:\.\d+)?)\s*万",
        r"估算金额[：:]?\s*(\d+(?:\.\d+)?)\s*万",
        r"(?:含税)?(?:采购)?预算[：:]\s*(\d+(?:\.\d+)?)\s*万",
        r"(?:含税)?(?:采购)?预算[：:]\s*人民币\s*(\d+(?:\.\d+)?)\s*万",
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            return float(m.group(1).replace(",", ""))
    return None


def extract_deadline(content: str) -> str:
    patterns = [
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})\s*(?:日)?\s*(?:前|截止|之前)?.*?(?:投标|递交|提交|应答)",
        r"(?:投标|递交|提交|应答).*?截止.*?(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
        r"截止时间[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
        r"(?:应答|投标|递交|提交).*?时间[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            return _normalize_date(m.group(1))
    return ""


def extract_bid_date(content: str) -> str:
    patterns = [
        r"(?:开标|投标|谈判|磋商).*?时间[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
        r"(?:开标|开启).*?日期[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            return _normalize_date(m.group(1))
    return ""


def extract_registration_fee(content: str) -> float | None:
    patterns = [
        r"(?:招标文件|采购文件|标书|询价文件)[工]?本?费?[：:]\s*(\d+(?:\.\d+)?)\s*元?",
        r"(?:招标文件|采购文件|标书|询价文件).*?售价[：:]\s*(\d+(?:\.\d+)?)\s*元?",
        r"文件费[用]?[：:]\s*(\d+(?:\.\d+)?)\s*元?",
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            val = float(m.group(1))
            if val > 100000:
                val = val / 100
            return val
    return None


def extract_deposit(content: str) -> float | None:
    patterns = [
        r"(?:投标|询价|谈判|磋商)?保证金[：:]\s*(\d+(?:\.\d+)?)\s*万",
        r"(?:投标|询价|谈判|磋商)?保证金[：:]\s*([\d,]+(?:\.\d+)?)\s*元",
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            val = float(m.group(1).replace(",", ""))
            if "元" in m.group(0) and "万" not in m.group(0):
                return val / 10000
            return val
    return None


def _normalize_date(raw: str) -> str:
    m = re.match(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", raw)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return raw


def parse_html_content(html: str) -> str:
    """从 HTML 中提取纯文本"""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n")


def parse_date(s: str) -> date | None:
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def parse_datetime(s: str) -> datetime | None:
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})[T\s]?(\d{1,2}):(\d{1,2})?", s)
    if m:
        return datetime(
            int(m.group(1)), int(m.group(2)), int(m.group(3)),
            int(m.group(4) or 17), int(m.group(5) or 0),
        )
    return None


async def backfill():
    from app.db.session import AsyncSessionLocal
    from app.models.announcement import Announcement
    from sqlalchemy import select, update

    client = _build_client()

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Announcement).order_by(Announcement.id))
        announcements = result.scalars().all()

    total = len(announcements)
    updated = 0
    skipped = 0
    failed = 0

    logger.info(f"共 {total} 条公告待处理")

    for i, ann in enumerate(announcements):
        source_url = ann.source_url or ""
        title = ann.title or ""

        # 从 source_url 提取 publishId 和 publishUuid
        pid_match = re.search(r"publishId=(\d+)", source_url)
        puid_match = re.search(r"publishUuid=([^&]+)", source_url)

        if not pid_match:
            logger.info(f"[{i+1}/{total}] ID={ann.id} — 无 publishId，跳过")
            skipped += 1
            continue

        publish_id = pid_match.group(1)
        publish_uuid = puid_match.group(1) if puid_match else ""

        if (i + 1) % 20 == 0 or i == total - 1:
            logger.info(f"进度: {i+1}/{total} (已更新 {updated}, 跳过 {skipped}, 失败 {failed})")

        try:
            body = {
                "publishId": publish_id,
                "publishType": "PROCUREMENT",
                "sfactApplColumn5": "PC",
            }
            if publish_uuid:
                body["publishUuid"] = publish_uuid

            resp = client.post(DETAIL_API, json=body)

            if resp.status_code != 200:
                logger.warning(f"  [{i+1}] ID={ann.id} API {resp.status_code}")
                failed += 1
                continue

            data = resp.json()
            if data.get("code") != 0:
                logger.warning(f"  [{i+1}] ID={ann.id} API code={data.get('code')}: {data.get('msg','')}")
                failed += 1
                continue

            detail = data.get("data", {}) or {}

            # 结构化字段直接从 API 获取
            company_name = detail.get("companyName", "") or ""

            # HTML 正文
            notice_html = detail.get("noticeContent", "") or ""
            content_text = parse_html_content(notice_html) if notice_html else ""

            if not content_text and not company_name:
                skipped += 1
                continue

            # 从文本提取字段
            fields = {
                "industry": extract_purchaser(title, content_text, company_name),
                "budget": extract_budget(content_text),
                "deadline": extract_deadline(content_text),
                "bid_date": extract_bid_date(content_text),
                "registration_fee": extract_registration_fee(content_text),
                "deposit": extract_deposit(content_text),
            }

            # 只更新有值的字段
            updates = {}
            if fields["industry"]:
                existing = (ann.industry or "").strip()
                if fields["industry"] != existing:
                    updates["industry"] = fields["industry"]
            if fields["budget"] is not None:
                existing = float(ann.budget or 0)
                if existing == 0 or abs(existing - fields["budget"]) > 0.01:
                    updates["budget"] = fields["budget"]
            if fields["deadline"]:
                dt = parse_datetime(fields["deadline"])
                if dt and (not ann.deadline or ann.deadline.year < 2000):
                    updates["deadline"] = dt
            if fields["bid_date"]:
                d = parse_date(fields["bid_date"])
                if d and not ann.bid_date:
                    updates["bid_date"] = d
            if fields["registration_fee"] is not None:
                existing = float(ann.registration_fee or 0)
                if existing == 0:
                    updates["registration_fee"] = fields["registration_fee"]
            if fields["deposit"] is not None:
                existing = float(ann.deposit or 0)
                if existing == 0:
                    updates["deposit"] = fields["deposit"]

            if updates:
                async with AsyncSessionLocal() as db:
                    stmt = update(Announcement).where(Announcement.id == ann.id).values(**updates)
                    await db.execute(stmt)
                    await db.commit()

                field_names = ", ".join(updates.keys())
                logger.info(f"  [{i+1}] ID={ann.id} ✅ 更新: {field_names}")
                updated += 1
            else:
                skipped += 1

            _time.sleep(1.0)

        except Exception as e:
            logger.error(f"  [{i+1}] ID={ann.id} ❌ {e}")
            failed += 1

    client.close()
    logger.info(f"\n===== 回填完成 =====")
    logger.info(f"  总计: {total}, 已更新: {updated}, 跳过: {skipped}, 失败: {failed}")


if __name__ == "__main__":
    asyncio.run(backfill())
