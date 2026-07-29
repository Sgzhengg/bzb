"""聚焦银行广告：ccgp 快速扫描 (1类1页，不入库)"""
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.WARNING)  # 静默

from adapters.ccgp_adapter import CcgpAdapter

config = {"max_pages": 1, "min_delay": 2, "max_delay": 3, "max_retries": 2,
          "categories": ["gkzb"], "scope": "local"}
adapter = CcgpAdapter(config)

# 只做列表解析 + 关键词匹配，不抓详情
url = adapter._get_list_url("gkzb", 1, "local")
html = adapter._fetch_list_page(url)
items = adapter.parse_list(html, list_url=url)

print(f"ccgp 地方公开招标 第1页: {len(items)} 条\n")

# 按行业关键词分类
bank_kw = ["银行", "工行", "农行", "建行", "中行", "交行", "招商", "浦发", "中信", "光大", "民生", "兴业", "平安银行", "华夏", "广发"]
ad_kw = ["广告", "宣传", "品牌", "营销", "活动策划", "物料", "新媒体", "视频制作", "设计"]

bank_items = [i for i in items if any(k in i["title"] for k in bank_kw)]
bank_ad_items = [i for i in bank_items if any(k in i["title"] for k in ad_kw)]

print(f"  银行相关: {len(bank_items)} 条")
print(f"  银行+广告: {len(bank_ad_items)} 条")
print()

if bank_items:
    print("── 银行相关项目 ──")
    for i in bank_items[:10]:
        ad_flag = "🎯广告" if any(k in i["title"] for k in ad_kw) else "  "
        print(f"  {ad_flag} {i['title'][:80]}")

if not bank_ad_items and bank_items:
    print("\n💡 有银行项目但无广告类，需要其他来源（如银行自采平台）")
elif not bank_items:
    print("\n💡 ccgp 地方公开招标第1页无银行项目")
    print("   可能银行集中在中央采购或特定分类")
