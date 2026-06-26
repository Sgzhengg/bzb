"""
中国招标网 (zhaobiao.cn) 适配器 — 单元测试
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.zhaobiao_adapter import ZhaobiaoAdapter

# ============================================================
# Mock HTML 数据
# ============================================================

MOCK_LIST_HTML = """
<!DOCTYPE html>
<html>
<head><title>搜索结果 - 中国招标网</title></head>
<body>
<div class="search-result-list">
  <div class="result-item">
    <h3><a href="/detail/20240615001.html">广东移动2024年度品牌广告投放服务项目招标公告</a></h3>
    <span class="date">2024-06-15</span>
    <span class="region">广东</span>
  </div>
  <div class="result-item">
    <h3><a href="/detail/20240614002.html">中国移动广东公司东莞分公司宣传活动物料制作项目中标结果公示</a></h3>
    <span class="date">2024-06-14</span>
    <span class="region">广东东莞</span>
  </div>
  <div class="result-item">
    <h3><a href="/detail/20240613003.html">广东移动5G基站机房建设施工项目招标公告</a></h3>
    <span class="date">2024-06-13</span>
    <span class="region">广东</span>
  </div>
  <div class="result-item">
    <h3><a href="/detail/20240612004.html">某市水务局管道工程项目</a></h3>
    <span class="date">2024-06-12</span>
    <span class="region">广东深圳</span>
  </div>
</div>
<div class="pagination">
  <a href="?page=2">下一页</a>
</div>
</body>
</html>
"""

MOCK_DETAIL_HTML = """
<!DOCTYPE html>
<html>
<head><title>广东移动2024年度品牌广告投放服务项目招标公告 - 中国招标网</title></head>
<body>
<div class="detail-content">
  <h1>广东移动2024年度品牌广告投放服务项目招标公告</h1>
  <div class="info-bar">
    <span>项目编号：GDYD202406001</span>
    <span>发布时间：2024-06-15</span>
  </div>
  <div class="project-info">
    <p>采购人：中国移动通信集团广东有限公司</p>
    <p>采购方式：公开招标</p>
    <p>采购预算：500万元</p>
    <p>投标截止时间：2024年07月20日 17:00:00</p>
    <p>开标时间：2024年07月21日 10:00:00</p>
  </div>
  <div class="qualification">
    <h3>投标人资格要求</h3>
    <p>1. 具有独立法人资格，注册资金不低于1000万元。</p>
    <p>2. 近三年具有同类广告投放项目经验，需提供合同证明。</p>
    <p>3. 具有抖音、快手等平台广告投放代理资质。</p>
  </div>
  <div class="score-section">
    <h3>评分办法</h3>
    <p>本项目采用综合评分法：技术分占40%，商务分占30%，价格分占30%。</p>
  </div>
  <div class="contact">
    <p>联系人：张经理</p>
    <p>联系电话：020-12345678</p>
  </div>
  <a href="/upload/zbwj_20240615.pdf">招标文件.pdf</a>
</div>
</body>
</html>
"""

MOCK_DETAIL2_HTML = """
<!DOCTYPE html>
<html>
<head><title>中国移动广东公司东莞分公司宣传活动物料制作项目中标结果 - 中国招标网</title></head>
<body>
<div class="detail-content">
  <h1>中国移动广东公司东莞分公司宣传活动物料制作项目中标结果公示</h1>
  <div class="info-bar">
    <span>项目编号：DG-2024-ZH-005</span>
    <span>发布时间：2024-06-14</span>
  </div>
  <div class="project-info">
    <p>采购人：中国移动通信集团广东有限公司东莞分公司</p>
    <p>中标人：东莞市东艺文化传播有限公司</p>
    <p>中标金额：128.5万元</p>
    <p>采购预算：150万元</p>
  </div>
</div>
</body>
</html>
"""


# ============================================================
# 测试
# ============================================================

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


def run_tests():
    global passed, failed
    passed = 0
    failed = 0

    print("=" * 60)
    print("中国招标网 (zhaobiao.cn) 适配器 — 单元测试")
    print("=" * 60)

    adapter = ZhaobiaoAdapter({"max_pages": 1, "min_delay": 0, "max_delay": 0})

    # ── 测试组 1: 列表解析 ──
    print("\n📌 测试组 1: 列表页解析")

    items = adapter.parse_list(MOCK_LIST_HTML)
    assert_equal(len(items), 3, "解析出3条广东移动项目（过滤非移动）")
    assert_true("品牌广告投放" in items[0]["title"], "第1条标题正确")
    assert_equal(items[0]["publish_date"], "2024-06-15", "日期提取")
    assert_true("/detail/20240615001" in items[0]["detail_url"], "URL拼接")
    assert_equal(items[0]["notice_type"], "招标公告", "类型=招标公告")
    assert_equal(items[1]["notice_type"], "中标公告", "第2条=中标公告")
    assert_equal(items[1]["region"], "广东东莞", "地区=广东东莞")

    # 非广东移动项目被过滤
    titles = [i["title"] for i in items]
    assert_true("水务局" not in str(titles), "非移动项目已过滤")

    # ── 测试组 2: 详情页解析 ──
    print("\n📌 测试组 2: 详情页解析")

    detail = adapter.parse_detail(MOCK_DETAIL_HTML)
    assert_equal(detail["title"], "广东移动2024年度品牌广告投放服务项目招标公告", "标题")
    assert_equal(detail["purchaser"], "中国移动通信集团广东有限公司", "采购方")
    assert_equal(detail["purchaser_level"], "省公司", "层级=省公司")
    assert_equal(detail["bid_number"], "GDYD202406001", "项目编号")
    assert_equal(detail["notice_type"], "招标公告", "公告类型")
    assert_equal(detail["publish_date"], "2024-06-15", "发布日期")
    assert_equal(detail["budget"], 500.0, "预算500万")
    assert_equal(detail["industry"], "移动", "行业=移动")
    assert_true("张经理" in detail.get("contact_info", ""), "联系人提取")

    # 中标详情
    detail2 = adapter.parse_detail(MOCK_DETAIL2_HTML)
    assert_equal(detail2["title"], "中国移动广东公司东莞分公司宣传活动物料制作项目中标结果公示", "中标标题")
    assert_equal(detail2["purchaser"], "中国移动通信集团广东有限公司东莞分公司", "采购方(东莞)")
    assert_equal(detail2["purchaser_level"], "东莞分公司", "层级=东莞分公司")
    assert_equal(detail2["budget"], 150.0, "预算150万")
    assert_equal(detail2["notice_type"], "中标结果", "类型=中标结果")

    # ── 测试组 3: 标准化+过滤 ──
    print("\n📌 测试组 3: 标准化 + 关键词过滤")

    record = adapter._normalize_record(detail)
    assert_true(record["is_ad"], "广告类=是")
    assert_true("品牌" in record["matched_keywords"], "命中品牌")
    assert_true("广告" in record["matched_keywords"], "命中广告")
    assert_true("投放" in record["matched_keywords"], "命中投放")
    assert_equal(record["procurement_method"], "公开招标", "采购方式")
    assert_equal(record["source_url"], "", "source_url为空(由run填充)")

    record2 = adapter._normalize_record(detail2)
    assert_true(record2["is_ad"], "中标项目也是广告类")
    assert_true("宣传" in record2["matched_keywords"], "命中宣传")

    # ── 测试组 4: 辅助方法 ──
    print("\n📌 测试组 4: 辅助方法")

    assert_equal(adapter._guess_type("广东移动广告项目招标公告"), "招标公告", "招标公告")
    assert_equal(adapter._guess_type("广东移动项目中选结果公示"), "中标公告", "中标公告")
    assert_equal(adapter._guess_type("广东移动项目中标候选人公示"), "中标候选人公示", "候选人公示")
    assert_equal(adapter._guess_level("广东移动东莞分公司广告项目", ""), "东莞分公司", "东莞")
    assert_equal(adapter._guess_level("中国移动广东公司项目", ""), "省公司", "省公司")
    assert_true(adapter._is_gd_mobile("广东移动项目"), "is移动")
    assert_true(not adapter._is_gd_mobile("水务局项目"), "非移动")

    adapter.close()

    # ── 结果 ──
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"  测试结果: {passed}/{total} 通过", end="")
    if failed > 0:
        print(f"  ❌ {failed} 个失败")
    else:
        print("  🎉 全部通过！")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
