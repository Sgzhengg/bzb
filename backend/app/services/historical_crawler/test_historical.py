"""
历史中标采集 — 单元测试
测试数据清洗、解析器、断点续传等核心功能。
"""

import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.services.historical_crawler.cleaner import (
    normalize_purchaser_name,
    normalize_winner_name,
    normalize_amount,
    extract_bid_and_budget,
    identify_winner_type,
    calc_discount_rate,
    extract_contract_period,
    clean_award_record,
    batch_clean,
)
from app.services.historical_crawler.collector import (
    CheckpointManager,
    BatchSaver,
    parse_award_detail,
)

# ============================================================
# Mock 数据
# ============================================================

MOCK_AWARD_HTML = """
<!DOCTYPE html>
<html>
<head><title>中国移动广东公司2024年度品牌广告投放项目中标结果公示</title></head>
<body>
<div class="notice-content">
    <h1>中国移动广东公司2024年度品牌广告投放项目中标结果公示</h1>

    <p>采购人：中国移动通信集团广东有限公司</p>
    <p>采购方式：公开招标</p>
    <p>中标人：广东省广告集团股份有限公司</p>
    <p>中标金额：4850000元</p>
    <p>采购预算：500万元</p>
    <p>开标日期：2024年07月20日</p>

    <h2>一、项目概况</h2>
    <p>本项目为中国移动广东公司2024年度品牌广告投放服务采购，
    包括抖音信息流广告投放、KOL达人资源采购等内容。</p>

    <h2>二、评审结果</h2>
    <p>第一中标候选人：广东省广告集团股份有限公司</p>
    <p>第二中标候选人：广州某某文化传播有限公司</p>

    <h2>三、合同期限</h2>
    <p>合同期限：2024年8月1日至2025年7月31日</p>
</div>
</body>
</html>
"""

MOCK_AWARD_HTML2 = """
<!DOCTYPE html>
<html>
<head><title>广东移动东莞分公司宣传活动执行项目中选结果公示</title></head>
<body>
<div class="notice-content">
    <h1>广东移动东莞分公司宣传活动执行项目中选结果公示</h1>
    <p>采购人：中国移动通信集团广东有限公司东莞分公司</p>
    <p>中选人：东莞市东艺文化传播有限公司</p>
    <p>中选金额：128.5万元</p>
    <p>项目预算：150万元</p>
    <p>开标日期：2024年06月15日</p>
</div>
</body>
</html>
"""

MOCK_AWARD_HTML3 = """
<!DOCTYPE html>
<html>
<head><title>广东移动5G基站机房建设施工项目中标公告</title></head>
<body>
<div class="notice-content">
    <h1>广东移动5G基站机房建设施工项目中标公告</h1>
    <p>采购人：中国移动通信集团广东有限公司</p>
    <p>中标人：中建三局集团有限公司</p>
    <p>中标金额：2000万元</p>
    <p>开标日期：2024年05月10日</p>
    <h2>评分办法</h2>
    <p>技术部分40分，商务部分30分，价格部分30分。</p>
</div>
</body>
</html>
"""

# ============================================================
# 单元测试
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


def run_all_tests():
    global passed, failed
    passed = 0
    failed = 0

    print("=" * 60)
    print("标中宝历史中标采集 — 单元测试")
    print("=" * 60)

    # ── 测试组 1: 采购方名称标准化 ──
    print("\n📌 测试组 1: 采购方名称标准化")

    assert_equal(
        normalize_purchaser_name("中国移动通信集团广东有限公司"),
        "省公司", "省公司识别"
    )
    assert_equal(
        normalize_purchaser_name("中国移动通信集团广东有限公司东莞分公司"),
        "东莞分公司", "东莞分公司识别"
    )
    assert_equal(
        normalize_purchaser_name("中国移动广东公司广州分公司"),
        "广州分公司", "广州分公司(简写)识别"
    )
    assert_equal(
        normalize_purchaser_name("中国移动通信集团广东有限公司深圳分公司"),
        "深圳分公司", "深圳分公司识别"
    )
    assert_equal(
        normalize_purchaser_name("中国移动通信集团广东有限公司佛山分公司"),
        "佛山分公司", "佛山分公司识别"
    )
    assert_equal(normalize_purchaser_name(""), "未知", "空字符串→未知")
    assert_equal(normalize_purchaser_name("广东省电信公司"), "广东省电信公司", "非移动采购方保留原样")

    # ── 测试组 2: 金额清洗 ──
    print("\n📌 测试组 2: 金额标准化（→万元）")

    assert_equal(normalize_amount("3800000元"), 380.0, "380万元")
    assert_equal(normalize_amount("500万元"), 500.0, "500万元")
    assert_equal(normalize_amount("1200万"), 1200.0, "1200万")
    assert_equal(normalize_amount("不含税：450万元"), 450.0, "含前缀 450万元")
    assert_equal(normalize_amount("0.05亿元"), 500.0, "0.05亿元→500万元")
    assert_equal(normalize_amount("128.5万元"), 128.5, "128.5万元")
    assert_equal(normalize_amount(""), None, "空文本→None")
    assert_equal(normalize_amount("本项目无预算"), None, "无金额→None")
    assert_equal(normalize_amount("2,500万元"), 2500.0, "逗号分隔 2500万元")

    # ── 测试组 3: 中标方类型识别 ──
    print("\n📌 测试组 3: 中标方类型识别")

    assert_equal(identify_winner_type("广东省广告集团股份有限公司"), "头部常客", "省广→头部常客")
    assert_equal(identify_winner_type("蓝色光标传播集团"), "头部常客", "蓝色光标→头部常客")
    assert_equal(identify_winner_type("广州某某文化传播有限公司"), "中小公司", "文化传播→中小公司")
    assert_equal(identify_winner_type("东莞市东艺文化传播有限公司"), "中小公司", "东艺文化传播→中小公司")
    assert_equal(identify_winner_type("某科技发展有限公司"), "新进入者", "科技公司→新进入者")
    assert_equal(identify_winner_type(""), "新进入者", "空名→新进入者")

    # ── 测试组 4: 折扣率计算 ──
    print("\n📌 测试组 4: 折扣率计算")

    assert_equal(calc_discount_rate(485, 500), 97.0, "485/500=97%")
    assert_equal(calc_discount_rate(128.5, 150), 85.67, "128.5/150=85.67%")
    assert_equal(calc_discount_rate(0, 500), 0.0, "0/500=0%")
    assert_equal(calc_discount_rate(500, None), None, "无预算→None")
    assert_equal(calc_discount_rate(None, 500), None, "无中标→None")

    # ── 测试组 5: 合同期限提取 ──
    print("\n📌 测试组 5: 合同期限提取")

    contract = extract_contract_period("合同期限：2024年8月1日至2025年7月31日")
    assert_equal(contract["contract_start"], "2024-08-01", "开始日期")
    assert_equal(contract["contract_end"], "2025-07-31", "结束日期")

    contract2 = extract_contract_period("自合同签订之日起1年")
    assert_equal(contract2["contract_end"], "签订日+1年", "相对期限")

    contract3 = extract_contract_period("")
    assert_equal(contract3["contract_start"], None, "空文本")

    # ── 测试组 6: 中标详情页解析 ──
    print("\n📌 测试组 6: 中标详情页解析")

    detail = parse_award_detail(MOCK_AWARD_HTML, url="http://test/001")
    assert_true("品牌广告投放" in detail["title"], "标题提取")
    assert_equal(detail["winner_name"], "广东省广告集团股份有限公司", "中标方提取")
    assert_equal(detail["bid_amount"], 485.0, "中标金额 485万")
    assert_equal(detail["budget_amount"], 500.0, "预算金额 500万")

    detail2 = parse_award_detail(MOCK_AWARD_HTML2, url="http://test/002")
    assert_equal(detail2["winner_name"], "东莞市东艺文化传播有限公司", "中选方提取")
    assert_equal(detail2["bid_amount"], 128.5, "中选金额 128.5万")
    assert_equal(detail2["budget_amount"], 150.0, "预算 150万")

    detail3 = parse_award_detail(MOCK_AWARD_HTML3, url="http://test/003")
    assert_equal(detail3["bid_amount"], 2000.0, "基站中标 2000万")

    # ── 测试组 7: 完整清洗管道 ──
    print("\n📌 测试组 7: 完整清洗管道")

    # 广告项目清洗
    detail_ad = parse_award_detail(MOCK_AWARD_HTML, url="http://test/001")
    cleaned_ad = clean_award_record(detail_ad)
    assert_equal(cleaned_ad["project_name"], detail_ad["title"], "项目名称保留")
    assert_equal(cleaned_ad["purchaser"], "省公司", "采购方标准化→省公司")
    assert_equal(cleaned_ad["winner_name"], "广东省广告集团股份有限公司", "中标方保留")
    assert_equal(cleaned_ad["winner_type"], "头部常客", "中标方类型→头部常客")
    assert_equal(cleaned_ad["bid_amount"], 485.0, "中标金额")
    assert_equal(cleaned_ad["budget_amount"], 500.0, "预算金额")
    assert_equal(cleaned_ad["discount_rate"], 97.0, "折扣率 97%")
    assert_true(cleaned_ad["project_category"] in [
        "媒介投放类", "品牌策略类"
    ], f"赛道识别: {cleaned_ad['project_category']}")
    assert_equal(cleaned_ad["contract_start"], "2024-08-01", "合同开始")
    assert_equal(cleaned_ad["contract_end"], "2025-07-31", "合同结束")
    assert_equal(cleaned_ad["source_url"], "http://test/001", "来源URL")

    # 地市分公司项目
    detail_city = parse_award_detail(MOCK_AWARD_HTML2, url="http://test/002")
    cleaned_city = clean_award_record(detail_city)
    assert_equal(cleaned_city["purchaser"], "东莞分公司", "采购方→东莞分公司")
    assert_equal(cleaned_city["winner_name"], "东莞市东艺文化传播有限公司", "中选方")
    assert_equal(cleaned_city["winner_type"], "中小公司", "类型→中小公司")

    # 批量清洗
    raw_list = [detail_ad, detail_city, detail3]
    cleaned_list = batch_clean(raw_list)
    assert_equal(len(cleaned_list), 3, "批量清洗3条")
    assert_equal(cleaned_list[0]["winner_type"], "头部常客", "第1条头部")
    assert_equal(cleaned_list[1]["winner_type"], "中小公司", "第2条中小")
    assert_equal(cleaned_list[2]["winner_type"], "新进入者", "第3条新进入")

    # ── 测试组 8: 断点续传 ──
    print("\n📌 测试组 8: 断点续传")

    with tempfile.TemporaryDirectory() as tmpdir:
        checkpoint_path = os.path.join(tmpdir, "test_checkpoint.json")

        # 新建断点
        ckpt = CheckpointManager(checkpoint_path)
        assert_equal(ckpt.count, 0, "新断点为空")

        # 标记已采集
        ckpt.mark_processed("http://test.com/notice/001")
        ckpt.mark_processed("http://test.com/notice/002")
        assert_equal(ckpt.count, 2, "标记2条")
        assert_true(ckpt.is_processed("http://test.com/notice/001"), "URL1已采集")
        assert_true(not ckpt.is_processed("http://test.com/notice/003"), "URL3未采集")

        # 重新加载
        ckpt2 = CheckpointManager(checkpoint_path)
        assert_equal(ckpt2.count, 2, "重新加载仍为2条")
        assert_true(ckpt2.is_processed("http://test.com/notice/001"), "重新加载后URL1仍已采集")

    # ── 测试组 9: 分批保存与合并 ──
    print("\n📌 测试组 9: 分批保存与合并")

    with tempfile.TemporaryDirectory() as tmpdir:
        partial_dir = os.path.join(tmpdir, "partial")
        output_path = os.path.join(tmpdir, "merged.json")

        saver = BatchSaver(partial_dir, output_path)

        batch1 = [
            {"project_name": "项目A", "source_url": "http://a"},
            {"project_name": "项目B", "source_url": "http://b"},
        ]
        batch2 = [
            {"project_name": "项目C", "source_url": "http://c"},
        ]

        saver.save_batch(batch1, label="test1")
        saver.save_batch(batch2, label="test2")

        # 验证分批文件存在
        files = os.listdir(partial_dir)
        assert_true(len(files) == 2, f"2个分批文件（实际{len(files)}）")

        # 合并
        total = saver.merge_all()
        assert_equal(total, 3, "合并后共3条")

        # 验证合并文件内容
        with open(output_path, "r", encoding="utf-8") as f:
            merged = json.load(f)
        assert_equal(merged["total"], 3, "merged total=3")
        assert_equal(len(merged["results"]), 3, "results长度=3")

    # ── 测试组 10: 中标金额/预算金额联合提取 ──
    print("\n📌 测试组 10: bid+预算联合提取")

    text1 = "中标金额：485万元。采购预算：500万元。"
    bid, budget = extract_bid_and_budget(text1)
    assert_equal(bid, 485.0, "中标485")
    assert_equal(budget, 500.0, "预算500")

    text2 = "成交价：128.5万；项目预算150万。"
    bid2, budget2 = extract_bid_and_budget(text2)
    assert_equal(bid2, 128.5, "成交128.5")
    assert_equal(budget2, 150.0, "预算150")

    text3 = "中选金额3650000元"
    bid3, budget3 = extract_bid_and_budget(text3)
    assert_equal(bid3, 365.0, "中选365万(元)")
    assert_equal(budget3, None, "无预算")

    # ── 结果汇总 ──
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
    success = run_all_tests()
    sys.exit(0 if success else 1)
