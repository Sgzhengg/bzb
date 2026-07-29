"""全面扫描 ccgp: 中央+地方 × 全部分类，找银行广告"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logging
logging.basicConfig(level=logging.WARNING)

from adapters.ccgp_adapter import CcgpAdapter
adapter = CcgpAdapter({"max_pages": 1, "min_delay": 2, "max_delay": 3, "max_retries": 1,
                       "categories": ["gkzb","jzxcs","jzxtpgg","xjgg","dylygg"], "scope": "all"})

bank_kw = ["银行", "工行", "农行", "建行", "中行", "交行", "招商", "浦发", "中信", "光大", "民生", "兴业", "平安", "华夏", "广发"]
ad_kw = ["广告", "宣传", "品牌", "营销", "活动策划", "物料", "新媒体", "视频", "设计"]

total = 0
bank_total = 0
bank_ad_total = 0
bank_ad_items = []

for scope, scope_name in [("central","中央"), ("local","地方")]:
    for cat in ["gkzb","jzxcs","jzxtpgg","xjgg","dylygg"]:
        url = adapter._get_list_url(cat, 1, scope)
        html = adapter._fetch_list_page(url)
        if not html:
            continue
        items = adapter.parse_list(html, list_url=url)
        if not items:
            continue
        total += len(items)
        
        for item in items:
            title = item["title"]
            if any(k in title for k in bank_kw):
                bank_total += 1
                if any(k in title for k in ad_kw):
                    bank_ad_total += 1
                    bank_ad_items.append(title)

print(f"ccgp 扫描: {total} 条, 银行相关: {bank_total}, 银行广告: {bank_ad_total}")
print()

if bank_ad_items:
    print("🎯 银行广告招标:")
    for t in bank_ad_items:
        print(f"  {t[:90]}")
else:
    print("❌ ccgp 上没有银行广告类招标")
    print()
    print("原因：银行（工行/建行等）通常在自己的采购平台发布广告招标，")
    print("不在 ccgp.gov.cn 上。需要银行自有的采购平台适配器。")