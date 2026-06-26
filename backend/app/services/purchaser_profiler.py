"""
采购方画像分析模块

基于历史中标数据，生成各采购方的竞争格局分析报告。
包括：Top10供应商、HHI集中度、在位者地图、中小公司占比、
新进入者数量、破圈案例检测、机会评级。

支持两种数据源：
  1. Python 列表（适用于内存分析）
  2. PostgreSQL 数据库（适用于大规模数据）
"""

from typing import List, Dict, Optional, Tuple
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from dataclasses import dataclass, field


# ============================================================
# 常量定义
# ============================================================

# HHI 集中度标签
HHI_DISPERSED = "分散"
HHI_MODERATE = "中度集中"
HHI_HIGH = "高度集中"

# 中小公司关键词（复用 historical_crawler/cleaner.py 的逻辑）
HEAD_PLAYER_KEYWORDS = [
    "省广", "因赛", "华扬联众", "蓝色光标", "电通", "奥美",
    "阳狮", "群邑", "宏盟", "广东省广告", "GIMC", "引力传媒",
    "天下秀", "浙文互联", "三人行", "思美传媒", "华媒控股",
    "中广", "凤凰", "分众", "新潮", "兆讯",
]

# 近2年天数
TWO_YEARS_DAYS = 730


# ============================================================
# 输出数据结构
# ============================================================

@dataclass
class SupplierStat:
    """供应商统计"""
    name: str
    win_count: int
    percentage: float  # 该采购方总中标次数的占比


@dataclass
class IncumbentInfo:
    """在位者信息"""
    company: str
    contract_end: Optional[str]


@dataclass
class PurchaserProfile:
    """采购方画像"""
    purchaser_name: str
    purchaser_id: int
    supplier_top10: List[Dict]
    hhi_index: float
    concentration_level: str
    incumbent_map: Dict[str, Dict]       # {category: {company, contract_end}}
    sme_win_rate: float                  # 中小公司中标占比（%）
    new_entrant_count: int               # 近2年新进入者数量
    has_breakthrough_case: bool          # 是否存在破圈案例
    opportunity_rating: str              # ★ ~ ★★★★★

    def to_dict(self) -> Dict:
        return {
            "purchaser_name": self.purchaser_name,
            "purchaser_id": self.purchaser_id,
            "supplier_top10": self.supplier_top10,
            "hhi_index": self.hhi_index,
            "concentration_level": self.concentration_level,
            "incumbent_map": self.incumbent_map,
            "sme_win_rate": self.sme_win_rate,
            "new_entrant_count": self.new_entrant_count,
            "has_breakthrough_case": self.has_breakthrough_case,
            "opportunity_rating": self.opportunity_rating,
        }


# ============================================================
# 辅助判断函数
# ============================================================

def _is_head_player(company_name: str) -> bool:
    """判断是否为头部公司。"""
    if not company_name:
        return False
    for kw in HEAD_PLAYER_KEYWORDS:
        if kw in company_name:
            return True
    return False


def _is_sme(company_name: str) -> bool:
    """判断是否为中小公司（非头部 = 中小）。"""
    return not _is_head_player(company_name)


def _hhi_concentration_label(hhi: float) -> str:
    """HHI → 集中度标签。"""
    if hhi < 1500:
        return HHI_DISPERSED
    elif hhi < 2500:
        return HHI_MODERATE
    else:
        return HHI_HIGH


def _parse_date_safe(date_str: Optional[str]) -> Optional[date]:
    """安全解析日期。"""
    if not date_str:
        return None
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]:
        try:
            return datetime.strptime(str(date_str)[:10], fmt).date()
        except (ValueError, IndexError):
            continue
    return None


# ============================================================
# 聚合计算函数
# ============================================================

def _calc_supplier_top10(awards: List[Dict]) -> List[Dict]:
    """
    计算 Top10 供应商（按中标次数降序）。

    Returns:
        [{"name": "...", "win_count": N, "percentage": P}, ...]
    """
    counter = Counter()
    for a in awards:
        winner = (a.get("winner_name") or "").strip()
        if winner:
            counter[winner] += 1

    total = sum(counter.values())
    if total == 0:
        return []

    top10 = counter.most_common(10)
    return [
        {
            "name": name,
            "win_count": count,
            "percentage": round(count / total * 100, 1),
        }
        for name, count in top10
    ]


def _calc_hhi(awards: List[Dict]) -> float:
    """
    计算 HHI 指数（基于中标金额）。

    HHI = Σ(每个供应商金额占比² × 10000)
    """
    if not awards:
        return 0.0

    supplier_amounts: Dict[str, float] = {}
    for award in awards:
        winner = (award.get("winner_name") or "").strip()
        if not winner:
            continue
        amount = award.get("bid_amount") or 0
        supplier_amounts[winner] = supplier_amounts.get(winner, 0) + float(amount)

    total = sum(supplier_amounts.values())
    if total <= 0:
        return 0.0

    hhi = 0.0
    for amount in supplier_amounts.values():
        share = amount / total
        hhi += share * share * 10000

    return round(hhi, 1)


def _build_incumbent_map(awards: List[Dict]) -> Dict[str, Dict]:
    """
    构建在位者地图：每个赛道最近一次中标的供应商。

    Returns:
        {
            "品牌策略类": {"company": "省广集团", "contract_end": "2025-06-01"},
            "媒介投放类": {"company": "蓝色光标", "contract_end": "2025-03-01"},
            ...
        }
    """
    # 按赛道分组，取每组最近开标日期的中标方
    category_latest: Dict[str, Dict] = {}

    for a in awards:
        cat = (a.get("project_category") or "").strip()
        winner = (a.get("winner_name") or "").strip()
        if not cat or not winner:
            continue

        bid_date_str = a.get("bid_open_date") or ""
        bid_date = _parse_date_safe(bid_date_str)
        contract_end = a.get("contract_end") or None

        if cat not in category_latest:
            category_latest[cat] = {
                "company": winner,
                "contract_end": contract_end,
                "bid_date": bid_date,
            }
        else:
            existing_date = category_latest[cat].get("bid_date")
            if bid_date and (not existing_date or bid_date > existing_date):
                category_latest[cat] = {
                    "company": winner,
                    "contract_end": contract_end,
                    "bid_date": bid_date,
                }

    # 清理内部 bid_date 字段
    result = {}
    for cat, info in category_latest.items():
        result[cat] = {
            "company": info["company"],
            "contract_end": info["contract_end"],
        }
    return result


def _calc_sme_win_rate(awards: List[Dict]) -> float:
    """计算中小公司中标占比（%）。"""
    if not awards:
        return 0.0
    sme_count = sum(1 for a in awards if _is_sme(a.get("winner_name", "")))
    return round(sme_count / len(awards) * 100, 1)


def _calc_new_entrant_count(awards: List[Dict], reference_date: Optional[date] = None) -> int:
    """
    计算近2年新进入者数量。

    "新进入者" = 首次出现在该采购方中标记录中的公司，
    且首次中标时间在近2年内。
    """
    if not awards:
        return 0

    today = reference_date or date.today()
    cutoff = today - timedelta(days=TWO_YEARS_DAYS)

    # 按公司分组，取每家公司的最早中标日期
    company_first_win: Dict[str, date] = {}
    for a in awards:
        winner = (a.get("winner_name") or "").strip()
        if not winner:
            continue
        bid_date = _parse_date_safe(a.get("bid_open_date"))
        if not bid_date:
            continue
        if winner not in company_first_win or bid_date < company_first_win[winner]:
            company_first_win[winner] = bid_date

    # 统计近2年内首次出现的公司
    new_count = sum(
        1 for d in company_first_win.values()
        if d >= cutoff
    )
    return new_count


def _detect_breakthrough(awards: List[Dict]) -> bool:
    """
    检测是否存在"破圈案例"。

    破圈定义：在某个赛道中，非头部公司（中小/新进入者）
    打破了头部公司的垄断，成功中标。

    判定逻辑：按赛道分组，若该赛道的最近一次中标方为中小公司，
    且该赛道之前有头部公司中标过 → 破圈。
    """
    if not awards:
        return False

    # 按赛道分组
    by_category: Dict[str, List[Dict]] = defaultdict(list)
    for a in awards:
        cat = (a.get("project_category") or "").strip()
        if cat:
            by_category[cat].append(a)

    for cat, cat_awards in by_category.items():
        # 按开标日期排序
        sorted_awards = sorted(
            cat_awards,
            key=lambda x: _parse_date_safe(x.get("bid_open_date")) or date.min,
        )

        if len(sorted_awards) < 2:
            continue

        # 最近一次
        latest_winner = (sorted_awards[-1].get("winner_name") or "").strip()

        # 之前是否有头部公司
        has_head_before = any(
            _is_head_player(a.get("winner_name", ""))
            for a in sorted_awards[:-1]
        )

        # 最近一次是中小公司，且之前有头部 → 破圈
        if _is_sme(latest_winner) and has_head_before:
            return True

    return False


# ============================================================
# 机会评级
# ============================================================

def _calc_opportunity_rating(
    sme_win_rate: float,
    has_breakthrough: bool,
    hhi: float,
) -> str:
    """
    计算机会评级（针对中小公司视角）。

    规则：
    - sme_win_rate ≥ 25% 且 has_breakthrough → ★★★★★
    - sme_win_rate ≥ 15% → ★★★★
    - hhi < 2000 → ★★★
    - 其余 → ★★
    """
    if sme_win_rate >= 25 and has_breakthrough:
        return "★★★★★"
    elif sme_win_rate >= 15:
        return "★★★★"
    elif hhi < 2000:
        return "★★★"
    else:
        return "★★"


# ============================================================
# 主分析函数
# ============================================================

def analyze_purchaser_profile(
    purchaser_name: str,
    purchaser_id: int,
    awards: List[Dict],
) -> PurchaserProfile:
    """
    分析单个采购方的竞争格局，生成画像报告。

    Args:
        purchaser_name: 采购方名称（如 "东莞分公司"）
        purchaser_id: 采购方ID
        awards: 该采购方的所有历史中标记录（可跨赛道）

    Returns:
        PurchaserProfile 画像报告

    Examples:
        >>> awards = [
        ...     {"winner_name":"省广","project_category":"媒介投放类",
        ...      "bid_amount":500,"bid_open_date":"2024-06-01",
        ...      "contract_end":"2025-06-01"},
        ...     {"winner_name":"小公司A","project_category":"活动执行类",
        ...      "bid_amount":100,"bid_open_date":"2024-03-01",
        ...      "contract_end":"2025-03-01"},
        ... ]
        >>> profile = analyze_purchaser_profile("测试", 1, awards)
        >>> profile.hhi_index > 0
        True
    """
    if not awards:
        return PurchaserProfile(
            purchaser_name=purchaser_name,
            purchaser_id=purchaser_id,
            supplier_top10=[],
            hhi_index=0.0,
            concentration_level=HHI_DISPERSED,
            incumbent_map={},
            sme_win_rate=0.0,
            new_entrant_count=0,
            has_breakthrough_case=False,
            opportunity_rating="★★",
        )

    # ── 各维度计算 ──
    top10 = _calc_supplier_top10(awards)
    hhi = _calc_hhi(awards)
    concentration = _hhi_concentration_label(hhi)
    inc_map = _build_incumbent_map(awards)
    sme_rate = _calc_sme_win_rate(awards)
    new_count = _calc_new_entrant_count(awards)
    breakthrough = _detect_breakthrough(awards)
    rating = _calc_opportunity_rating(sme_rate, breakthrough, hhi)

    return PurchaserProfile(
        purchaser_name=purchaser_name,
        purchaser_id=purchaser_id,
        supplier_top10=top10,
        hhi_index=hhi,
        concentration_level=concentration,
        incumbent_map=inc_map,
        sme_win_rate=sme_rate,
        new_entrant_count=new_count,
        has_breakthrough_case=breakthrough,
        opportunity_rating=rating,
    )


# ============================================================
# 批量分析
# ============================================================

def batch_analyze_purchasers(
    purchasers: List[Dict],
    all_awards: List[Dict],
) -> List[Dict]:
    """
    批量分析多个采购方。

    Args:
        purchasers: [{"id": 1, "name": "省公司"}, ...]
        all_awards: 全部历史中标记录

    Returns:
        各采购方的画像报告列表（按机会评级降序）
    """
    profiles = []
    for p in purchasers:
        pid = p.get("id", 0)
        pname = p.get("name", str(pid))
        # 筛选该采购方的记录
        p_awards = [a for a in all_awards if a.get("purchaser_id") == pid]
        profile = analyze_purchaser_profile(pname, pid, p_awards)
        profiles.append(profile.to_dict())

    # 按机会评级排序（星越多越靠前）
    profiles.sort(key=lambda x: len(x["opportunity_rating"]), reverse=True)
    return profiles


# ============================================================
# SQL 聚合查询（PostgreSQL）
# ============================================================

PURCHASER_PROFILE_SQL = """
-- ============================================================
-- 采购方画像分析 — PostgreSQL 聚合查询
-- ============================================================

-- 1. 供应商 Top10（按中标次数）
SELECT
    p.name AS purchaser_name,
    ha.winner_name,
    COUNT(*) AS win_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (
        PARTITION BY ha.purchaser_id
    ), 1) AS percentage
FROM historical_awards ha
JOIN purchasers p ON p.id = ha.purchaser_id
WHERE ha.purchaser_id = %(purchaser_id)s
  AND ha.winner_name IS NOT NULL
  AND ha.winner_name != ''
GROUP BY p.name, ha.purchaser_id, ha.winner_name
ORDER BY win_count DESC
LIMIT 10;


-- 2. HHI 指数（按中标金额）
SELECT
    ROUND(SUM((share * 100) ^ 2)::numeric, 1) AS hhi_index
FROM (
    SELECT
        winner_name,
        SUM(bid_amount) / SUM(SUM(bid_amount)) OVER () AS share
    FROM historical_awards
    WHERE purchaser_id = %(purchaser_id)s
      AND bid_amount IS NOT NULL
      AND bid_amount > 0
    GROUP BY winner_name
) sub;


-- 3. 在位者地图（每赛道最近中标方）
SELECT DISTINCT ON (project_category)
    project_category,
    winner_name AS company,
    contract_end
FROM historical_awards
WHERE purchaser_id = %(purchaser_id)s
  AND project_category IS NOT NULL
  AND project_category != ''
  AND winner_name IS NOT NULL
ORDER BY project_category, bid_open_date DESC;


-- 4. 中小公司中标占比
SELECT
    ROUND(
        COUNT(*) FILTER (
            WHERE winner_name !~ '省广|因赛|华扬联众|蓝色光标|电通|奥美|阳狮|群邑|宏盟'
        ) * 100.0 / COUNT(*),
        1
    ) AS sme_win_rate
FROM historical_awards
WHERE purchaser_id = %(purchaser_id)s
  AND winner_name IS NOT NULL
  AND winner_name != '';


-- 5. 近2年新进入者数量
WITH first_wins AS (
    SELECT
        winner_name,
        MIN(bid_open_date) AS first_win_date
    FROM historical_awards
    WHERE purchaser_id = %(purchaser_id)s
      AND winner_name IS NOT NULL
    GROUP BY winner_name
)
SELECT COUNT(*) AS new_entrant_count
FROM first_wins
WHERE first_win_date >= CURRENT_DATE - INTERVAL '2 years';


-- 6. 破圈案例检测
-- 条件：某赛道在近2年内有中小公司中标，且该赛道曾有头部公司中标
WITH category_winners AS (
    SELECT
        project_category,
        winner_name,
        bid_open_date,
        ROW_NUMBER() OVER (
            PARTITION BY project_category ORDER BY bid_open_date DESC
        ) AS rn
    FROM historical_awards
    WHERE purchaser_id = %(purchaser_id)s
),
head_categories AS (
    SELECT DISTINCT project_category
    FROM historical_awards
    WHERE purchaser_id = %(purchaser_id)s
      AND winner_name ~ '省广|因赛|华扬联众|蓝色光标|电通|奥美|阳狮|群邑|宏盟'
),
sme_recent AS (
    SELECT project_category
    FROM category_winners
    WHERE rn = 1
      AND winner_name !~ '省广|因赛|华扬联众|蓝色光标|电通|奥美|阳狮|群邑|宏盟'
)
SELECT
    CASE WHEN COUNT(*) > 0 THEN TRUE ELSE FALSE END AS has_breakthrough
FROM sme_recent s
INNER JOIN head_categories h ON s.project_category = h.project_category;
"""


# ============================================================
# 数据库查询封装
# ============================================================

async def query_purchaser_profile_from_db(
    purchaser_id: int,
    db_session,  # AsyncSession
) -> Optional[Dict]:
    """
    从 PostgreSQL 数据库查询采购方画像数据。

    Args:
        purchaser_id: 采购方ID
        db_session: SQLAlchemy AsyncSession

    Returns:
        画像数据字典，或 None
    """
    from sqlalchemy import text

    # 查询采购方名称
    name_result = await db_session.execute(
        text("SELECT name FROM purchasers WHERE id = :pid"),
        {"pid": purchaser_id},
    )
    name_row = name_result.fetchone()
    if not name_row:
        return None
    purchaser_name = name_row[0]

    # 查询各项指标
    async def _query_single(sql_key: str, params: dict):
        result = await db_session.execute(text(sql_key), params)
        row = result.fetchone()
        return row

    # Top10
    top10_rows = await db_session.execute(
        text("""
            SELECT winner_name, COUNT(*) AS cnt,
                   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
            FROM historical_awards
            WHERE purchaser_id = :pid AND winner_name != ''
            GROUP BY winner_name ORDER BY cnt DESC LIMIT 10
        """),
        {"pid": purchaser_id},
    )
    supplier_top10 = [
        {"name": r[0], "win_count": r[1], "percentage": float(r[2])}
        for r in top10_rows.fetchall()
    ]

    # HHI
    hhi_row = await db_session.execute(
        text("""
            SELECT ROUND(SUM((share * 100)^2)::numeric, 1)
            FROM (
                SELECT winner_name,
                       SUM(COALESCE(bid_amount,0)) /
                       SUM(SUM(COALESCE(bid_amount,0))) OVER () AS share
                FROM historical_awards
                WHERE purchaser_id = :pid AND bid_amount > 0
                GROUP BY winner_name
            ) sub
        """),
        {"pid": purchaser_id},
    )
    hhi_val = float(hhi_row.fetchone()[0] or 0)

    # 在位者地图
    inc_rows = await db_session.execute(
        text("""
            SELECT DISTINCT ON (project_category)
                   project_category, winner_name, contract_end
            FROM historical_awards
            WHERE purchaser_id = :pid AND project_category != ''
                  AND winner_name != ''
            ORDER BY project_category, bid_open_date DESC
        """),
        {"pid": purchaser_id},
    )
    incumbent_map = {}
    for r in inc_rows.fetchall():
        incumbent_map[r[0]] = {
            "company": r[1],
            "contract_end": r[2].isoformat() if r[2] else None,
        }

    # SME 占比
    sme_row = await db_session.execute(
        text("""
            SELECT ROUND(
                COUNT(*) FILTER (
                    WHERE winner_name !~ '省广|因赛|华扬联众|蓝色光标|电通|奥美|阳狮|群邑|宏盟'
                ) * 100.0 / NULLIF(COUNT(*), 0), 1
            )
            FROM historical_awards
            WHERE purchaser_id = :pid AND winner_name != ''
        """),
        {"pid": purchaser_id},
    )
    sme_rate = float(sme_row.fetchone()[0] or 0)

    # 新进入者
    new_row = await db_session.execute(
        text("""
            WITH first_wins AS (
                SELECT winner_name, MIN(bid_open_date) AS first_date
                FROM historical_awards
                WHERE purchaser_id = :pid AND winner_name != ''
                GROUP BY winner_name
            )
            SELECT COUNT(*) FROM first_wins
            WHERE first_date >= CURRENT_DATE - INTERVAL '2 years'
        """),
        {"pid": purchaser_id},
    )
    new_count = new_row.fetchone()[0]

    # 破圈
    bt_row = await db_session.execute(
        text("""
            WITH recent AS (
                SELECT DISTINCT ON (project_category) project_category, winner_name
                FROM historical_awards
                WHERE purchaser_id = :pid AND project_category != ''
                ORDER BY project_category, bid_open_date DESC
            ),
            head_cats AS (
                SELECT DISTINCT project_category FROM historical_awards
                WHERE purchaser_id = :pid
                  AND winner_name ~ '省广|因赛|华扬联众|蓝色光标|电通|奥美|阳狮|群邑|宏盟'
            )
            SELECT COUNT(*) > 0 FROM recent r
            JOIN head_cats h ON r.project_category = h.project_category
            WHERE r.winner_name !~ '省广|因赛|华扬联众|蓝色光标|电通|奥美|阳狮|群邑|宏盟'
        """),
        {"pid": purchaser_id},
    )
    has_breakthrough = bt_row.fetchone()[0]

    # 机会评级
    rating = _calc_opportunity_rating(sme_rate, has_breakthrough, hhi_val)

    return {
        "purchaser_name": purchaser_name,
        "purchaser_id": purchaser_id,
        "supplier_top10": supplier_top10,
        "hhi_index": hhi_val,
        "concentration_level": _hhi_concentration_label(hhi_val),
        "incumbent_map": incumbent_map,
        "sme_win_rate": sme_rate,
        "new_entrant_count": new_count,
        "has_breakthrough_case": has_breakthrough,
        "opportunity_rating": rating,
    }


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

    def assert_approx(actual, expected, tolerance, name):
        global passed, failed
        if abs(actual - expected) <= tolerance:
            passed += 1
            print(f"  ✅ {name} ({actual})")
        else:
            failed += 1
            print(f"  ❌ {name}: {actual} vs {expected}±{tolerance}")

    print("=" * 60)
    print("采购方画像分析 — 单元测试")
    print("=" * 60)

    # 构造测试数据
    test_awards = [
        # 头部公司多次中标（媒介投放）
        {"winner_name": "省广集团", "project_category": "媒介投放类",
         "bid_amount": 500, "bid_open_date": "2024-06-01",
         "contract_end": "2025-06-01"},
        {"winner_name": "省广集团", "project_category": "媒介投放类",
         "bid_amount": 480, "bid_open_date": "2023-06-01",
         "contract_end": "2024-06-01"},
        {"winner_name": "省广集团", "project_category": "媒介投放类",
         "bid_amount": 450, "bid_open_date": "2022-06-01",
         "contract_end": "2023-06-01"},
        # 蓝色光标（活动执行）
        {"winner_name": "蓝色光标", "project_category": "活动执行类",
         "bid_amount": 300, "bid_open_date": "2024-05-01",
         "contract_end": "2025-05-01"},
        {"winner_name": "蓝色光标", "project_category": "活动执行类",
         "bid_amount": 280, "bid_open_date": "2023-05-01",
         "contract_end": "2024-05-01"},
        # 中小公司（新媒体运营）—— 破圈案例！
        {"winner_name": "东莞东艺文化传播有限公司", "project_category": "新媒体运营类",
         "bid_amount": 80, "bid_open_date": "2024-08-01",
         "contract_end": "2025-08-01"},
        {"winner_name": "蓝色光标", "project_category": "新媒体运营类",
         "bid_amount": 100, "bid_open_date": "2023-08-01",
         "contract_end": "2024-08-01"},
        # 中小公司（设计）
        {"winner_name": "广州创意设计工作室", "project_category": "创意设计类",
         "bid_amount": 50, "bid_open_date": "2024-03-01",
         "contract_end": "2025-03-01"},
        # 新进入者（近2年首次出现）
        {"winner_name": "新兴广告公司", "project_category": "品牌策略类",
         "bid_amount": 120, "bid_open_date": "2024-09-01",
         "contract_end": "2025-09-01"},
    ]

    # ── 测试组 1: Top10 供应商 ──
    print("\n📌 测试组 1: 供应商 Top10")

    top10 = _calc_supplier_top10(test_awards)
    assert_equal(len(top10), 5, "5家不同供应商")
    assert_equal(top10[0]["name"], "省广集团", "Top1=省广集团")
    assert_equal(top10[0]["win_count"], 3, "省广中标3次")
    assert_approx(top10[0]["percentage"], 33.3, 0.5, "省广占比≈33.3%")
    # 验证百分比之和=100
    total_pct = sum(item["percentage"] for item in top10)
    assert_approx(total_pct, 100.0, 1.0, "百分比之和≈100%")

    # ── 测试组 2: HHI ──
    print("\n📌 测试组 2: HHI 指数")

    hhi = _calc_hhi(test_awards)
    # 省广: 500+480+450=1430, 蓝标: 300+280+100=680, 东艺:80, 创意工作室:50, 新兴:120
    # total = 1430+680+80+50+120 = 2360
    # shares: 省广=0.6059, 蓝标=0.2881, 东艺=0.0339, 创意=0.0212, 新兴=0.0508
    # HHI ≈ (0.6059²+0.2881²+0.0339²+0.0212²+0.0508²)*10000 ≈ (0.3671+0.0830+0.0011+0.0004+0.0026)*10000 ≈ 4543
    assert_true(hhi > 4000, f"HHI>4000（实际{hhi}）")

    # ── 测试组 3: 在位者地图 ──
    print("\n📌 测试组 3: 在位者地图")

    inc_map = _build_incumbent_map(test_awards)
    assert_equal(len(inc_map), 5, "5个赛道")
    assert_equal(inc_map["媒介投放类"]["company"], "省广集团", "媒介投放→省广")
    assert_equal(inc_map["活动执行类"]["company"], "蓝色光标", "活动执行→蓝色光标")
    assert_equal(inc_map["新媒体运营类"]["company"], "东莞东艺文化传播有限公司", "新媒体→东艺（破圈）")
    assert_equal(inc_map["媒介投放类"]["contract_end"], "2025-06-01", "合同到期日")

    # ── 测试组 4: SME 占比 ──
    print("\n📌 测试组 4: 中小公司占比")

    sme_rate = _calc_sme_win_rate(test_awards)
    # 9条记录: 省广×3(头) + 蓝标×3(头) + 东艺(中) + 创意(中) + 新兴(中) = 3家中小
    assert_approx(sme_rate, 33.3, 1.0, f"SME占比≈33.3%（实际{sme_rate}）")

    # ── 测试组 5: 新进入者 ──
    print("\n📌 测试组 5: 新进入者数量")

    new_count = _calc_new_entrant_count(test_awards, reference_date=date(2024, 10, 1))
    # 省广最早2022-06(超2年) 以外，蓝标/东艺/创意工作室/新兴 都在近2年内首次出现
    assert_equal(new_count, 4, "4个新进入者（蓝标+东艺+创意+新兴）")

    # ── 测试组 6: 破圈案例 ──
    print("\n📌 测试组 6: 破圈案例检测")

    breakthrough = _detect_breakthrough(test_awards)
    # 新媒体运营类：之前蓝标(头)→最近东艺(中) → 破圈
    assert_true(breakthrough, "存在破圈案例（新媒体运营）")

    # 无破圈的数据
    no_bt_awards = [
        {"winner_name": "省广集团", "project_category": "媒介投放类",
         "bid_amount": 500, "bid_open_date": "2024-06-01"},
        {"winner_name": "省广集团", "project_category": "媒介投放类",
         "bid_amount": 480, "bid_open_date": "2023-06-01"},
    ]
    assert_true(not _detect_breakthrough(no_bt_awards), "无破圈（头部持续垄断）")

    # ── 测试组 7: 机会评级 ──
    print("\n📌 测试组 7: 机会评级")

    assert_equal(_calc_opportunity_rating(30, True, 5000), "★★★★★", "SME≥25+破圈→5星")
    assert_equal(_calc_opportunity_rating(20, False, 5000), "★★★★", "SME≥15→4星")
    assert_equal(_calc_opportunity_rating(10, False, 1500), "★★★", "HHI<2000→3星")
    assert_equal(_calc_opportunity_rating(5, False, 3000), "★★", "其余→2星")

    # ── 测试组 8: 完整画像 ──
    print("\n📌 测试组 8: 完整画像报告")

    profile = analyze_purchaser_profile("东莞分公司", 1, test_awards)
    d = profile.to_dict()

    assert_equal(d["purchaser_name"], "东莞分公司", "采购方名称")
    assert_equal(len(d["supplier_top10"]), 5, "Top10=5家")
    assert_true(d["hhi_index"] > 0, "HHI>0")
    assert_true(d["concentration_level"] in ("分散", "中度集中", "高度集中"), "集中度标签有效")
    assert_equal(len(d["incumbent_map"]), 5, "在位者地图5赛道")
    assert_true(d["sme_win_rate"] > 0, "SME占比>0")
    # today=2026-06-26, 近2年首次出现: 东艺(2024-08)+新兴(2024-09)=2
    assert_equal(d["new_entrant_count"], 2, "新进入者=2（东艺+新兴）")
    assert_true(d["has_breakthrough_case"], "有破圈")
    # sme_rate≈33.3% ≥25 + breakthrough → 5星
    assert_equal(d["opportunity_rating"], "★★★★★", "机会评级=5星")

    # ── 测试组 9: 边界 ──
    print("\n📌 测试组 9: 边界情况")

    empty_profile = analyze_purchaser_profile("空采购方", 999, [])
    ed = empty_profile.to_dict()
    assert_equal(ed["supplier_top10"], [], "空数据Top10=[]")
    assert_equal(ed["hhi_index"], 0.0, "空数据HHI=0")
    assert_equal(ed["incumbent_map"], {}, "空数据在位者={}")
    assert_equal(ed["sme_win_rate"], 0.0, "空数据SME=0")
    assert_equal(ed["new_entrant_count"], 0, "空数据新进入者=0")
    assert_equal(ed["has_breakthrough_case"], False, "空数据无破圈")
    assert_equal(ed["opportunity_rating"], "★★", "空数据=2星")

    # 仅1条记录
    single = analyze_purchaser_profile("单条", 1, [test_awards[0]])
    assert_equal(len(single.supplier_top10), 1, "单条Top10=1")

    # ── 结果汇总 ──
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"  测试结果: {passed}/{total} 通过", end="")
    if failed > 0:
        print(f"  ❌ {failed} 个失败")
    else:
        print("  🎉 全部通过！")
    print("=" * 60)
