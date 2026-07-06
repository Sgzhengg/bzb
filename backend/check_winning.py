"""检查项目中标结果采集情况"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

output_dir = os.path.join(os.path.dirname(__file__), "output")

# 1. 检查现有采集结果
for fname in ["gd_mobile_tracks.json", "zhaobiao_winning.json", 
              "b2b_winning_results.json", "bidding_results.json", "zhaobiao_results.json"]:
    fpath = os.path.join(output_dir, fname)
    if not os.path.exists(fpath):
        print(f"[NOT FOUND] {fname}")
        continue

    with open(fpath, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except:
            print(f"[EMPTY] {fname}")
            continue

    print(f"\n=== {fname} ===")
    if isinstance(data, list):
        items = data
        print(f"  总条数: {len(items)}")
    elif isinstance(data, dict):
        items = data.get("items", [])
        print(f"  总条数: {data.get('total', len(items))}")

    # 分析公告类型
    if items:
        notice_types = {}
        for item in items:
            t = item.get("notice_type", "未知")
            notice_types[t] = notice_types.get(t, 0) + 1
        for t, c in sorted(notice_types.items(), key=lambda x: -x[1]):
            print(f"  - {t}: {c} 条")

        # 展示前5条
        print("\n  前5条:")
        for item in items[:5]:
            t = item.get("title", "") or item.get("project_name", "")
            nt = item.get("notice_type", "")
            d = item.get("publish_date", "") or item.get("bid_open_date", "")
            pur = item.get("purchaser", "") or item.get("winner_name", "")
            print(f"  [{nt}] {t[:90]}")
            if pur:
                print(f"    采购方/中标方: {pur}")
            if d:
                print(f"    日期: {d}")

# 2. 检查历史爬虫模块
print("\n=== 历史中标爬虫模块 (historical_crawler) ===")
hc_dir = os.path.join(os.path.dirname(__file__), "app", "services", "historical_crawler")
for f in sorted(os.listdir(hc_dir)):
    if f.endswith(".py") and not f.startswith("__"):
        print(f"  - {f}")
