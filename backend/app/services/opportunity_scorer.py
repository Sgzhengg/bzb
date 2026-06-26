"""
机会评分引擎

对每条新招标公告自动计算综合推荐指数（0-100分），
帮助用户判断是否值得投入资源参与投标。

评分维度（6项）：
  1. 采购方式公平性    — 20%
  2. 历史中标集中度    — 20%
  3. 项目类型匹配度    — 20%
  4. 预算健康度        — 15%
  5. 在位者优势        — 15%
  6. 客情关系强度      — 10%
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter


# ============================================================
# 权重配置
# ============================================================

WEIGHTS = {
    "procurement_fairness": 0.20,   # 采购方式公平性
    "hhi_concentration":   0.20,    # 历史中标集中度（HHI）
    "category_match":      0.20,    # 项目类型匹配度
    "budget_health":       0.15,    # 预算健康度
    "incumbent_advantage": 0.15,    # 在位者优势
    "client_relation":     0.10,    # 客情关系强度
}

# 验证权重总和 = 1.0
assert abs(sum(WEIGHTS.values()) - 1.0) < 0.001, "权重总和必须为 1.0"


# ============================================================
# 陪跑概率标签
# ============================================================

def _probability_label(score: float) -> str:
    """根据总分判定陪跑概率标签。"""
    if score >= 75:
        return "低"
    elif score >= 50:
        return "中"
    else:
        return "高"


# ============================================================
# 输出数据结构
# ============================================================

@dataclass
class ScoreDetail:
    """各维度评分明细"""
    procurement_fairness: float = 0.0
    hhi_concentration: float = 0.0
    category_match: float = 0.0
    budget_health: float = 0.0
    incumbent_advantage: float = 0.0
    client_relation: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "procurement_fairness": self.procurement_fairness,
            "hhi_concentration": self.hhi_concentration,
            "category_match": self.category_match,
            "budget_health": self.budget_health,
            "incumbent_advantage": self.incumbent_advantage,
            "client_relation": self.client_relation,
        }


@dataclass
class OpportunityScore:
    """机会评分结果"""
    total_score: float
    probability_label: str       # "高" / "中" / "低"（陪跑概率）
    recommendation: str          # 推荐建议文本
    detail_scores: ScoreDetail

    def to_dict(self) -> Dict:
        return {
            "total_score": self.total_score,
            "probability_label": self.probability_label,
            "recommendation": self.recommendation,
            "detail_scores": self.detail_scores.to_dict(),
        }


# ============================================================
# 1. 采购方式公平性评分（权重20%）
# ============================================================

PROCUREMENT_SCORE_MAP = {
    "公开招标":     100,
    "公开询比":     80,
    "竞争性谈判":   50,
    "单一来源":     0,
}


def _score_procurement_fairness(procurement_method: str) -> float:
    """
    根据采购方式评估公平性。

    公开招标最公平，单一来源最不公平。
    未知方式默认给 60 分（中性）。
    """
    if not procurement_method:
        return 60.0
    method = procurement_method.strip()
    return float(PROCUREMENT_SCORE_MAP.get(method, 60.0))


# ============================================================
# 2. HHI 集中度计算 & 评分（权重20%）
# ============================================================

def calculate_hhi(
    awards: List[Dict],
    purchaser_id: Optional[int] = None,
) -> float:
    """
    计算赫芬达尔-赫希曼指数（HHI）。

    HHI = Σ(每个供应商的市场份额² × 10000)
    市场份额以中标金额占比计算。

    Args:
        awards: 历史中标记录列表
        purchaser_id: 可选，限定特定采购方

    Returns:
        HHI 指数值。无数据时返回 0。

    Reference:
        HHI < 1500: 竞争分散
        1500 ≤ HHI < 2500: 中度集中
        HHI ≥ 2500: 高度集中
    """
    if not awards:
        return 0.0

    # 筛选
    if purchaser_id is not None:
        awards = [a for a in awards if a.get("purchaser_id") == purchaser_id]

    if not awards:
        return 0.0

    # 按供应商聚合金额
    supplier_amounts: Dict[str, float] = {}
    for award in awards:
        winner = award.get("winner_name", "").strip()
        if not winner:
            continue
        amount = award.get("bid_amount") or 0
        supplier_amounts[winner] = supplier_amounts.get(winner, 0) + float(amount)

    total = sum(supplier_amounts.values())
    if total <= 0:
        return 0.0

    # HHI = Σ(market_share² × 10000)
    hhi = 0.0
    for amount in supplier_amounts.values():
        share = amount / total
        hhi += share * share * 10000

    return round(hhi, 1)


def _score_hhi(hhi: float) -> float:
    """
    根据 HHI 指数评估竞争程度。

    HHI 越低 → 竞争越分散 → 机会越大 → 分越高
    """
    if hhi < 1500:
        return 100.0
    elif hhi < 2500:
        return 60.0
    else:
        return 20.0


def _score_hhi_from_history(
    historical_awards: List[Dict],
    purchaser_id: int,
) -> float:
    """从历史中标记录计算 HHI 并评分。"""
    hhi = calculate_hhi(historical_awards, purchaser_id=purchaser_id)
    return _score_hhi(hhi)


# ============================================================
# 3. 项目类型匹配度评分（权重20%）
# ============================================================

def _score_category_match(
    project_category: str,
    preferred_categories: Optional[List[str]] = None,
) -> float:
    """
    根据用户预设的擅长赛道评估匹配度。

    Args:
        project_category: 项目赛道
        preferred_categories: 用户擅长的赛道列表，None 表示未设置

    Returns:
        匹配 100，不匹配 50（可以尝试），未设置 60（中性）
    """
    if not preferred_categories:
        return 60.0  # 用户未设置偏好，中性分

    if not project_category:
        return 50.0

    if project_category in preferred_categories:
        return 100.0
    else:
        return 50.0  # 不匹配但不是 0，保留尝试空间


# ============================================================
# 4. 预算健康度评分（权重15%）
# ============================================================

def _score_budget_health(
    historical_awards: List[Dict],
    purchaser_id: int,
    project_category: str,
) -> float:
    """
    基于同类项目历史折扣率评估预算健康度。

    折扣率 = 中标金额 / 预算金额 × 100%
    折扣率越高 → 预算越真实 → 利润空间越好

    Args:
        historical_awards: 历史中标记录
        purchaser_id: 采购方ID
        project_category: 项目类别

    Returns:
        预算健康度分数
    """
    # 筛选同类项目
    relevant = [
        a for a in historical_awards
        if (
            a.get("purchaser_id") == purchaser_id
            and a.get("project_category") == project_category
            and a.get("bid_amount") is not None
            and a.get("budget_amount") is not None
            and a.get("budget_amount", 0) > 0
        )
    ]

    if not relevant:
        return 60.0  # 无历史参考数据，中性分

    # 计算平均折扣率
    total_discount = 0.0
    count = 0
    for award in relevant:
        bid = float(award.get("bid_amount", 0))
        budget = float(award.get("budget_amount", 0))
        if budget > 0:
            total_discount += bid / budget * 100
            count += 1

    if count == 0:
        return 60.0

    avg_discount = total_discount / count

    # 评分映射
    if avg_discount >= 85:
        return 100.0  # 预算真实，利润健康
    elif avg_discount >= 70:
        return 70.0
    else:
        return 40.0  # 价格战激烈


# ============================================================
# 5. 在位者优势评分（权重15%）
# ============================================================

def _score_incumbent(
    has_incumbent: bool,
    continuous_count: int,
    risk_level: str,
) -> float:
    """
    根据在位者检测结果评估机会。

    Args:
        has_incumbent: 是否存在在位者
        continuous_count: 连续中标次数
        risk_level: 在位者风险等级（高/中/低/无）

    Returns:
        无在位者 → 100（机会大）
        有在位者但即将到期 → 50
        在位者连续2次 → 20
        在位者连续≥3次 → 0
    """
    if not has_incumbent:
        return 100.0

    # 在位者存在的情况
    if continuous_count >= 3:
        return 0.0
    elif continuous_count >= 2:
        # 检查是否合同即将到期（risk_level 已是降级后的结果）
        if risk_level in ("中", "低"):
            return 50.0
        return 20.0
    else:
        return 70.0  # 仅1次在位（理论上不会到这里，保底）


# ============================================================
# 6. 客情关系强度评分（权重10%）
# ============================================================

def _score_client_relation(
    client_relations: List[Dict],
    purchaser_id: int,
) -> float:
    """
    根据该采购方的客情记录评估关系强度。

    Args:
        client_relations: 客情记录列表
        purchaser_id: 采购方ID

    Returns:
        S: 100, A: 80, B: 60, C/D: 30, 无记录: 0
    """
    if not client_relations:
        return 0.0

    # 筛选该采购方的客情记录
    matched = [
        r for r in client_relations
        if r.get("purchaser_id") == purchaser_id
    ]

    if not matched:
        return 0.0

    # 取最高评级（S > A > B > C > D）
    rating_order = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
    best_rating = "D"
    best_order = 0
    for r in matched:
        rating = (r.get("rating") or "D").strip().upper()
        order = rating_order.get(rating, 0)
        if order > best_order:
            best_order = order
            best_rating = rating

    score_map = {"S": 100, "A": 80, "B": 60, "C": 30, "D": 30}
    return float(score_map.get(best_rating, 0))


# ============================================================
# 综合评分引擎
# ============================================================

def calculate_opportunity_score(
    announcement: Dict,
    historical_awards: List[Dict],
    preferred_categories: Optional[List[str]] = None,
    client_relations: Optional[List[Dict]] = None,
    incumbent_result: Optional[Dict] = None,
) -> OpportunityScore:
    """
    对一条招标公告计算综合机会评分。

    Args:
        announcement:
            {
                "title": str,
                "purchaser_id": int,
                "procurement_method": str,
                "project_category": str,
                "budget": float | None,
            }
        historical_awards:
            历史中标记录列表（需含 purchaser_id, project_category,
            winner_name, bid_amount, budget_amount, is_continuous,
            continuous_count, contract_end 等字段）
        preferred_categories:
            用户预设的擅长赛道列表，如 ["媒介投放类", "品牌策略类"]
        client_relations:
            客情记录列表，含 purchaser_id, rating 等
        incumbent_result:
            在位者检测结果，如 {"has_incumbent": True, "continuous_count": 3,
            "risk_level": "高"}。
            若不传则默认为无在位者。

    Returns:
        OpportunityScore 综合评分结果

    Examples:
        >>> score = calculate_opportunity_score(
        ...     {"purchaser_id":1, "procurement_method":"公开招标",
        ...      "project_category":"媒介投放类"},
        ...     historical_awards=[],
        ...     preferred_categories=["媒介投放类"],
        ... )
        >>> score.total_score > 70
        True
    """
    purchaser_id = announcement.get("purchaser_id", 0)
    procurement_method = announcement.get("procurement_method", "")
    project_category = announcement.get("project_category", "")

    inc = incumbent_result or {}
    has_incumbent = inc.get("has_incumbent", False)
    inc_continuous = inc.get("continuous_count", 0)
    inc_risk = inc.get("risk_level", "无")

    # ── 维度1: 采购方式公平性 (20%) ──
    s1 = _score_procurement_fairness(procurement_method)

    # ── 维度2: HHI 集中度 (20%) ──
    s2 = _score_hhi_from_history(historical_awards, purchaser_id)

    # ── 维度3: 项目类型匹配度 (20%) ──
    s3 = _score_category_match(project_category, preferred_categories)

    # ── 维度4: 预算健康度 (15%) ──
    s4 = _score_budget_health(historical_awards, purchaser_id, project_category)

    # ── 维度5: 在位者优势 (15%) ──
    s5 = _score_incumbent(has_incumbent, inc_continuous, inc_risk)

    # ── 维度6: 客情关系强度 (10%) ──
    s6 = _score_client_relation(client_relations or [], purchaser_id)

    # ── 加权求和 ──
    total = (
        s1 * WEIGHTS["procurement_fairness"]
        + s2 * WEIGHTS["hhi_concentration"]
        + s3 * WEIGHTS["category_match"]
        + s4 * WEIGHTS["budget_health"]
        + s5 * WEIGHTS["incumbent_advantage"]
        + s6 * WEIGHTS["client_relation"]
    )
    total = round(total, 1)

    # ── 陪跑概率 & 建议 ──
    label = _probability_label(total)
    recommendation = _make_recommendation(label, total, s5, s6)

    return OpportunityScore(
        total_score=total,
        probability_label=label,
        recommendation=recommendation,
        detail_scores=ScoreDetail(
            procurement_fairness=s1,
            hhi_concentration=s2,
            category_match=s3,
            budget_health=s4,
            incumbent_advantage=s5,
            client_relation=s6,
        ),
    )


def _make_recommendation(
    label: str, total: float,
    incumbent_score: float, relation_score: float,
) -> str:
    """生成人类可读的推荐建议。"""
    if label == "低":
        return "✅ 推荐参与：竞争环境公平，中标概率较高"
    elif label == "中":
        parts = []
        if incumbent_score < 50:
            parts.append("在位者强势")
        if relation_score < 50:
            parts.append("客情关系较弱")
        if parts:
            return f"⚠️ 可考虑参与，但需注意：{'、'.join(parts)}"
        return "⚠️ 可考虑参与，建议进一步评估"
    else:
        if incumbent_score <= 20:
            return "❌ 不建议投入：在位者优势极强，陪跑概率高"
        elif relation_score == 0:
            return "❌ 不建议投入：无客情关系且竞争激烈"
        return "❌ 不建议投入：综合评分过低，陪跑概率高"


# ============================================================
# 批量评分
# ============================================================

def batch_score_opportunities(
    announcements: List[Dict],
    historical_awards: List[Dict],
    preferred_categories: Optional[List[str]] = None,
    client_relations: Optional[List[Dict]] = None,
    incumbent_results: Optional[List[Dict]] = None,
) -> List[Dict]:
    """
    批量计算多条招标公告的机会评分。

    Returns:
        每条公告附加上 total_score / probability_label / detail_scores
    """
    results = []
    inc_map = {}
    if incumbent_results:
        # 按 purchaser_id 建立索引（简化：假设按顺序对应）
        inc_map = {i: incumbent_results[i] for i in range(len(incumbent_results))}

    for idx, ann in enumerate(announcements):
        inc = inc_map.get(idx) if inc_map else None
        score = calculate_opportunity_score(
            ann, historical_awards,
            preferred_categories=preferred_categories,
            client_relations=client_relations,
            incumbent_result=inc,
        )
        results.append({**ann, **score.to_dict()})

    # 按总分降序排列
    results.sort(key=lambda x: x["total_score"], reverse=True)
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

    def assert_between(val, lo, hi, name):
        global passed, failed
        if lo <= val <= hi:
            passed += 1
            print(f"  ✅ {name} ({val})")
        else:
            failed += 1
            print(f"  ❌ {name}: {val} not in [{lo}, {hi}]")

    print("=" * 60)
    print("机会评分引擎 — 单元测试")
    print("=" * 60)

    # ── 测试组 1: 采购方式公平性 ──
    print("\n📌 测试组 1: 采购方式公平性评分")

    assert_equal(_score_procurement_fairness("公开招标"), 100, "公开招标→100")
    assert_equal(_score_procurement_fairness("公开询比"), 80, "公开询比→80")
    assert_equal(_score_procurement_fairness("竞争性谈判"), 50, "竞争性谈判→50")
    assert_equal(_score_procurement_fairness("单一来源"), 0, "单一来源→0")
    assert_equal(_score_procurement_fairness(""), 60, "空值→60")
    assert_equal(_score_procurement_fairness("未知方式"), 60, "未知→60")

    # ── 测试组 2: HHI 计算 ──
    print("\n📌 测试组 2: HHI 计算与评分")

    # 完全分散：4家各25%
    awards_dispersed = [
        {"winner_name": "A", "bid_amount": 250, "purchaser_id": 1},
        {"winner_name": "B", "bid_amount": 250, "purchaser_id": 1},
        {"winner_name": "C", "bid_amount": 250, "purchaser_id": 1},
        {"winner_name": "D", "bid_amount": 250, "purchaser_id": 1},
    ]
    hhi1 = calculate_hhi(awards_dispersed)
    assert_equal(hhi1, 2500.0, "4家均分 HHI=2500")
    assert_equal(_score_hhi(hhi1), 20.0, "HHI=2500→20分（高度集中）")

    # 极度分散：10家各10%
    awards_very_dispersed = [
        {"winner_name": f"公司{i}", "bid_amount": 100, "purchaser_id": 1}
        for i in range(10)
    ]
    hhi2 = calculate_hhi(awards_very_dispersed)
    assert_equal(hhi2, 1000.0, "10家均分 HHI=1000")
    assert_equal(_score_hhi(hhi2), 100.0, "HHI=1000→100分")

    # 一家独占
    awards_monopoly = [
        {"winner_name": "垄断公司", "bid_amount": 1000, "purchaser_id": 1},
    ]
    hhi3 = calculate_hhi(awards_monopoly)
    assert_equal(hhi3, 10000.0, "一家独占 HHI=10000")
    assert_equal(_score_hhi(hhi3), 20.0, "HHI=10000→20分")

    # 空数据
    assert_equal(calculate_hhi([]), 0.0, "空列表 HHI=0")

    # ── 测试组 3: 项目类型匹配度 ──
    print("\n📌 测试组 3: 项目类型匹配度评分")

    assert_equal(
        _score_category_match("媒介投放类", ["媒介投放类", "品牌策略类"]),
        100, "匹配→100"
    )
    assert_equal(
        _score_category_match("创意设计类", ["媒介投放类", "品牌策略类"]),
        50, "不匹配→50"
    )
    assert_equal(
        _score_category_match("媒介投放类", None),
        60, "未设置偏好→60"
    )
    assert_equal(
        _score_category_match("", ["媒介投放类"]),
        50, "项目无类别→50"
    )

    # ── 测试组 4: 预算健康度 ──
    print("\n📌 测试组 4: 预算健康度评分")

    awards_healthy = [
        {"purchaser_id": 1, "project_category": "媒介投放类",
         "bid_amount": 480, "budget_amount": 500},  # 折扣率 96%
        {"purchaser_id": 1, "project_category": "媒介投放类",
         "bid_amount": 450, "budget_amount": 500},  # 折扣率 90%
    ]
    s4a = _score_budget_health(awards_healthy, 1, "媒介投放类")
    assert_equal(s4a, 100.0, "平均折扣93%→100分")

    awards_moderate = [
        {"purchaser_id": 1, "project_category": "媒介投放类",
         "bid_amount": 375, "budget_amount": 500},  # 折扣率 75%
    ]
    s4b = _score_budget_health(awards_moderate, 1, "媒介投放类")
    assert_equal(s4b, 70.0, "折扣75%→70分")

    awards_cutthroat = [
        {"purchaser_id": 1, "project_category": "媒介投放类",
         "bid_amount": 300, "budget_amount": 500},  # 折扣率 60%
    ]
    s4c = _score_budget_health(awards_cutthroat, 1, "媒介投放类")
    assert_equal(s4c, 40.0, "折扣60%→40分")

    s4d = _score_budget_health([], 1, "媒介投放类")
    assert_equal(s4d, 60.0, "无历史→60分（中性）")

    # ── 测试组 5: 在位者优势评分 ──
    print("\n📌 测试组 5: 在位者优势评分")

    assert_equal(_score_incumbent(False, 0, "无"), 100, "无在位者→100")
    assert_equal(_score_incumbent(True, 3, "高"), 0, "在位者×3→0")
    assert_equal(_score_incumbent(True, 2, "中"), 50, "在位者×2+合同到期→50")
    assert_equal(_score_incumbent(True, 2, "高"), 20, "在位者×2→20")
    assert_equal(_score_incumbent(True, 1, "无"), 70, "在位者×1→70")

    # ── 测试组 6: 客情关系评分 ──
    print("\n📌 测试组 6: 客情关系评分")

    relations = [
        {"purchaser_id": 1, "rating": "A"},
        {"purchaser_id": 1, "rating": "C"},  # 取最高A
        {"purchaser_id": 2, "rating": "S"},
    ]
    assert_equal(_score_client_relation(relations, 1), 80, "有A级→80")
    assert_equal(_score_client_relation(relations, 2), 100, "有S级→100")
    assert_equal(_score_client_relation(relations, 3), 0, "无记录→0")
    assert_equal(_score_client_relation([], 1), 0, "空列表→0")

    # ── 测试组 7: 综合评分 ──
    print("\n📌 测试组 7: 综合评分计算")

    # 场景A：最佳机会（公开招标 + HHI低 + 匹配赛道 + 无在位者 + S级客情）
    best_ann = {
        "purchaser_id": 1, "procurement_method": "公开招标",
        "project_category": "媒介投放类", "title": "最佳项目",
    }
    best_hist = [
        {"purchaser_id": 1, "project_category": "媒介投放类",
         "winner_name": f"公司{i}", "bid_amount": 100, "budget_amount": 100}
        for i in range(10)
    ]
    best_rel = [{"purchaser_id": 1, "rating": "S"}]
    best_inc = {"has_incumbent": False, "continuous_count": 0, "risk_level": "无"}

    best_score = calculate_opportunity_score(
        best_ann, best_hist,
        preferred_categories=["媒介投放类"],
        client_relations=best_rel,
        incumbent_result=best_inc,
    )
    # 预期: 100*0.2 + 100*0.2 + 100*0.2 + 100*0.15 + 100*0.15 + 100*0.10 = 100
    assert_between(best_score.total_score, 95, 100, "最佳场景 95-100分")
    assert_equal(best_score.probability_label, "低", "陪跑概率=低")

    # 场景B：最差机会（单一来源 + HHI高 + 不匹配 + 在位者×3 + 无客情）
    worst_ann = {
        "purchaser_id": 2, "procurement_method": "单一来源",
        "project_category": "创意设计类", "title": "最差项目",
    }
    worst_hist = [
        {"purchaser_id": 2, "project_category": "创意设计类",
         "winner_name": "垄断公司", "bid_amount": 1000, "budget_amount": 1000},
    ]
    worst_inc = {"has_incumbent": True, "continuous_count": 3, "risk_level": "高"}

    worst_score = calculate_opportunity_score(
        worst_ann, worst_hist,
        preferred_categories=["媒介投放类"],
        client_relations=[],
        incumbent_result=worst_inc,
    )
    # 预期: 0*0.2 + 20*0.2 + 50*0.2 + 60*0.15 + 0*0.15 + 0*0.10
    #      = 0 + 4 + 10 + 9 + 0 + 0 = 23
    assert_between(worst_score.total_score, 20, 30, "最差场景 20-30分")
    assert_equal(worst_score.probability_label, "高", "陪跑概率=高")

    # 场景C：中等机会
    mid_ann = {
        "purchaser_id": 1, "procurement_method": "公开询比",
        "project_category": "品牌策略类", "title": "中等项目",
    }
    mid_score = calculate_opportunity_score(
        mid_ann, best_hist,
        preferred_categories=["媒介投放类"],
        client_relations=[{"purchaser_id": 1, "rating": "B"}],
        incumbent_result={"has_incumbent": True, "continuous_count": 2, "risk_level": "高"},
    )
    # 预期: 80*0.2 + 100*0.2 + 50*0.2 + 70*0.15 + 20*0.15 + 60*0.10
    #      = 16 + 20 + 10 + 10.5 + 3 + 6 = 65.5
    assert_between(mid_score.total_score, 60, 70, "中等场景 60-70分")
    assert_equal(mid_score.probability_label, "中", "陪跑概率=中")

    # ── 测试组 8: 边界 ──
    print("\n📌 测试组 8: 边界情况")

    # 全空数据
    empty_score = calculate_opportunity_score(
        {"purchaser_id": 0, "procurement_method": "", "project_category": ""},
        [],
    )
    # 60*0.20 + 100*0.20(HHI=0→分散→100) + 60*0.20 + 60*0.15 + 100*0.15(无在位者→100) + 0*0.10 = 68
    assert_between(empty_score.total_score, 65, 72, "全空数据 65-72分")
    assert_equal(empty_score.probability_label, "中", "全空→中陪跑概率（乐观估计）")

    # 缺少 purchaser_id
    noid_score = calculate_opportunity_score(
        {"procurement_method": "公开招标", "project_category": "媒介投放类"},
        awards_dispersed,
    )
    assert_true(noid_score.total_score > 0, "缺ID仍有评分")

    # ── 测试组 9: 批量评分 ──
    print("\n📌 测试组 9: 批量评分")

    batch = [
        {"purchaser_id": 1, "procurement_method": "公开招标", "project_category": "媒介投放类", "title": "A"},
        {"purchaser_id": 1, "procurement_method": "单一来源", "project_category": "创意设计类", "title": "B"},
    ]
    batch_results = batch_score_opportunities(
        batch, awards_dispersed,
        preferred_categories=["媒介投放类"],
        client_relations=[{"purchaser_id": 1, "rating": "A"}],
    )
    assert_equal(len(batch_results), 2, "返回2条")
    assert_true(batch_results[0]["total_score"] > batch_results[1]["total_score"],
                "A分 > B分（公开招标优于单一来源）")

    # ── 结果汇总 ──
    print("\n" + "=" * 60)
    total_tests = passed + failed
    print(f"  测试结果: {passed}/{total_tests} 通过", end="")
    if failed > 0:
        print(f"  ❌ {failed} 个失败")
    else:
        print("  🎉 全部通过！")
    print("=" * 60)
