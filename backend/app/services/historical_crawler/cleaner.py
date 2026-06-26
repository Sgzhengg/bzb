"""
数据清洗与标准化模块

负责：
- 金额单位统一（→万元）
- 采购方名称标准化
- 中标方类型识别
- 项目赛道识别（集成关键词过滤器）
- 日期标准化
"""

import re
import sys
import os
from typing import Optional, Dict, List

# 集成关键词过滤器
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from keyword_filter import filter_advertisement_projects
except ImportError:
    from app.services.keyword_filter import filter_advertisement_projects


# ============================================================
# 采购方名称标准化
# ============================================================

# 广东移动下属 21 个地市分公司
CITY_NAMES = [
    "广州", "深圳", "东莞", "佛山", "珠海", "中山", "惠州",
    "汕头", "江门", "湛江", "茂名", "肇庆", "梅州", "汕尾",
    "河源", "阳江", "清远", "潮州", "揭阳", "云浮", "韶关",
]


def normalize_purchaser_name(name: str) -> str:
    """
    标准化采购方名称。

    "中国移动通信集团广东有限公司东莞分公司" → "东莞分公司"
    "中国移动通信集团广东有限公司" → "省公司"
    "中国移动广东公司广州分公司" → "广州分公司"
    """
    if not name:
        return "未知"

    name = name.strip()

    # 省公司：含"移动"+"广东"且不含"分公司"
    if ("移动" in name or "中移" in name) and "广东" in name and "分公司" not in name:
        return "省公司"

    # 地市分公司
    for city in CITY_NAMES:
        if city in name:
            return f"{city}分公司"

    # 回退：保留最后一段
    parts = re.split(r"[有限]公司", name)
    if len(parts) > 1:
        last = parts[-1].strip()
        if last:
            return last

    return name


def normalize_winner_name(name: str) -> str:
    """
    标准化中标方名称。
    去除多余空格、统一全角半角。
    """
    if not name:
        return ""
    name = name.strip()
    # 去除多余空格
    name = re.sub(r"\s+", "", name)
    return name


# ============================================================
# 金额清洗
# ============================================================

def normalize_amount(text: str) -> Optional[float]:
    """
    将各种金额格式统一转换为万元（数值）。

    支持格式：
        "3800000元" → 380.0
        "500万元"   → 500.0
        "1200万"    → 1200.0
        "不含税：450万元" → 450.0
        "0.05亿元"  → 500.0
        "预算380万，中标365万" → 取第一个
    """
    if not text:
        return None

    text = text.strip().replace(",", "").replace("，", "")

    # 亿元
    match = re.search(r"(\d+\.?\d*)\s*亿", text)
    if match:
        return float(match.group(1)) * 10000

    # 万元
    match = re.search(r"(\d+\.?\d*)\s*万", text)
    if match:
        return round(float(match.group(1)), 2)

    # 元
    match = re.search(r"(\d{4,})[元整]", text)
    if match:
        return round(float(match.group(1)) / 10000, 2)

    return None


def extract_bid_and_budget(text: str) -> tuple:
    """
    从公告文本中同时提取中标金额和预算金额。

    Returns:
        (中标金额_万元, 预算金额_万元)
    """
    bid_amount = None
    budget_amount = None

    if not text:
        return None, None

    # 策略1：明确的"中标金额"和"预算金额"
    bid_patterns = [
        r"中标(?:金额|价|价格)[：:]?\s*(.+?)(?:[；;。]|\n|$)",
        r"成交(?:金额|价|价格)[：:]?\s*(.+?)(?:[；;。]|\n|$)",
        r"中选(?:金额|价|价格)[：:]?\s*(.+?)(?:[；;。]|\n|$)",
    ]
    budget_patterns = [
        r"(?:采购|项目)?预算(?:金额)?[：:]?\s*(.+?)(?:[；;。]|\n|$)",
        r"项目预算[：:]?\s*(.+?)(?:[；;。]|\n|$)",
    ]

    for pat in bid_patterns:
        match = re.search(pat, text)
        if match:
            bid_amount = normalize_amount(match.group(1))
            break

    for pat in budget_patterns:
        match = re.search(pat, text)
        if match:
            budget_amount = normalize_amount(match.group(1))
            break

    # 策略2：从文本中提取所有金额，取最大值作为中标金额
    if bid_amount is None:
        amounts = []
        for m in re.finditer(r"(\d+\.?\d*)\s*万", text):
            amounts.append(float(m.group(1)))
        if amounts:
            # 跳过明显是预算的描述
            bid_amount = max(amounts)

    return bid_amount, budget_amount


# ============================================================
# 中标方类型识别
# ============================================================

# 广东移动广告类头部常客
HEAD_PLAYERS = [
    "省广", "因赛", "华扬联众", "蓝色光标", "电通", "奥美",
    "阳狮", "群邑", "宏盟", "广东省广告", "GIMC", "引力传媒",
    "天下秀", "浙文互联", "三人行", "思美传媒", "华媒控股",
    "中广", "凤凰", "分众", "新潮", "兆讯",
]

# 广东本地中小广告公司特征
SMALL_PLAYER_KEYWORDS = [
    "文化传播", "广告公司", "传媒", "营销策划", "品牌策划",
    "设计公司", "公关", "展览展示", "会展", "活动策划",
]


def identify_winner_type(winner_name: str) -> str:
    """
    识别中标方类型。

    Returns:
        "头部常客" / "中小公司" / "新进入者"
    """
    if not winner_name:
        return "新进入者"

    # 头部常客
    for head in HEAD_PLAYERS:
        if head in winner_name:
            return "头部常客"

    # 中小公司
    for kw in SMALL_PLAYER_KEYWORDS:
        if kw in winner_name:
            return "中小公司"

    # 默认
    return "新进入者"


# ============================================================
# 折扣率计算
# ============================================================

def calc_discount_rate(bid_amount: Optional[float], budget_amount: Optional[float]) -> Optional[float]:
    """
    计算折扣率 = 中标金额 / 预算金额 × 100%。
    """
    if bid_amount is not None and budget_amount is not None and budget_amount > 0:
        return round(bid_amount / budget_amount * 100, 2)
    return None


# ============================================================
# 合同期限提取
# ============================================================

def extract_contract_period(text: str) -> Dict[str, Optional[str]]:
    """
    从公告文本提取合同期限。

    Returns:
        {"contract_start": "YYYY-MM-DD", "contract_end": "YYYY-MM-DD"}
    """
    result = {"contract_start": None, "contract_end": None}

    if not text:
        return result

    # "合同期限：2023年6月1日至2024年5月31日"
    match = re.search(
        r"合同(?:期限|履行期|有效期)[：:]\s*"
        r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?\s*[至到-]\s*"
        r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?",
        text,
    )
    if match:
        result["contract_start"] = (
            f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
        )
        result["contract_end"] = (
            f"{match.group(4)}-{match.group(5).zfill(2)}-{match.group(6).zfill(2)}"
        )
        return result

    # "自合同签订之日起1年" → 从开标日期推算
    match = re.search(r"自(?:合同)?(?:签订|签署|生效).{0,5}起\s*(\d+)\s*(?:个)?(年|月|天)", text)
    if match:
        # 无法推算具体日期，标记为相对期限
        result["contract_end"] = f"签订日+{match.group(1)}{match.group(2)}"
        return result

    return result


# ============================================================
# 完整清洗管道
# ============================================================

def clean_award_record(raw: Dict) -> Dict:
    """
    对单条中标记录执行完整的数据清洗。

    Args:
        raw: 原始解析结果，包含 title, purchaser, winner_name, bid_amount_raw, 等

    Returns:
        清洗后的标准化记录
    """
    title = raw.get("title", "")
    content = raw.get("content", "") or raw.get("qualification_requirements", "")

    # ── 采购方标准化 ──
    purchaser_raw = raw.get("purchaser", "") or ""
    purchaser = normalize_purchaser_name(purchaser_raw)
    if purchaser in ("未知", "") and title:
        purchaser = normalize_purchaser_name(title)

    # ── 中标方 ──
    winner_raw = raw.get("winner_name", "") or ""
    winner_name = normalize_winner_name(winner_raw)

    # 如果解析器没提取到中标方，尝试从标题推断
    if not winner_name and title:
        match = re.search(r"(.+?)(?:中标|中选|成交)", title)
        if match and len(match.group(1)) < 50:
            winner_name = normalize_winner_name(match.group(1))

    # ── 金额清洗 ──
    bid_amount = raw.get("bid_amount")
    budget_amount = raw.get("budget_amount")
    if bid_amount is None or budget_amount is None:
        full_text = f"{title} {content} {raw.get('bid_amount_raw', '')} {raw.get('budget_amount_raw', '')}"
        extracted_bid, extracted_budget = extract_bid_and_budget(full_text)
        if bid_amount is None:
            bid_amount = extracted_bid
        if budget_amount is None:
            budget_amount = extracted_budget

    # ── 折扣率 ──
    discount_rate = calc_discount_rate(bid_amount, budget_amount)

    # ── 中标方类型 ──
    winner_type = identify_winner_type(winner_name)

    # ── 项目赛道（集成关键词过滤器） ──
    filter_result = filter_advertisement_projects(title, content)
    project_category = filter_result.get("category", "")

    # ── 合同期限 ──
    contract = extract_contract_period(content)

    # ── 日期标准化 ──
    bid_open_date = _normalize_date_str(raw.get("bid_open_date", "") or raw.get("publish_date", ""))

    # ── 组装结果 ──
    cleaned = {
        "project_name": title,
        "purchaser": purchaser,
        "purchaser_raw": purchaser_raw,
        "winner_name": winner_name,
        "winner_type": winner_type,
        "bid_amount": bid_amount,
        "budget_amount": budget_amount,
        "discount_rate": discount_rate,
        "project_category": project_category,
        "bid_open_date": bid_open_date,
        "contract_start": contract["contract_start"],
        "contract_end": contract["contract_end"],
        "matched_keywords": filter_result.get("matched_keywords", []),
        "source_url": raw.get("source_url", ""),
    }

    return cleaned


def _normalize_date_str(date_str: str) -> str:
    """标准化日期字符串为 YYYY-MM-DD。"""
    if not date_str:
        return ""
    date_str = date_str.strip()

    patterns = [
        (r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", "{}-{:02d}-{:02d}"),
        (r"(\d{4})年(\d{1,2})月(\d{1,2})日?", "{}-{:02d}-{:02d}"),
    ]
    for pat, fmt in patterns:
        m = re.match(pat, date_str)
        if m:
            return fmt.format(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return date_str[:10]


# ============================================================
# 批量清洗
# ============================================================

def batch_clean(records: List[Dict]) -> List[Dict]:
    """批量清洗中标记录。"""
    return [clean_award_record(r) for r in records]
