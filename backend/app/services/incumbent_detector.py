"""
在位者优势识别模块

判断某个招标项目是否存在"在位者供应商"（Incumbent Supplier），
即在同一采购方、同一项目类别中连续中标的公司。

业务价值：
- 在位者在新一轮招标中有信息优势、关系优势、经验优势
- 新进入者投标时需评估竞争难度，制定差异化策略
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass


# ============================================================
# 输出数据结构
# ============================================================

@dataclass
class IncumbentResult:
    """在位者识别结果"""

    has_incumbent: bool           # 是否存在在位者
    incumbent_name: str            # 在位者公司名称
    continuous_count: int          # 连续中标次数
    contract_end_date: Optional[str]  # 最近合同到期日
    risk_level: str               # 风险等级：高 / 中 / 低 / 无
    latest_winner: str            # 最近一次中标方
    reason: str                   # 判定原因说明


# ============================================================
# 风险等级常量
# ============================================================

RISK_HIGH = "高"
RISK_MEDIUM = "中"
RISK_LOW = "低"
RISK_NONE = "无"

# 高风险的连续中标次数阈值
HIGH_RISK_CONTINUOUS_THRESHOLD = 3

# 中风险的连续中标次数阈值
MEDIUM_RISK_CONTINUOUS_THRESHOLD = 2

# 合同即将到期的月数阈值（到期前3个月内风险降为中）
CONTRACT_EXPIRING_MONTHS = 3


# ============================================================
# 核心函数
# ============================================================

def detect_incumbent(
    current_announcement: Dict,
    historical_awards: List[Dict],
    current_date: Optional[str] = None,
) -> IncumbentResult:
    """
    检测招标项目是否存在在位者供应商。

    Args:
        current_announcement:
            {
                "purchaser_id": int,          # 采购方ID
                "project_category": str,      # 项目类别
                "title": str,                 # 项目名称（用于日志）
            }
        historical_awards:
            [
                {
                    "purchaser_id": int,
                    "project_category": str,
                    "winner_name": str,        # 中标方名称
                    "bid_amount": float,
                    "bid_open_date": str,      # 开标日期 YYYY-MM-DD
                    "contract_start": str,     # 合同开始日期（可选）
                    "contract_end": str,       # 合同结束日期（可选）
                    "is_continuous": bool,     # 是否连续中标
                    "continuous_count": int,   # 连续中标次数
                },
                ...
            ]
        current_date:
            当前日期，格式 YYYY-MM-DD。默认取今天。

    Returns:
        IncumbentResult 在位者识别结果

    Examples:
        >>> awards = [
        ...     {"purchaser_id":1, "project_category":"媒介投放类",
        ...      "winner_name":"省广集团", "bid_open_date":"2024-06-01",
        ...      "is_continuous":True, "continuous_count":3,
        ...      "contract_end":"2025-06-01"},
        ...     {"purchaser_id":1, "project_category":"媒介投放类",
        ...      "winner_name":"省广集团", "bid_open_date":"2023-06-01",
        ...      "is_continuous":True, "continuous_count":2,
        ...      "contract_end":"2024-06-01"},
        ... ]
        >>> result = detect_incumbent(
        ...     {"purchaser_id":1, "project_category":"媒介投放类"},
        ...     awards
        ... )
        >>> result.has_incumbent
        True
        >>> result.incumbent_name
        '省广集团'
        >>> result.risk_level
        '中'
    """
    # ── 第 1 步：参数校验 ──
    purchaser_id = current_announcement.get("purchaser_id")
    project_category = current_announcement.get("project_category", "")

    if purchaser_id is None or not project_category:
        return _no_incumbent("缺少采购方ID或项目类别")

    if not historical_awards:
        return _no_incumbent("无历史中标记录")

    # 标准化当前日期
    today = _parse_date(current_date) if current_date else date.today()

    # ── 第 2 步：筛选匹配的历史记录 ──
    matched = _filter_and_sort(
        historical_awards, purchaser_id, project_category
    )

    if not matched:
        return _no_incumbent(
            f"采购方{purchaser_id}在'{project_category}'赛道无历史中标记录"
        )

    # ── 第 3 步：获取最近一次中标方 ──
    latest = matched[0]  # 已按开标日期降序排列
    latest_winner = _safe_get(latest, "winner_name", "")
    continuous_count = _safe_get(latest, "continuous_count", 1)
    is_continuous = _safe_get(latest, "is_continuous", False)
    contract_end = _safe_get(latest, "contract_end", None)

    if not latest_winner:
        return _no_incumbent("最近中标记录缺失中标方名称")

    # ── 第 4 步：判定在位者 ──
    # 条件1：连续中标次数 >= 2
    if continuous_count < MEDIUM_RISK_CONTINUOUS_THRESHOLD:
        return IncumbentResult(
            has_incumbent=False,
            incumbent_name="",
            continuous_count=continuous_count,
            contract_end_date=contract_end,
            risk_level=RISK_NONE,
            latest_winner=latest_winner,
            reason=(
                f"最近中标方'{latest_winner}'仅中标{continuous_count}次，"
                f"未达到在位者阈值（需≥{MEDIUM_RISK_CONTINUOUS_THRESHOLD}次）"
            ),
        )

    # 条件2：验证最近两期是否同一中标方
    if len(matched) >= 2:
        second_latest_winner = _safe_get(matched[1], "winner_name", "")
        if second_latest_winner and second_latest_winner != latest_winner:
            return IncumbentResult(
                has_incumbent=False,
                incumbent_name="",
                continuous_count=continuous_count,
                contract_end_date=contract_end,
                risk_level=RISK_LOW,
                latest_winner=latest_winner,
                reason=(
                    f"最近一次中标方为'{latest_winner}'，"
                    f"但上一期为'{second_latest_winner}'（不同公司），"
                    f"不存在在位者优势"
                ),
            )

    # ── 第 5 步：评估风险等级 ──
    risk_level = _evaluate_risk_level(
        continuous_count=continuous_count,
        contract_end=contract_end,
        today=today,
    )

    # 生成原因说明
    reason_parts = [
        f"在位者: {latest_winner}",
        f"连续中标{continuous_count}次",
    ]
    if contract_end:
        days_left = (_parse_date(contract_end) - today).days if _parse_date(contract_end) else None
        if days_left is not None:
            reason_parts.append(f"合同到期剩余{days_left}天")

    return IncumbentResult(
        has_incumbent=True,
        incumbent_name=latest_winner,
        continuous_count=continuous_count,
        contract_end_date=contract_end,
        risk_level=risk_level,
        latest_winner=latest_winner,
        reason="；".join(reason_parts),
    )


# ============================================================
# 辅助函数
# ============================================================

def _filter_and_sort(
    awards: List[Dict],
    purchaser_id: int,
    project_category: str,
) -> List[Dict]:
    """
    筛选匹配采购方+赛道的记录，按开标日期降序排列。
    过滤掉 winner_name 为空的脏数据。
    """
    matched = []
    for award in awards:
        if (
            award.get("purchaser_id") == purchaser_id
            and award.get("project_category") == project_category
            and award.get("winner_name")
        ):
            matched.append(award)

    # 按开标日期降序
    matched.sort(
        key=lambda x: x.get("bid_open_date") or "",
        reverse=True,
    )
    return matched


def _evaluate_risk_level(
    continuous_count: int,
    contract_end: Optional[str],
    today: date,
) -> str:
    """
    根据连续中标次数和合同到期时间评估风险等级。

    规则：
    - continuous_count >= 3 → 高风险
    - continuous_count >= 2 → 中风险
    - 若合同在 3 个月内到期 → 降一级（高→中，中→低）
    - 合同已过期 → 风险为低
    """
    # 基础风险
    if continuous_count >= HIGH_RISK_CONTINUOUS_THRESHOLD:
        base_risk = RISK_HIGH
    elif continuous_count >= MEDIUM_RISK_CONTINUOUS_THRESHOLD:
        base_risk = RISK_MEDIUM
    else:
        base_risk = RISK_LOW

    # 合同到期调整
    if contract_end:
        parsed = _parse_date(contract_end)
        if parsed:
            days_remaining = (parsed - today).days

            if days_remaining < 0:
                # 合同已过期
                return RISK_LOW
            elif days_remaining <= CONTRACT_EXPIRING_MONTHS * 30:
                # 3 个月内到期，降一级
                if base_risk == RISK_HIGH:
                    return RISK_MEDIUM
                elif base_risk == RISK_MEDIUM:
                    return RISK_LOW

    return base_risk


def _no_incumbent(reason: str) -> IncumbentResult:
    """快速构造"无在位者"结果。"""
    return IncumbentResult(
        has_incumbent=False,
        incumbent_name="",
        continuous_count=0,
        contract_end_date=None,
        risk_level=RISK_NONE,
        latest_winner="",
        reason=reason,
    )


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """
    安全解析日期字符串。

    支持格式：YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD
    """
    if not date_str:
        return None
    date_str = str(date_str).strip()

    formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str[:10], fmt).date()
        except (ValueError, IndexError):
            continue
    return None


def _safe_get(d: Dict, key: str, default=None):
    """安全获取字典值，空字符串视为 None。"""
    val = d.get(key, default)
    if val == "" or val is None:
        return default
    return val


# ============================================================
# 批量识别
# ============================================================

def batch_detect_incumbents(
    announcements: List[Dict],
    historical_awards: List[Dict],
    current_date: Optional[str] = None,
) -> List[Dict]:
    """
    对多个招标公告批量检测在位者。

    Args:
        announcements: 招标公告列表
        historical_awards: 全部历史中标记录
        current_date: 当前日期

    Returns:
        每个公告附加上 incumbent 检测结果
    """
    results = []
    for ann in announcements:
        result = detect_incumbent(ann, historical_awards, current_date)
        results.append({
            **ann,
            "has_incumbent": result.has_incumbent,
            "incumbent_name": result.incumbent_name,
            "continuous_count": result.continuous_count,
            "contract_end_date": result.contract_end_date,
            "risk_level": result.risk_level,
            "incumbent_reason": result.reason,
        })
    return results


# ============================================================
# 单元测试
# ============================================================

if __name__ == "__main__":
    passed = 0
    failed = 0

    def assert_equal(actual, expected, name):
        global passed, failed
        if actual == expected:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}")
            print(f"     期望: {expected!r}")
            print(f"     实际: {actual!r}")

    def assert_true(condition, name):
        global passed, failed
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}")

    print("=" * 60)
    print("在位者优势识别 — 单元测试")
    print("=" * 60)

    # ── 测试组 1: 典型在位者场景 ──
    print("\n📌 测试组 1: 连续中标 ≥2 次 → 在位者")

    awards_3x = [
        {
            "purchaser_id": 1, "project_category": "媒介投放类",
            "winner_name": "省广集团", "bid_open_date": "2024-06-01",
            "bid_amount": 485.0, "is_continuous": True,
            "continuous_count": 3, "contract_end": "2025-06-01",
        },
        {
            "purchaser_id": 1, "project_category": "媒介投放类",
            "winner_name": "省广集团", "bid_open_date": "2023-06-01",
            "bid_amount": 470.0, "is_continuous": True,
            "continuous_count": 2, "contract_end": "2024-06-01",
        },
        {
            "purchaser_id": 1, "project_category": "媒介投放类",
            "winner_name": "省广集团", "bid_open_date": "2022-06-01",
            "bid_amount": 450.0, "is_continuous": True,
            "continuous_count": 1, "contract_end": "2023-06-01",
        },
    ]

    r = detect_incumbent(
        {"purchaser_id": 1, "project_category": "媒介投放类", "title": "品牌广告投放"},
        awards_3x,
        current_date="2024-07-01",
    )
    assert_true(r.has_incumbent, "在位者=是")
    assert_equal(r.incumbent_name, "省广集团", "在位者=省广集团")
    assert_equal(r.continuous_count, 3, "连续次数=3")
    assert_equal(r.risk_level, "高", "风险=高（≥3次）")

    # ── 测试组 2: 连续2次（中风险） ──
    print("\n📌 测试组 2: 连续2次 → 在位者，中风险")

    awards_2x = [
        {
            "purchaser_id": 1, "project_category": "活动执行类",
            "winner_name": "蓝色光标", "bid_open_date": "2024-05-01",
            "bid_amount": 300.0, "is_continuous": True,
            "continuous_count": 2, "contract_end": "2025-05-01",
        },
        {
            "purchaser_id": 1, "project_category": "活动执行类",
            "winner_name": "蓝色光标", "bid_open_date": "2023-05-01",
            "bid_amount": 280.0, "is_continuous": True,
            "continuous_count": 1, "contract_end": "2024-05-01",
        },
    ]

    r2 = detect_incumbent(
        {"purchaser_id": 1, "project_category": "活动执行类"},
        awards_2x,
        current_date="2024-07-01",
    )
    assert_true(r2.has_incumbent, "在位者=是")
    assert_equal(r2.incumbent_name, "蓝色光标", "在位者=蓝色光标")
    assert_equal(r2.continuous_count, 2, "连续次数=2")
    assert_equal(r2.risk_level, "中", "风险=中（2次）")

    # ── 测试组 3: 合同3个月内到期 → 降级 ──
    print("\n📌 测试组 3: 合同即将到期 → 风险降级")

    awards_expiring = [
        {
            "purchaser_id": 2, "project_category": "新媒体运营类",
            "winner_name": "因赛集团", "bid_open_date": "2024-06-01",
            "bid_amount": 200.0, "is_continuous": True,
            "continuous_count": 3,  # 原本高风险
            "contract_end": "2024-08-15",  # 距2024-07-01仅45天
        },
        {
            "purchaser_id": 2, "project_category": "新媒体运营类",
            "winner_name": "因赛集团", "bid_open_date": "2023-06-01",
            "bid_amount": 190.0, "is_continuous": True,
            "continuous_count": 2,
            "contract_end": "2024-06-01",
        },
    ]

    r3 = detect_incumbent(
        {"purchaser_id": 2, "project_category": "新媒体运营类"},
        awards_expiring,
        current_date="2024-07-01",
    )
    assert_true(r3.has_incumbent, "在位者=是")
    assert_equal(r3.risk_level, "中", "风险=中（合同3月内到期，降级）")

    # ── 测试组 4: 合同已过期 → 低风险 ──
    print("\n📌 测试组 4: 合同已过期 → 低风险")

    awards_expired = [
        {
            "purchaser_id": 3, "project_category": "品牌策略类",
            "winner_name": "华扬联众", "bid_open_date": "2023-01-01",
            "bid_amount": 400.0, "is_continuous": True,
            "continuous_count": 3,
            "contract_end": "2023-12-31",  # 早已过期
        },
    ]

    r4 = detect_incumbent(
        {"purchaser_id": 3, "project_category": "品牌策略类"},
        awards_expired,
        current_date="2024-07-01",
    )
    assert_true(r4.has_incumbent, "在位者=是（虽然过期但仍是在位者）")
    assert_equal(r4.risk_level, "低", "风险=低（合同已过期）")

    # ── 测试组 5: 中标方不固定 → 无在位者 ──
    print("\n📌 测试组 5: 不同公司交替中标 → 无在位者")

    awards_mixed = [
        {
            "purchaser_id": 1, "project_category": "内容制作类",
            "winner_name": "小公司A", "bid_open_date": "2024-03-01",
            "bid_amount": 100.0, "is_continuous": False,
            "continuous_count": 1, "contract_end": "2025-03-01",
        },
        {
            "purchaser_id": 1, "project_category": "内容制作类",
            "winner_name": "小公司B", "bid_open_date": "2023-03-01",
            "bid_amount": 95.0, "is_continuous": False,
            "continuous_count": 1, "contract_end": "2024-03-01",
        },
    ]

    r5 = detect_incumbent(
        {"purchaser_id": 1, "project_category": "内容制作类"},
        awards_mixed,
    )
    assert_true(not r5.has_incumbent, "无在位者（不同公司）")
    # continuous_count=1 → 不满足阈值，风险为"无"
    assert_equal(r5.risk_level, "无", "风险=无（连续次数不足）")
    assert_true("仅中标1次" in r5.reason or "不足" in r5.reason, "原因含'仅中标1次'")

    # ── 测试组 6: 边界情况 ──
    print("\n📌 测试组 6: 边界情况")

    # 空历史
    r6a = detect_incumbent(
        {"purchaser_id": 999, "project_category": "品牌策略类"},
        [],
    )
    assert_true(not r6a.has_incumbent, "空历史→无在位者")
    assert_equal(r6a.risk_level, "无", "风险=无")
    assert_equal(r6a.reason, "无历史中标记录", "原因正确")

    # 缺少 purchaser_id
    r6b = detect_incumbent(
        {"project_category": "品牌策略类"},
        awards_3x,
    )
    assert_true(not r6b.has_incumbent, "缺purchaser_id→无在位者")

    # 历史数据缺合同日期
    awards_no_contract = [
        {
            "purchaser_id": 1, "project_category": "媒介投放类",
            "winner_name": "省广集团", "bid_open_date": "2024-06-01",
            "bid_amount": 485.0, "is_continuous": True,
            "continuous_count": 3,
            "contract_end": None,  # 无合同信息
        },
    ]
    r6c = detect_incumbent(
        {"purchaser_id": 1, "project_category": "媒介投放类"},
        awards_no_contract,
    )
    assert_true(r6c.has_incumbent, "缺合同日期→仍识别在位者")
    assert_equal(r6c.risk_level, "高", "风险=高（缺合同日期不降级）")
    assert_equal(r6c.contract_end_date, None, "合同日为None")

    # 仅中标1次
    awards_single = [
        {
            "purchaser_id": 1, "project_category": "创意设计类",
            "winner_name": "某设计公司", "bid_open_date": "2024-01-01",
            "bid_amount": 50.0, "is_continuous": False,
            "continuous_count": 1, "contract_end": "2025-01-01",
        },
    ]
    r6d = detect_incumbent(
        {"purchaser_id": 1, "project_category": "创意设计类"},
        awards_single,
    )
    assert_true(not r6d.has_incumbent, "仅1次→无在位者")
    assert_equal(r6d.risk_level, "无", "风险=无")

    # 不同赛道不匹配
    r6e = detect_incumbent(
        {"purchaser_id": 1, "project_category": "创意设计类"},
        awards_3x,  # 这是 媒介投放类
    )
    assert_true(not r6e.has_incumbent, "赛道不匹配→无在位者")

    # ── 测试组 7: 批量识别 ──
    print("\n📌 测试组 7: 批量识别")

    all_awards = awards_3x + awards_2x + awards_mixed  # 3组历史数据混合
    batch_input = [
        {"id": 1, "purchaser_id": 1, "project_category": "媒介投放类", "title": "项目A"},
        {"id": 2, "purchaser_id": 1, "project_category": "活动执行类", "title": "项目B"},
        {"id": 3, "purchaser_id": 1, "project_category": "内容制作类", "title": "项目C"},
    ]
    batch_results = batch_detect_incumbents(batch_input, all_awards)

    assert_equal(len(batch_results), 3, "批量返回3条")
    assert_true(batch_results[0]["has_incumbent"], "项目A有位者")
    assert_true(batch_results[1]["has_incumbent"], "项目B有位者")
    assert_true(not batch_results[2]["has_incumbent"], "项目C无在位者")

    # ── 结果汇总 ──
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"  测试结果: {passed}/{total} 通过", end="")
    if failed > 0:
        print(f"  ❌ {failed} 个失败")
    else:
        print("  🎉 全部通过！")
    print("=" * 60)
