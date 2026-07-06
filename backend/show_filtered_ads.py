"""用修复后的过滤逻辑，从旧版爬虫结果中提取真正的广东移动广告项目"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.zhaobiao_crawler import ZhaobiaoCrawler
from app.services.keyword_filter import filter_advertisement_projects

# 读取旧版爬虫结果
old_path = os.path.join(os.path.dirname(__file__), "output", "gd_mobile_tracks.json")
if os.path.exists(old_path):
    with open(old_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    old_items = data.get("items", [])
else:
    old_items = []

# 旧版爬虫标题列表（从终端输出提取）
old_titles = [
    ("品牌策略", "中国移动通信集团广东有限公司中山分公司2026年至2028年集团客户活动公开询比采购项目_询比公告"),
    ("品牌策略", "中国移动通信集团广东有限公司韶关分公司2026年至2028年集团合作伙伴智慧展示体验参观学习公开询比项目"),
    ("品牌策略", "中国移动广东公司2026年至2029年珠江新城珠江西路11号全球通大厦首层北区101单元公开招租项目"),
    ("品牌策略", "清远市公安局5G视频报警项目中标（成交）结果公告"),
    ("品牌策略", "中国移动通信集团广东有限公司2026年至2027年统一DCN基础维护支撑服务公开询比采购项目_中选候选人公示"),
    ("品牌策略", "中国移动通信集团广东有限公司2026年业务支撑系统前端服务优化定制软件研发公开询比采购项目_中选候选人公示"),
    ("品牌策略", "中国移动通信集团广东有限公司2026年智能体API接口防护工具公开询比采购项目_中选候选人公示"),
    ("品牌策略", "中国移动通信集团广东有限公司2026年至2028年数据中心工程（第一批）监理服务公开招标采购项目_中标候选人公示"),
]

# 另外还有之前爬取到的真正的广告项目（从ZhaobiaoCrawler搜索"中国移动通信集团广东 广告"得到的）
extra_real_ads = [
    "云浮分公司政企渠道宣传策划推广服务框架项目询比公告",
]

print("=" * 70)
print("🔍 用修复后过滤器重新判定旧版爬虫的全部采集结果")
print("=" * 70)

crawler = ZhaobiaoCrawler(max_pages=1)

all_titles = old_titles + [("广告类", t) for t in extra_real_ads]

ad_count = 0
non_ad_count = 0
ad_items = []

for cat, title in all_titles:
    is_ad_crawler = crawler._is_gd_mobile(title)
    filter_result = filter_advertisement_projects(title, "")
    is_ad_filter = filter_result.get("is_ad", False)
    
    status = "🟢 广告" if (is_ad_crawler or is_ad_filter) else "🔴 非广告"
    detail = ""
    if is_ad_filter:
        detail = f" → 赛道: {filter_result.get('category', '')}"
    elif not is_ad_crawler and not is_ad_filter:
        detail = " → 被 hard排除/无广告词"
    
    print(f"  {status} | [{cat}] {title[:90]}{detail}")
    
    if is_ad_crawler or is_ad_filter:
        ad_count += 1
        ad_items.append((cat, title, filter_result))
    else:
        non_ad_count += 1

print()
print(f"📊 判定结果: {ad_count} 条广告类 / {non_ad_count} 条非广告类")
print()

if ad_items:
    print("=" * 70)
    print("✅ 真正的广东移动广告类项目（修复后保留的）：")
    print("=" * 70)
    for i, (cat, title, fr) in enumerate(ad_items, 1):
        c = fr.get("category", cat)
        kws = fr.get("matched_keywords", [])
        kws_str = ", ".join(kws[:5]) if kws else ""
        print(f"  {i}. [{c}] {title[:90]}")
        if kws_str:
            print(f"     匹配词: {kws_str}")
        print()
else:
    print("⚠️ 未找到任何符合的广东移动广告类项目")
    print("   这可能说明7月份确实没有新的广告类招标公告")
