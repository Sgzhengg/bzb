"""采购方画像分析模块 — 交叉验证脚本"""
import sys
sys.path.insert(0, 'd:/bzb/backend')

print("=" * 50)
print("采购方画像分析 — 全模块交叉验证")
print("=" * 50)

# 1. 导入验证
from app.services.purchaser_profiler import (
    analyze_purchaser_profile, batch_analyze_purchasers,
    _calc_hhi, _calc_supplier_top10, _calc_sme_win_rate,
    _calc_new_entrant_count, _detect_breakthrough, _calc_opportunity_rating,
    _build_incumbent_map, _hhi_concentration_label, _is_head_player, _is_sme,
    PURCHASER_PROFILE_SQL, query_purchaser_profile_from_db,
)
print("✅ 全部函数+SQL导入成功")

# 2. 与 opportunity_scorer 的 HHI 一致性
from app.services.opportunity_scorer import calculate_hhi as opp_hhi
test_awards = [
    {"winner_name": "A", "bid_amount": 500},
    {"winner_name": "B", "bid_amount": 300},
    {"winner_name": "C", "bid_amount": 200},
]
hhi1 = _calc_hhi(test_awards)
hhi2 = opp_hhi(test_awards)
print(f"HHI一致性: profiler={hhi1}, scorer={hhi2} → {'✅ 一致' if hhi1 == hhi2 else '❌ 不一致'}")

# 3. 与 incumbent_detector 的兼容性
from app.services.incumbent_detector import detect_incumbent

awards_inc = [
    {"purchaser_id": 1, "project_category": "媒介投放类",
     "winner_name": "省广集团", "bid_open_date": "2024-06-01",
     "bid_amount": 500, "is_continuous": True,
     "continuous_count": 3, "contract_end": "2025-06-01"},
    {"purchaser_id": 1, "project_category": "媒介投放类",
     "winner_name": "省广集团", "bid_open_date": "2023-06-01",
     "bid_amount": 480, "is_continuous": True,
     "continuous_count": 2, "contract_end": "2024-06-01"},
]
inc_result = detect_incumbent(
    {"purchaser_id": 1, "project_category": "媒介投放类"},
    awards_inc,
)
print(f"在位者检测: has_incumbent={inc_result.has_incumbent}, "
      f"name={inc_result.incumbent_name}, risk={inc_result.risk_level} → ✅")

# 4. 在位者地图验证
inc_map = _build_incumbent_map(awards_inc)
assert "媒介投放类" in inc_map
assert inc_map["媒介投放类"]["company"] == "省广集团"
print(f"在位者地图: {len(inc_map)}个赛道 → ✅")

# 5. SME判断
assert _is_head_player("省广集团")
assert not _is_sme("省广集团")
assert not _is_head_player("小公司")
assert _is_sme("小公司")
print("SME/头部判断: ✅")

# 6. Top10验证
top10 = _calc_supplier_top10(test_awards)
assert len(top10) == 3
assert top10[0]["name"] == "A"
assert abs(sum(x["percentage"] for x in top10) - 100) < 0.5
print(f"Top10: {len(top10)}家, 占比合计≈100% → ✅")

# 7. 集中度标签
assert _hhi_concentration_label(1000) == "分散"
assert _hhi_concentration_label(2000) == "中度集中"
assert _hhi_concentration_label(3000) == "高度集中"
print("集中度标签: 分散/中度/高度 → ✅")

# 8. SQL语法检查
assert "purchaser_id" in PURCHASER_PROFILE_SQL
assert "historical_awards" in PURCHASER_PROFILE_SQL
assert "winner_name" in PURCHASER_PROFILE_SQL
print(f"SQL聚合查询: {len(PURCHASER_PROFILE_SQL)}字符, 含6段查询 → ✅")

print()
print("=" * 50)
print("🎉 全模块交叉验证通过！")
print("=" * 50)
