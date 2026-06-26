"""
爬虫单元测试
使用模拟 HTML 数据验证解析器和管道的正确性。
"""

import sys
import os
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.services.crawler.parser import (
    parse_list_page,
    parse_detail_page,
    _extract_budget,
    _extract_score_weight,
    _extract_qualification,
    _extract_purchaser_level,
    _normalize_date,
    _normalize_datetime,
    _normalize_procurement_method,
)
from app.services.keyword_filter import filter_advertisement_projects

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ============================================================
# Mock 数据
# ============================================================

MOCK_LIST_HTML = """
<!DOCTYPE html>
<html>
<head><title>中国移动采购与招标网</title></head>
<body>
<div class="main-content">
    <table class="notice-table">
        <thead>
            <tr><th>项目名称</th><th>发布日期</th><th>采购方式</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><a href="/b2b/main/viewNoticeContent.html?noticeId=100001">
                    中国移动广东公司2024年度品牌广告投放项目
                </a></td>
                <td>2024-06-15</td>
                <td>公开招标</td>
            </tr>
            <tr>
                <td><a href="/b2b/main/viewNoticeContent.html?noticeId=100002">
                    广东移动5G基站机房建设施工项目
                </a></td>
                <td>2024-06-14</td>
                <td>公开招标</td>
            </tr>
            <tr>
                <td><a href="/b2b/main/viewNoticeContent.html?noticeId=100003">
                    中国移动通信集团广东有限公司宣传活动执行项目
                </a></td>
                <td>2024-06-13</td>
                <td>公开比选</td>
            </tr>
            <tr>
                <td><a href="/b2b/main/viewNoticeContent.html?noticeId=100004">
                    广东移动微信公众号代运营与视频号直播服务
                </a></td>
                <td>2024-06-12</td>
                <td>竞争性谈判</td>
            </tr>
            <tr>
                <td><a href="/b2b/main/viewNoticeContent.html?noticeId=100005">
                    广东移动办公大楼物业保洁服务采购
                </a></td>
                <td>2024-06-11</td>
                <td>公开招标</td>
            </tr>
        </tbody>
    </table>
</div>
</body>
</html>
"""

MOCK_DETAIL_AD = """
<!DOCTYPE html>
<html>
<head><title>中国移动广东公司2024年度品牌广告投放项目</title></head>
<body>
<div class="notice-content">
    <h1>中国移动广东公司2024年度品牌广告投放项目</h1>

    <p>采购人：中国移动通信集团广东有限公司</p>
    <p>采购方式：公开招标</p>

    <h2>一、项目概况</h2>
    <p>本项目为中国移动广东公司2024年度品牌广告投放服务采购，
    预算金额为500万元，包含抖音信息流广告投放、KOL达人资源采购、
    品牌创意设计及短视频制作等内容。</p>

    <p>采购预算：500万元</p>
    <p>发布日期：2024年06月15日</p>
    <p>投标截止时间：2024年07月20日 17:00:00</p>

    <h2>二、供应商资格要求</h2>
    <p>1. 投标人须具有独立法人资格，注册资金不低于1000万元。</p>
    <p>2. 近三年具有同类项目经验，需提供合同证明。</p>
    <p>3. 具有抖音、快手等平台广告投放代理资质。</p>

    <h2>三、评分办法</h2>
    <p>本项目采用综合评分法：技术分占40%，商务分占30%，价格分占30%。</p>
</div>
</body>
</html>
"""

MOCK_DETAIL_NON_AD = """
<!DOCTYPE html>
<html>
<head><title>广东移动5G基站机房建设施工项目</title></head>
<body>
<div class="notice-content">
    <h1>广东移动5G基站机房建设施工项目</h1>

    <p>采购人：中国移动通信集团广东有限公司</p>
    <p>采购方式：公开招标</p>

    <h2>一、项目概况</h2>
    <p>本项目为5G基站土建施工及机房配套工程，预算金额为2000万元。</p>

    <p>采购预算：2000万元</p>
    <p>发布日期：2024年06月14日</p>

    <h2>二、资格要求</h2>
    <p>1. 具备建筑工程施工总承包一级资质。</p>

    <h2>三、评分办法</h2>
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


def assert_equal(actual, expected, test_name):
    global passed, failed
    if actual == expected:
        passed += 1
        print(f"  ✅ {test_name}")
    else:
        failed += 1
        print(f"  ❌ {test_name}")
        print(f"     期望: {expected!r}")
        print(f"     实际: {actual!r}")


def assert_true(condition, test_name):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {test_name}")
    else:
        failed += 1
        print(f"  ❌ {test_name}")


def run_all_tests():
    global passed, failed
    passed = 0
    failed = 0

    print("=" * 60)
    print("标中宝爬虫 — 单元测试（Mock 数据）")
    print("=" * 60)

    # ── 测试组 1: 列表页解析 ──
    print("\n📌 测试组 1: 列表页解析")

    items = parse_list_page(MOCK_LIST_HTML)
    assert_true(len(items) == 5, f"列表页解析出5条公告（实际 {len(items)}）")

    if len(items) >= 1:
        assert_true("品牌广告投放" in items[0]["title"], "第1条标题含'品牌广告投放'")
        assert_equal(items[0]["publish_date"], "2024-06-15", "第1条日期")
        assert_equal(items[0]["procurement_method"], "公开招标", "第1条采购方式")

    if len(items) >= 3:
        assert_equal(items[2]["procurement_method"], "公开询比", "第3条'公开比选'→'公开询比'")

    if len(items) >= 4:
        assert_equal(items[3]["procurement_method"], "竞争性谈判", "第4条采购方式")

    # ── 测试组 2: 详情页解析 ──
    print("\n📌 测试组 2: 详情页解析")

    detail = parse_detail_page(MOCK_DETAIL_AD, url="http://test/100001")
    assert_equal(detail["title"], "中国移动广东公司2024年度品牌广告投放项目", "详情页标题")
    assert_equal(detail["purchaser"], "中国移动通信集团广东有限公司", "采购方提取")
    assert_equal(detail["procurement_method"], "公开招标", "采购方式提取")
    assert_equal(detail["budget"], 500.0, "预算金额 500万元")
    assert_equal(detail["announce_date"], "2024-06-15", "发布日期")
    assert_equal(detail["deadline"], "2024-07-20 17:00:00", "投标截止时间")
    assert_true("独立法人" in detail["qualification_requirements"], "资格要求提取")
    assert_equal(detail["source_url"], "http://test/100001", "来源URL")

    score = detail["score_weight"]
    assert_true(score is not None, "评分权重非空")
    if score:
        assert_equal(score["tech"], 0.40, "技术分权重 40%")
        assert_equal(score["biz"], 0.30, "商务分权重 30%")
        assert_equal(score["price"], 0.30, "价格分权重 30%")

    # 非广告项目详情页
    detail2 = parse_detail_page(MOCK_DETAIL_NON_AD)
    assert_equal(detail2["budget"], 2000.0, "基站项目预算 2000万")
    assert_true("施工总承包" in detail2["qualification_requirements"], "基站项目资格要求")

    # ── 测试组 3: 辅助函数 ──
    print("\n📌 测试组 3: 辅助函数")

    # 金额提取
    assert_equal(_extract_budget("预算金额：500万元"), 500.0, "提取'500万元'")
    assert_equal(_extract_budget("采购预算 320.5 万"), 320.5, "提取'320.5万'")
    assert_equal(_extract_budget("预算：1,200万元"), 1200.0, "提取'1,200万元'")
    assert_equal(_extract_budget("不含税预算 4500000元"), 450.0, "提取'4500000元'→450万")
    assert_equal(_extract_budget(""), None, "空文本→None")
    assert_equal(_extract_budget("本项目无预算"), None, "无金额→None")

    # 评分权重提取
    s1 = _extract_score_weight("技术分占40%，商务分占30%，价格分占30%")
    assert_true(s1 is not None, "提取百分比格式")
    if s1:
        assert_equal(s1["tech"], 0.40, "技术40%")
        assert_equal(s1["biz"], 0.30, "商务30%")

    s2 = _extract_score_weight("技术：40，商务：30，价格：30")
    assert_true(s2 is not None, "提取冒号格式")
    if s2:
        assert_equal(s2["price"], 0.30, "价格30%")

    s3 = _extract_score_weight("综合评分法：技术部分40分，商务部分30分，价格部分30分")
    assert_true(s3 is not None, "提取'评分法'格式")

    s4 = _extract_score_weight("")
    assert_equal(s4, None, "空文本→None")

    # 采购方层级
    assert_equal(_extract_purchaser_level("中国移动广东公司"), "省公司", "省公司识别")
    assert_equal(
        _extract_purchaser_level("中国移动广东广州分公司品牌项目"),
        "广州分公司",
        "广州分公司识别",
    )
    assert_equal(
        _extract_purchaser_level("中国移动通信集团广东有限公司东莞分公司"),
        "东莞分公司",
        "东莞分公司识别",
    )

    # 日期标准化
    assert_equal(_normalize_date("2024-06-15"), "2024-06-15", "YYYY-MM-DD")
    assert_equal(_normalize_date("2024/06/15"), "2024-06-15", "YYYY/MM/DD")
    assert_equal(_normalize_date("2024年06月15日"), "2024-06-15", "YYYY年MM月DD日")
    assert_equal(_normalize_date(""), "", "空日期")
    assert_equal(_normalize_date("2024-6-5"), "2024-06-05", "补零")

    # 日期时间标准化
    assert_equal(
        _normalize_datetime("2024-07-20 17:00:00"),
        "2024-07-20 17:00:00",
        "完整日期时间",
    )
    assert_equal(
        _normalize_datetime("2024年07月20日 17:00"),
        "2024-07-20 17:00:00",
        "中文日期时间补秒",
    )

    # 采购方式标准化
    assert_equal(_normalize_procurement_method("公开招标"), "公开招标", "公开招标→公开招标")
    assert_equal(_normalize_procurement_method("公开比选"), "公开询比", "公开比选→公开询比")
    assert_equal(_normalize_procurement_method("竞争性谈判"), "竞争性谈判", "竞争性谈判")
    assert_equal(_normalize_procurement_method(""), "公开招标", "空值默认公开招标")

    # ── 测试组 4: 端到端：解析+过滤 ──
    print("\n📌 测试组 4: 端到端（解析 → 关键词过滤）")

    # 广告项目
    detail_ad = parse_detail_page(MOCK_DETAIL_AD)
    filter_result = filter_advertisement_projects(
        detail_ad["title"],
        detail_ad.get("qualification_requirements", ""),
    )
    assert_true(filter_result["is_ad"], "广告投放项目判定为广告类")
    assert_true("品牌" in filter_result["matched_keywords"], "命中'品牌'")
    assert_true("广告" in filter_result["matched_keywords"], "命中'广告'")
    assert_true("投放" in filter_result["matched_keywords"], "命中'投放'")
    assert_equal(filter_result["category"], "媒介投放类", "赛道=媒介投放类")

    # 非广告项目
    detail_non = parse_detail_page(MOCK_DETAIL_NON_AD)
    filter_result2 = filter_advertisement_projects(
        detail_non["title"],
        detail_non.get("qualification_requirements", ""),
    )
    assert_true(not filter_result2["is_ad"], "基站施工项目判定为非广告类")
    assert_true("命中排除关键词" in filter_result2.get("reason", ""), "返回排除原因")

    # ── 测试组 5: 列表页项目批量过滤 ──
    print("\n📌 测试组 5: 列表页→关键词过滤（模拟管道）")

    list_items = parse_list_page(MOCK_LIST_HTML)
    ad_count = 0
    non_ad_count = 0
    categories = []

    for item in list_items:
        result = filter_advertisement_projects(item["title"], "")
        if result["is_ad"]:
            ad_count += 1
            categories.append(result["category"])
        else:
            non_ad_count += 1

    assert_equal(ad_count, 3, "5条中3条为广告类")
    assert_equal(non_ad_count, 2, "5条中2条为非广告类")
    assert_true("媒介投放类" in categories, "含媒介投放类")
    assert_true("活动执行类" in categories, "含活动执行类")
    assert_true("新媒体运营类" in categories, "含新媒体运营类")

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
