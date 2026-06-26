"""'
数据源适配器 — 集成入口 + 单元测试

用法:
    # 单元测试
    python -m app.adapters.test_adapters

    # 运行单个适配器
    python -m app.adapters.test_adapters --adapter gd_zbtb

    # 运行全部适配器
    python -m app.adapters.test_adapters --run-all
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Now 'adapters' is importable from D:\bzb\backend\adapters

# ============================================================
# Mock HTML/PDF 样本（用于单元测试，避免线上请求）
# ============================================================

MOCK_LIST_HTML_ZBTB = """
<!DOCTYPE html>
<html>
<head><title>广东省招标投标监管网 - 搜索结果</title></head>
<body>
<div class="xxgk-table">
<table>
<thead><tr><th>项目名称</th><th>发布时间</th></tr></thead>
<tbody>
<tr>
  <td><a href="/cms/xxgk/detail.html?id=202406001">广东移动2024年度品牌广告投放服务项目招标公告</a></td>
  <td>2024-06-15</td>
</tr>
<tr>
  <td><a href="/cms/xxgk/detail.html?id=202406002">中国移动广东公司东莞分公司宣传物料制作项目中选结果公示</a></td>
  <td>2024-06-14</td>
</tr>
<tr>
  <td><a href="/cms/xxgk/detail.html?id=202406003">广东移动5G基站机房建设工程施工招标公告</a></td>
  <td>2024-06-13</td>
</tr>
</tbody>
</table>
</div>
</body>
</html>
"""

MOCK_DETAIL_HTML = """
<!DOCTYPE html>
<html>
<head><title>广东移动2024年度品牌广告投放服务项目招标公告</title></head>
<body>
<div class="xxgk_con content">
  <h1>广东移动2024年度品牌广告投放服务项目招标公告</h1>
  <p>项目编号：GDYD202406001</p>
  <p>采购人：中国移动通信集团广东有限公司</p>
  <p>采购预算：500万元</p>
  <p>发布时间：2024-06-15</p>
  <p>投标截止时间：2024年07月20日 17:00:00</p>
  <div class="qualification">
    <h3>投标人资格要求</h3>
    <p>1. 具有独立法人资格，注册资金不低于1000万元。</p>
    <p>2. 近三年具有同类广告投放项目经验。</p>
  </div>
  <div class="score">
    <h3>评分办法</h3>
    <p>技术分占40%，商务分占30%，价格分占30%。</p>
  </div>
  <a href="/upload/2024/06/zbwj.pdf">招标文件.pdf</a>
</div>
</body>
</html>
"""

MOCK_LIST_JSON_YGP = json.dumps({
    "data": {
        "list": [
            {
                "title": "广东移动2024年度品牌传播策划服务项目招标公告",
                "publishTime": "2024-06-10",
                "url": "/detail/20240610001",
                "noticeType": "招标公告"
            },
            {
                "title": "中国移动广东公司广州分公司活动执行项目中标候选人公示",
                "publishTime": "2024-06-08",
                "url": "/detail/20240608002",
                "noticeType": "中标候选人公示"
            },
            {
                "title": "某市水务局信息化建设项目",
                "publishTime": "2024-06-05",
                "url": "/detail/20240605003",
                "noticeType": "招标公告"
            }
        ]
    }
})

# 简单的 PDF 二进制模拟（前4字节 %PDF）
MOCK_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Size 1 >>\n%%EOF"


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


def test_gd_zbtb():
    """测试广东招标投标监管网适配器。"""
    print("\n📌 测试组 1: 广东招标投标监管网适配器")

    from adapters.gd_zbtb_adapter import GzZbtbAdapter

    adapter = GzZbtbAdapter({"max_pages": 1, "min_delay": 0, "max_delay": 0})

    # 列表解析
    items = adapter.parse_list(MOCK_LIST_HTML_ZBTB)
    assert_equal(len(items), 3, "列表解析3条")
    assert_true("品牌广告投放" in items[0]["title"], "标题含'品牌广告投放'")
    assert_equal(items[0]["publish_date"], "2024-06-15", "日期提取")
    assert_true("detail.html?id=202406001" in items[0]["detail_url"], "URL拼接")

    # 详情解析
    parsed = adapter.parse_detail(MOCK_DETAIL_HTML)
    assert_equal(parsed["title"], "广东移动2024年度品牌广告投放服务项目招标公告", "详情标题")
    assert_equal(parsed["purchaser"], "中国移动通信集团广东有限公司", "采购方")
    assert_equal(parsed["purchaser_level"], "省公司", "层级=省公司")
    assert_equal(parsed["bid_number"], "GDYD202406001", "招标编号")
    assert_equal(parsed["notice_type"], "招标公告", "公告类型")
    assert_equal(parsed["budget"], 500.0, "预算500万")

    # 标准化
    record = adapter._normalize_record(parsed)
    assert_true(record["is_ad"], "广告类判定=是")
    assert_true("品牌" in record["matched_keywords"], "命中'品牌'")
    assert_true("广告" in record["matched_keywords"], "命中'广告'")

    adapter.close()
    print(f"  ✅ 广东招标投标监管网适配器 全部通过")


def test_gd_ygp():
    """测试广东公共资源交易平台适配器。"""
    print("\n📌 测试组 2: 广东公共资源交易平台适配器")

    from adapters.gd_ygp_adapter import GdYgpAdapter

    adapter = GdYgpAdapter({"max_pages": 1, "min_delay": 0, "max_delay": 0})

    # JSON 列表解析
    items = adapter.parse_list(MOCK_LIST_JSON_YGP)
    assert_equal(len(items), 2, "JSON解析2条（过滤掉非移动项目）")
    assert_true("品牌传播策划" in items[0]["title"], "标题正确")
    assert_equal(items[0]["publish_date"], "2024-06-10", "日期")
    assert_equal(items[1]["notice_type"], "中标候选人公示", "类型")

    adapter.close()
    print(f"  ✅ 广东公共资源交易平台适配器 全部通过")


def test_pdf_parser():
    """测试 PDF 解析模块。"""
    print("\n📌 测试组 3: PDF 解析模块")

    from adapters.pdf_parser import (
        extract_text_from_pdf_bytes, extract_fields_from_pdf_text,
    )

    # 基础 PDF 解析（模拟二进制）
    text = extract_text_from_pdf_bytes(MOCK_PDF_BYTES)
    assert_true(isinstance(text, str), "PDF解析返回字符串")
    # 模拟 PDF 太大或损坏
    assert_equal(extract_text_from_pdf_bytes(b""), "", "空字节→空字符串")

    # 字段提取
    sample_text = "采购预算：500万元。投标人资格：1.具有独立法人资格。技术分40%，商务分30%，价格分30%。"
    fields = extract_fields_from_pdf_text(sample_text)
    assert_equal(fields["budget"], 500.0, "PDF提取预算500万")
    assert_true("独立法人" in fields["qualification"], "PDF提取资格要求")
    assert_true(fields["score_weight"] is not None, "PDF提取评分权重")
    if fields["score_weight"]:
        assert_equal(fields["score_weight"]["tech"], 0.40, "技术分40%")

    print(f"  ✅ PDF 解析模块 全部通过")


def test_base_adapter():
    """测试基础适配器。"""
    print("\n📌 测试组 4: 基础适配器")

    from adapters.base_adapter import BaseAdapter, _parse_date, _parse_datetime

    # 日期解析
    from datetime import date, datetime
    assert_equal(_parse_date("2024-06-15"), date(2024, 6, 15), "2024-06-15")
    assert_equal(_parse_date("2024年06月15日"), date(2024, 6, 15), "2024年06月15日")
    assert_equal(_parse_date(""), date.today(), "空日期→今天")

    dt = _parse_datetime("2024-07-20 17:00:00")
    assert_true(dt == datetime(2024, 7, 20, 17, 0, 0), "完整日期时间")

    dt2 = _parse_datetime("2024年07月20日 17:00")
    assert_true(dt2 == datetime(2024, 7, 20, 17, 0, 0), "中文日期时间")

    print(f"  ✅ 基础适配器 全部通过")


# ============================================================
# 运行入口
# ============================================================

def run_all_tests():
    global passed, failed
    passed = 0
    failed = 0

    print("=" * 60)
    print("标中宝 — 数据源适配器 单元测试")
    print("=" * 60)

    test_pdf_parser()
    test_base_adapter()
    test_gd_zbtb()
    test_gd_ygp()

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
    import argparse
    parser = argparse.ArgumentParser(description="数据源适配器测试")
    parser.add_argument("--adapter", choices=["gd_zbtb", "gd_ygp"], help="指定适配器")
    parser.add_argument("--run-all", action="store_true", help="运行全部适配器采集")
    args = parser.parse_args()

    if args.run_all:
        print("🚀 运行全部适配器采集...")
        import yaml
        with open(os.path.join(os.path.dirname(__file__), "adapter_config.yaml"), "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        for key in ["gd_zbtb", "gd_ygp"]:
            if config.get(key, {}).get("enabled", True):
                print(f"\n===== 启动 {config[key]['name']} =====")
                if key == "gd_zbtb":
                    from adapters.gd_zbtb_adapter import GzZbtbAdapter
                    adapter = GzZbtbAdapter(config[key])
                else:
                    from adapters.gd_ygp_adapter import GdYgpAdapter
                    adapter = GdYgpAdapter(config[key])
                try:
                    results = adapter.run(save_to_db=False)
                    print(f"结果: {len(results)} 条广告类项目")
                except Exception as e:
                    print(f"采集失败: {e}")
    else:
        success = run_all_tests()
        sys.exit(0 if success else 1)
