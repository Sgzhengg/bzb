"""
标中宝 V1 — 历史采集器 + 请求工具 集成测试

测试范围:
  1. request_utils: UA池/令牌桶/随机延迟/RequestSession创建
  2. history_collector: 断点加载保存/日期过滤/去重/校验/安全标准化
  3. 断点续传: 模拟中断→恢复流程
"""

import json
import os
import sys
import tempfile
import logging
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 抑制日志噪音
logging.basicConfig(level=logging.CRITICAL)

# ============================================================
# 测试辅助
# ============================================================

passed = 0
failed = 0


def assert_equal(actual, expected, name: str):
    global passed, failed
    if actual == expected:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}")
        print(f"     期望: {expected!r}")
        print(f"     实际: {actual!r}")


def assert_true(condition: bool, name: str):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}")


def assert_in(item, container, name: str):
    global passed, failed
    if item in container:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}")


# ============================================================
# 测试组 1: request_utils
# ============================================================

def test_ua_pool():
    print("\n📌 测试组 1: User-Agent 池")
    from utils.request_utils import USER_AGENT_POOL, random_ua

    assert_true(len(USER_AGENT_POOL) >= 18, "至少18个UA")
    ua1 = random_ua()
    ua2 = random_ua()
    assert_true(len(ua1) > 50, "UA长度>50")
    assert_true("Mozilla" in ua1, "UA含Mozilla")


def test_token_bucket():
    print("\n📌 测试组 2: 令牌桶限速")
    import time
    from utils.request_utils import TokenBucket

    # 高速桶：几乎不阻塞
    bucket = TokenBucket(rpm=60)
    t0 = time.time()
    for _ in range(10):
        bucket.acquire()
    elapsed = time.time() - t0
    assert_true(elapsed < 0.5, f"rpm=60, 10次acquire耗时 {elapsed:.2f}s < 0.5s")

    # 低速桶：应明显阻塞
    bucket2 = TokenBucket(rpm=6)
    t0 = time.time()
    for _ in range(3):
        bucket2.acquire()
    elapsed = time.time() - t0
    # rpm=6 → 每10秒1个令牌，3个需要约20秒
    assert_true(elapsed < 22, f"rpm=6, 3次acquire耗时 {elapsed:.2f}s < 22s")


def test_random_delay():
    print("\n📌 测试组 3: 随机延迟")
    import time
    from utils.request_utils import random_delay

    t0 = time.time()
    random_delay(0.1, 0.3)
    elapsed = time.time() - t0
    assert_true(0.09 <= elapsed <= 0.4, f"延迟0.1-0.3s, 实际 {elapsed:.2f}s")


def test_request_session_creation():
    print("\n📌 测试组 4: RequestSession 创建")
    from utils.request_utils import RequestSession, create_session

    # 基础创建
    s = RequestSession(domain="test.com", rpm=15, min_delay=1, max_delay=2)
    assert_equal(s.domain, "test.com", "domain=test.com")
    assert_equal(s.rpm, 15, "rpm=15")
    assert_equal(s.max_retries, 3, "max_retries=3")
    assert_equal(s.proxy_enabled, False, "proxy默认关闭")
    assert_true(s.client is not None, "自动创建客户端")
    stats = s.get_stats()
    assert_equal(stats["total_requests"], 0, "初始请求数=0")
    s.close()

    # 通过配置创建
    s2 = create_session("zhaobiao.cn", {
        "request_interval": {"min": 3, "max": 8},
        "retry": {"max_attempts": 5, "backoff_factor": 3},
        "rpm": 10,
    })
    assert_equal(s2.max_retries, 5, "max_retries=5")
    assert_equal(s2.backoff_factor, 3, "backoff_factor=3")
    s2.close()

    # 代理
    s3 = RequestSession(
        domain="test.com",
        proxies=["http://p1:8080", "http://p2:8080"],
        proxy_enabled=True,
    )
    assert_true(s3.proxy_enabled, "代理启用")
    s3.close()


# ============================================================
# 测试组 5: HistoryCollector 基础设施
# ============================================================

def test_date_extraction():
    print("\n📌 测试组 5: 日期提取")
    from history_collector import HistoryCollector

    hc = HistoryCollector()

    d1 = hc._extract_date_from_item({"publish_date": "2024-06-15"})
    assert_equal(str(d1), "2024-06-15", "2024-06-15")

    d2 = hc._extract_date_from_item({"publish_date": "2024年06月15日"})
    assert_equal(str(d2), "2024-06-15", "2024年06月15日")

    d3 = hc._extract_date_from_item({"publish_date": "2024/06/15"})
    assert_equal(str(d3), "2024-06-15", "2024/06/15")

    d4 = hc._extract_date_from_item({"publish_date": ""})
    assert_true(d4 is None, "空日期→None")

    d5 = hc._extract_date_from_item({})
    assert_true(d5 is None, "无日期字段→None")


def test_date_range_filter():
    print("\n📌 测试组 6: 日期范围过滤")
    from datetime import date
    from history_collector import HistoryCollector

    hc = HistoryCollector()
    sd = date(2024, 1, 1)
    ed = date(2024, 12, 31)

    assert_true(hc._is_in_range({"publish_date": "2024-06-15"}, sd, ed),
                "2024-06-15 在范围内")
    assert_true(not hc._is_in_range({"publish_date": "2023-12-01"}, sd, ed),
                "2023-12-01 超出范围")
    assert_true(not hc._is_in_range({"publish_date": "2025-01-01"}, sd, ed),
                "2025-01-01 超出范围")
    assert_true(hc._is_in_range({"publish_date": ""}, sd, ed),
                "空日期保守处理→在范围内")
    assert_true(hc._is_in_range({}, sd, ed),
                "无日期保守处理→在范围内")


def test_dedup():
    print("\n📌 测试组 7: 去重机制")
    from history_collector import HistoryCollector

    hc = HistoryCollector()

    # 初始不重复
    assert_true(not hc._is_duplicate("项目A", "http://example.com/1"), "第一次不重复")
    hc._mark_collected("项目A", "http://example.com/1")

    # URL 重复
    assert_true(hc._is_duplicate("项目A", "http://example.com/1"), "URL重复")
    assert_true(hc._is_duplicate("项目B", "http://example.com/1"), "不同标题同URL=重复")

    # 标题重复
    hc._mark_collected("项目C", "http://example.com/2")
    assert_true(hc._is_duplicate("项目C", "http://example.com/3"), "标题重复")

    # 完全不同的不重复
    assert_true(not hc._is_duplicate("项目D", "http://example.com/4"), "不同标题+URL不重复")


def test_validation():
    print("\n📌 测试组 8: 数据校验")
    from history_collector import HistoryCollector

    hc = HistoryCollector()

    # 完整记录
    assert_equal(
        hc._validate_record({"title": "t", "purchaser": "p", "announce_date": "d"}),
        [],
        "完整记录→无缺失",
    )

    # 缺失 title
    missing = hc._validate_record({"title": "", "purchaser": "p", "announce_date": "d"})
    assert_in("title", missing, "title缺失")

    # 缺失多个
    missing = hc._validate_record({"title": "", "purchaser": "", "announce_date": ""})
    assert_equal(len(missing), 3, "3个字段缺失")


def test_checkpoint():
    print("\n📌 测试组 9: 断点保存/加载")
    from history_collector import HistoryCollector

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump({
            "last_date": "2024-06-15",
            "last_page": 5,
            "total_collected": 120,
            "collected_urls": ["http://a", "http://b"],
        }, f)
        tmp = f.name

    try:
        # 通过 monkey-patch checkpoint_file
        hc = HistoryCollector()
        hc.checkpoint_file = tmp
        cp = hc._load_checkpoint()

        assert_equal(cp["last_date"], "2024-06-15", "加载last_date")
        assert_equal(cp["last_page"], 5, "加载last_page")
        assert_equal(cp["total_collected"], 120, "加载total_collected")
        assert_equal(len(cp["collected_urls"]), 2, "加载collected_urls")

        # 保存
        hc._checkpoint = cp
        hc._total_collected = 130
        hc._collected_urls = {"http://a", "http://b", "http://c"}
        hc._save_checkpoint("2024-06-16", 6, 3)

        # 重新加载验证
        cp2 = hc._load_checkpoint()
        assert_equal(cp2["last_date"], "2024-06-16", "保存后加载last_date")
        assert_equal(cp2["total_collected"], 130, "保存后加载total_collected")

    finally:
        os.unlink(tmp)


def test_safe_normalize():
    print("\n📌 测试组 10: 安全标准化（字段容错）")
    from history_collector import HistoryCollector

    hc = HistoryCollector()

    # 正常记录
    parsed = {
        "title": "测试项目",
        "purchaser": "测试采购方",
        "purchaser_level": "省公司",
        "procurement_method": "公开招标",
        "budget": 100.0,
        "notice_type": "招标公告",
        "bid_number": "TEST-001",
        "publish_date": "2024-06-15",
        "deadline": "2024-07-15 17:00",
        "content_text": "测试内容",
    }

    # 需要模拟 adapter 有 _save_to_db
    class FakeAdapter:
        def _save_to_db(self, record):
            pass

    adapter = FakeAdapter()
    record = hc._safe_normalize(adapter, parsed, "http://test.com/1")
    assert_equal(record["title"], "测试项目", "title提取")
    assert_equal(record["budget"], 100.0, "budget提取")
    assert_equal(record["announce_date"], "2024-06-15", "date映射")
    assert_equal(record["source_url"], "http://test.com/1", "source_url")
    assert_equal(record["procurement_method"], "公开招标", "procurement_method")

    # 部分缺失
    parsed_missing = {
        "title": "缺失字段项目",
        "purchaser": "",
        "content_text": "",
    }
    record2 = hc._safe_normalize(adapter, parsed_missing, "http://test.com/2")
    assert_equal(record2["title"], "缺失字段项目", "title存在")
    assert_equal(record2["purchaser"], "", "purchaser空")
    assert_equal(record2["procurement_method"], "公开招标", "默认采购方式")
    assert_equal(record2["notice_type"], "招标公告", "默认公告类型")

    # 完全异常（非 dict 类型字段）
    parsed_bad = {
        "title": "异常项目",
        "budget": "不是数字",
        "publish_date": None,
    }
    record3 = hc._safe_normalize(adapter, parsed_bad, "http://test.com/3")
    assert_equal(record3["title"], "异常项目", "异常字段不影响title")


# ============================================================
# 入口
# ============================================================

def run_tests():
    global passed, failed
    passed = 0
    failed = 0

    print("=" * 60)
    print("历史采集器 + 请求工具 — 集成测试")
    print("=" * 60)

    test_ua_pool()
    test_token_bucket()
    test_random_delay()
    test_request_session_creation()
    test_date_extraction()
    test_date_range_filter()
    test_dedup()
    test_validation()
    test_checkpoint()
    test_safe_normalize()

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
