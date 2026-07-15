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
    """从公告正文中提取关键截止日期，按优先级：投标截止 > 应答递交截止 > 反馈截止 > 其他"""
    if not content:
        return ""

    patterns_priority = [
        # P0: 明确的投标/应答截止时间（最高优先级）
        r"(?:投标(?:文件)?|应答(?:文件)?|申请(?:文件)?|响应(?:文件)?|参选(?:文件)?)\s*(?:截止|递交|提交).*?(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})\s*(?:日)?\s*\d{1,2}[：:]\d{2}",
        # P0b: 时间在前，后面跟截止描述
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


def extract_qualification(content: str) -> str:
    """从公告正文中提取资格要求章节"""
    if not content:
        return ""

    # 资格要求章节的可能标题
    qual_headers = [
        r"资格要求",
        r"资格条件",
        r"投标人资格要求",
        r"投标人资格条件",
        r"供应商资格要求",
        r"申请人资格要求",
        r"应答人资格要求",
        r"资质要求",
        r"资质条件",
        r"投标人资质要求",
        r"资格证明文件",
        r"(?:二|三|四|五|六|七|八|九|十)[、.]?\s*投标人资格",
        r"(?:二|三|四|五|六|七|八|九|十)[、.]?\s*资格",
    ]

    # 后续章节标题（资格章节到此结束）
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

    # 拼接正则：匹配资格标题
    header_pattern = "|".join(qual_headers)
    end_pattern = "|".join(end_headers)

    # 找到资格章节起点
    match = re.search(rf"({header_pattern})", content, re.IGNORECASE)
    if not match:
        return ""

    start = match.start()
    # 跳过标题行本身
    rest = content[match.end():]

    # 找到下一个章节标题作为终点
    end_match = re.search(rf"(?:^|\n)\s*({end_pattern})", rest, re.IGNORECASE)
    if end_match:
        qual_text = rest[:end_match.start()].strip()
    else:
        # 没有明确的结束标志，取后续 2000 字
        qual_text = rest[:2000].strip()

    # 清理：删除多余空白和无关前缀
    qual_text = re.sub(r"\n{3,}", "\n\n", qual_text)
    qual_text = qual_text[:2000]  # 限制长度

    # 如果提取到的内容太短（<20字），可能匹配有误
    if len(qual_text) < 20:
        return ""

    return qual_text


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
            api_publish_date = detail.get("publishDate", "") or ""
            api_deadline = detail.get("tenderSaleDeadline", "") or ""
            api_back_date = detail.get("backDate", "") or ""

            # HTML 正文
            notice_html = detail.get("noticeContent", "") or ""
            content_text = parse_html_content(notice_html) if notice_html else ""

            if not content_text and not company_name:
                skipped += 1
                continue

            # 从文本提取字段（API结构化数据优先）
            deadline_from_content = extract_deadline(content_text)
            bid_date_from_content = extract_bid_date(content_text)

            # deadline: 优先用API的 tenderSaleDeadline，否则用正则
            deadline = None
            if api_deadline and not api_deadline.startswith("1900"):
                deadline = _normalize_date(api_deadline)
            elif deadline_from_content:
                deadline = deadline_from_content

            # bid_date: 优先用API的 backDate
            bid_date = None
            if api_back_date and not api_back_date.startswith("1900"):
                bid_date = _normalize_date(api_back_date)
            elif bid_date_from_content:
                bid_date = bid_date_from_content

            fields = {
                "industry": extract_purchaser(title, content_text, company_name),
                "announce_date": _normalize_date(api_publish_date) if api_publish_date and not api_publish_date.startswith("1900") else None,
                "budget": extract_budget(content_text),
                "deadline": deadline,
                "bid_date": bid_date,
                "registration_fee": extract_registration_fee(content_text),
                "deposit": extract_deposit(content_text),
                "qualification": extract_qualification(content_text),
            }

            # 只更新有值的字段
            updates = {}
            if fields["industry"]:
                existing = (ann.industry or "").strip()
                if fields["industry"] != existing:
                    updates["industry"] = fields["industry"]
            if fields["announce_date"]:
                d = parse_date(fields["announce_date"])
                if d:
                    existing = ann.announce_date
                    # Update if different day (not just today's default)
                    if existing and hasattr(existing, 'strftime'):
                        updates["announce_date"] = d
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
            if fields["qualification"]:
                existing = (ann.qualification_requirements or "").strip()
                if not existing or len(existing) < 50:
                    updates["qualification_requirements"] = fields["qualification"]

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
