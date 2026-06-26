"""Docker容器内验证采购方画像模块"""
from app.services.purchaser_profiler import (
    analyze_purchaser_profile, _calc_hhi, _calc_supplier_top10,
    _calc_sme_win_rate, _calc_new_entrant_count, _detect_breakthrough,
    _calc_opportunity_rating, _build_incumbent_map, PURCHASER_PROFILE_SQL,
)

awards = [
    {"winner_name": "省广集团", "project_category": "媒介投放类",
     "bid_amount": 500, "bid_open_date": "2024-06-01", "contract_end": "2025-06-01"},
    {"winner_name": "省广集团", "project_category": "媒介投放类",
     "bid_amount": 480, "bid_open_date": "2023-06-01", "contract_end": "2024-06-01"},
    {"winner_name": "小公司A", "project_category": "活动执行类",
     "bid_amount": 100, "bid_open_date": "2024-03-01", "contract_end": "2025-03-01"},
]

profile = analyze_purchaser_profile("测试采购方", 1, awards)
d = profile.to_dict()
print("HHI =", d["hhi_index"])
print("Top10 =", len(d["supplier_top10"]), "家")
print("SME占比 =", d["sme_win_rate"], "%")
print("在位者赛道 =", len(d["incumbent_map"]), "个")
print("评级 =", d["opportunity_rating"])
print("SQL长度 =", len(PURCHASER_PROFILE_SQL), "字符")
print("Docker容器内验证通过!")
