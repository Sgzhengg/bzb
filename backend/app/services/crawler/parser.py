"""
HTML 内容解析器
负责从列表页和详情页中提取结构化字段。
"""

import re
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


# ============================================================
# 采购方式识别映射
# ============================================================

PROCUREMENT_METHOD_MAP = {
    "公开招标": "公开招标",
    "公开比选": "公开询比",
    "公开询价": "公开询比",
    "公开询比": "公开询比",
    "竞争性谈判": "竞争性谈判",
    "单一来源": "单一来源",
    "比选": "公开询比",
    "询价": "公开询比",
}


def _normalize_procurement_method(method: str) -> str:
    """标准化采购方式名称。"""
    if not method:
        return "公开招标"
    method = method.strip()
    for key, value in PROCUREMENT_METHOD_MAP.items():
        if key in method:
            return value
    return method


# ============================================================
# 采购方层级识别
# ============================================================

def _extract_purchaser_level(title: str) -> str:
    """
    从标题中提取采购方层级。

    Examples:
        "中国移动广东公司..." → "省公司"
        "中国移动广东广州分公司..." → "广州分公司"
    """
    if not title:
        return "未知"

    # 地市分公司匹配
    city_pattern = re.compile(
        r"(广州|深圳|东莞|佛山|珠海|中山|惠州|汕头|江门|湛江|"
        r"茂名|肇庆|梅州|汕尾|河源|阳江|清远|潮州|揭阳|云浮|韶关)"
        r"\s*(?:市)?\s*(?:分)?公司"
    )
    city_match = city_pattern.search(title)
    if city_match:
        return f"{city_match.group(1)}分公司"

    if "省公司" in title or "广东公司" in title or "有限公司" in title:
        return "省公司"

    return "未知"


# ============================================================
# 金额提取
# ============================================================

def _extract_budget(text: str) -> Optional[float]:
    """
    从文本中提取预算金额（万元）。

    支持格式：
        "预算金额：500万元"
        "本项目预算为 320.5 万元"
        "采购预算：1,200万"
        "不含税预算 4500000元"
    """
    if not text:
        return None

    patterns = [
        # "XXX万元" / "XXX万" / "XXX 万元"
        r"(\d[\d,.]*)\s*万\s*(?:元)?",
        # "XXX元" → 转换为万元
        r"(\d[\d,.]*)\s*元",
        # "预算金额[：:]\s*(\d[\d,.]*)"
        r"预算(?:金额)?[：:]\s*(\d[\d,.]*)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value_str = match.group(1).replace(",", "")
            try:
                value = float(value_str)
            except ValueError:
                continue
            if "元" in match.group(0) and "万" not in match.group(0):
                value = value / 10000  # 元→万元
            return round(value, 2)

    return None


# ============================================================
# 评分权重提取
# ============================================================

def _extract_score_weight(text: str) -> Optional[Dict[str, float]]:
    """
    从评分办法文本中提取技术分/商务分/价格分权重。

    支持格式：
        "技术分占40%，商务分占30%，价格分占30%"
        "技术：40，商务：30，价格：30"
        "技术权重40%、商务权重30%、价格权重30%"
        "综合评分法：技术部分40分，商务部分30分，价格部分30分"
    """
    if not text:
        return None

    patterns = {
        "tech": [
            # "技术分占40%" / "技术：40" / "技术部分40分" / "技术权重40%"
            r"技术(?:分|部分|权重)?[：:占]?\s*(\d+)\s*(?:%|分|，|,)",
            # 数字在末尾（无后缀）
            r"技术(?:分|部分|权重)?[：:占]?\s*(\d+)\s*$",
        ],
        "biz": [
            r"商务(?:分|部分|权重)?[：:占]?\s*(\d+)\s*(?:%|分|，|,)",
            r"商务(?:分|部分|权重)?[：:占]?\s*(\d+)\s*$",
        ],
        "price": [
            r"价格(?:分|部分|权重)?[：:占]?\s*(\d+)\s*(?:%|分|，|,)",
            r"价格(?:分|部分|权重)?[：:占]?\s*(\d+)\s*$",
        ],
    }

    scores = {}
    for key, pat_list in patterns.items():
        for pat in pat_list:
            match = re.search(pat, text)
            if match:
                scores[key] = float(match.group(1)) / 100.0
                break

    if not scores:
        return None

    # 确保三项齐全，缺项填 0
    result = {
        "tech": scores.get("tech", 0),
        "biz": scores.get("biz", 0),
        "price": scores.get("price", 0),
    }

    # 如果只有一项，尝试归一化推断
    total = sum(result.values())
    if total == 0:
        return None

    return result


# ============================================================
# 资格要求提取
# ============================================================

def _extract_qualification(text: str) -> str:
    """
    从公告正文中提取"供应商资格要求"相关段落。
    """
    if not text:
        return ""

    # 匹配"资格要求"相关段落（从标题到下一个标题或末尾）
    patterns = [
        r"(?:供应商|投标人|申请人|应答人).{0,10}(?:资格|资质).{0,10}(?:要求|条件|审查)[：:]?(.*?)(?:\n\s*(?:[一二三四五六七八九十]、|\d+[.、]|（[一二三四五六七八九十]）))",
        r"(?:资格|资质).{0,5}(?:要求|条件|审查)[：:]?(.*?)(?:\n\s*(?:[一二三四五六七八九十]、|\d+[.、]))",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            result = match.group(1).strip()
            if len(result) > 20:
                return result[:2000]  # 截断过长文本

    # 回退：取"资格"附近 500 字
    idx = text.find("资格")
    if idx >= 0:
        start = max(0, idx - 50)
        end = min(len(text), idx + 500)
        return text[start:end].strip()

    return ""


# ============================================================
# 列表页解析
# ============================================================

def parse_list_page(html: str) -> List[Dict[str, str]]:
    """
    解析公告列表页，提取每条公告的基本信息。

    Args:
        html: 列表页 HTML 内容

    Returns:
        [{"title": "...", "publish_date": "...", "detail_url": "...", "procurement_method": "..."}, ...]
    """
    soup = BeautifulSoup(html, "lxml")
    items = []

    # ── 策略 1：尝试解析标准表格结构 ──
    table = soup.find("table")
    if table:
        rows = table.find_all("tr")[1:]  # 跳过表头
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            item = _parse_list_row_from_cells(cells)
            if item:
                items.append(item)

    # ── 策略 2：尝试解析列表 <li> / <div> 结构 ──
    if not items:
        for container in soup.select(
            ".notice-list li, .list-item, .notice-item, "
            "div[class*='notice'], div[class*='list'], li[class*='item']"
        ):
            item = _parse_list_item_generic(container)
            if item:
                items.append(item)

    # ── 策略 3：搜索所有链接，按标题关键词过滤 ──
    if not items:
        for a_tag in soup.find_all("a", href=True):
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            if not title or not href:
                continue
            # 过滤：至少包含一个招标相关关键词
            if any(kw in title for kw in ["招标", "采购", "公告", "移动", "比选"]):
                items.append({
                    "title": title,
                    "publish_date": "",
                    "detail_url": _resolve_url(href),
                    "procurement_method": "",
                })

    logger.info(f"列表页解析完成，提取 {len(items)} 条公告")
    return items


def _parse_list_row_from_cells(cells: List[Tag]) -> Optional[Dict[str, str]]:
    """从表格行单元格解析公告条目。"""
    try:
        title_cell = cells[0] if cells else None
        if not title_cell:
            return None

        link = title_cell.find("a")
        title = link.get_text(strip=True) if link else title_cell.get_text(strip=True)
        detail_url = _resolve_url(link.get("href", "")) if link else ""

        date_str = ""
        method = ""
        if len(cells) >= 2:
            date_str = cells[1].get_text(strip=True)
        if len(cells) >= 3:
            method = cells[2].get_text(strip=True)

        return {
            "title": title,
            "publish_date": _normalize_date(date_str),
            "detail_url": detail_url,
            "procurement_method": _normalize_procurement_method(method),
        }
    except Exception:
        return None


def _parse_list_item_generic(container: Tag) -> Optional[Dict[str, str]]:
    """从通用容器解析公告条目。"""
    try:
        link = container.find("a")
        if not link:
            return None

        title = link.get_text(strip=True)
        href = link.get("href", "")
        if not title:
            return None

        date_elem = container.find(["span", "time", "div"], class_=re.compile(r"date|time|pub", re.I))
        date_str = date_elem.get_text(strip=True) if date_elem else ""

        return {
            "title": title,
            "publish_date": _normalize_date(date_str),
            "detail_url": _resolve_url(href),
            "procurement_method": "",
        }
    except Exception:
        return None


# ============================================================
# 详情页解析
# ============================================================

def parse_detail_page(html: str, url: str = "") -> Dict[str, any]:
    """
    解析公告详情页，提取完整项目信息。

    Args:
        html: 详情页 HTML 内容
        url: 详情页 URL（用于日志）

    Returns:
        {
            "title": "", "purchaser": "", "purchaser_level": "",
            "procurement_method": "", "budget": null,
            "project_category": "", "announce_date": "", "deadline": "",
            "qualification_requirements": "", "score_weight": null,
            "source_url": ""
        }
    """
    soup = BeautifulSoup(html, "lxml")

    # 提取页面纯文本（用于正则匹配）
    page_text = soup.get_text(separator="\n", strip=True)
    # 限制文本长度以提升正则性能
    page_text_trimmed = page_text[:10000]

    # ── 标题 ──
    title = ""
    title_tag = soup.find(["h1", "h2", "h3"], class_=re.compile(r"title|subject", re.I))
    if not title_tag:
        title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
    if not title:
        # 回退：从文本首行提取
        lines = [l for l in page_text.split("\n") if l.strip()]
        if lines:
            title = lines[0][:200]

    # ── 采购方 ──
    purchaser = _extract_field(page_text_trimmed, [
        r"采购(?:人|方|单位)[：:]\s*(.+?)(?:\n|$)",
        r"采购(?:人|方|单位)\s*[：:]\s*(.+?)(?:。|\n)",
    ])

    # ── 采购方层级 ──
    purchaser_level = _extract_purchaser_level(title)
    if not purchaser_level or purchaser_level == "未知":
        purchaser_level = _extract_purchaser_level(purchaser)

    # ── 采购方式 ──
    method_raw = _extract_field(page_text_trimmed, [
        r"采购方式[：:]\s*(.+?)(?:\n|$)",
        r"(公开招标|公开比选|公开询比|竞争性谈判|单一来源|询价)",
    ])
    procurement_method = _normalize_procurement_method(method_raw)

    # ── 预算金额 ──
    budget = _extract_budget(page_text_trimmed)

    # ── 公告时间 ──
    announce_date = _extract_field(page_text_trimmed, [
        r"(?:公告)?发布日期[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)",
        r"(?:发布|公告)时间[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)",
    ])
    announce_date = _normalize_date(announce_date) if announce_date else ""

    # ── 投标截止时间 ──
    deadline = _extract_field(page_text_trimmed, [
        r"(?:投标|应答|申请|递交)截止(?:时间|日期)[：:]\s*(.+?)(?:\n|$)",
        r"截止(?:时间|日期)[：:]\s*(.+?)(?:\n|$)",
    ])
    deadline = _normalize_datetime(deadline) if deadline else ""

    # ── 资格要求 ──
    qualification_requirements = _extract_qualification(page_text)

    # ── 评分权重 ──
    score_weight = _extract_score_weight(page_text_trimmed)
    if not score_weight:
        # 回退：搜索页面中所有百分比，尝试推断
        score_weight = _extract_score_weight(page_text[:20000])

    # ── 来源 URL ──
    source_url = url

    result = {
        "title": title,
        "purchaser": purchaser,
        "purchaser_level": purchaser_level,
        "procurement_method": procurement_method,
        "budget": budget,
        "project_category": "",  # 由关键词过滤器填充
        "announce_date": announce_date,
        "deadline": deadline,
        "qualification_requirements": qualification_requirements,
        "score_weight": score_weight,
        "source_url": source_url,
    }

    return result


# ============================================================
# 辅助函数
# ============================================================

def _resolve_url(href: str) -> str:
    """补全相对 URL 为绝对 URL。"""
    from .config import BASE_URL

    if not href:
        return ""
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return f"https:{href}"
    if href.startswith("/"):
        return f"{BASE_URL}{href}"
    return f"{BASE_URL}/{href}"


def _extract_field(text: str, patterns: List[str]) -> str:
    """用多个正则模式尝试提取字段值，返回第一个匹配。"""
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""


def _normalize_date(date_str: str) -> str:
    """标准化日期为 YYYY-MM-DD 格式。"""
    if not date_str:
        return ""

    date_str = date_str.strip()

    # YYYY-MM-DD / YYYY/MM/DD
    match = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", date_str)
    if match:
        return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"

    # YYYY年MM月DD日
    match = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日?", date_str)
    if match:
        return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"

    return date_str[:10]


def _normalize_datetime(dt_str: str) -> str:
    """标准化日期时间为 YYYY-MM-DD HH:MM:SS 格式。"""
    if not dt_str:
        return ""

    dt_str = dt_str.strip()

    # 已有完整时间
    match = re.match(
        r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?",
        dt_str,
    )
    if match:
        base = (
            f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)} "
            f"{match.group(4).zfill(2)}:{match.group(5).zfill(2)}"
        )
        if match.group(6):
            base += f":{match.group(6).zfill(2)}"
        else:
            base += ":00"
        return base

    # 只有日期
    date_part = _normalize_date(dt_str)
    if date_part:
        # 尝试提取时间
        time_match = re.search(r"(\d{1,2}):(\d{2})", dt_str)
        if time_match:
            return f"{date_part} {time_match.group(1).zfill(2)}:{time_match.group(2).zfill(2)}:00"
        return f"{date_part} 17:00:00"  # 默认截止时间

    return dt_str[:19]
