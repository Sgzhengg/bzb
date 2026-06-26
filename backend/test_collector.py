"""
标中宝 V1 — DataCollector 集成测试

测试范围:
  1. 配置文件加载  — 默认适配器/备用/阈值
  2. 适配器动态加载  — importlib 实例化
  3. 容错切换逻辑   — 连续失败 → 自动切换
  4. 任务日志记录   — 执行情况记录
  5. 适配器列表     — list_adapters()

不测试真实 HTTP 请求，仅验证框架层。
"""

import os
import sys
import tempfile
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_collector import DataCollector

# 抑制测试期间的日志噪音
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
        print(f"  ❌ {name}: {item!r} not in {container!r}")


# ============================================================
# 构造最小可用配置
# ============================================================

MINIMAL_CONFIG = """
data_collector:
  default_adapter: "zhaobiao"
  fallback_adapter: "gd_zbtb"
  failure_threshold: 2
  auto_fallback: true
  adapters:
    zhaobiao:
      enabled: true
      module: "adapters.zhaobiao_adapter"
      class_name: "ZhaobiaoAdapter"
      config:
        base_url: "https://www.zhaobiao.cn"
        max_pages: 1
        min_delay: 0
        max_delay: 0
    gd_zbtb:
      enabled: true
      module: "adapters.gd_zbtb_adapter"
      class_name: "GzZbtbAdapter"
      config:
        base_url: "https://zbtb.gd.gov.cn"
        max_pages: 1
        min_delay: 0
        max_delay: 0
    gd_ygp:
      enabled: false
      module: "adapters.gd_ygp_adapter"
      class_name: "GdYgpAdapter"
      config:
        base_url: "https://ygp.gdzwfw.gov.cn"
        max_pages: 1
        min_delay: 0
        max_delay: 0
"""


# ============================================================
# 测试
# ============================================================

def test_config_loading():
    """测试组 1: 配置文件加载"""
    print("\n📌 测试组 1: 配置文件加载")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(MINIMAL_CONFIG)
        tmp_path = f.name

    try:
        dc = DataCollector(tmp_path)

        assert_equal(dc.default_adapter, "zhaobiao", "默认适配器=zhaobiao")
        assert_equal(dc.fallback_adapter, "gd_zbtb", "备用适配器=gd_zbtb")
        assert_equal(dc.failure_threshold, 2, "失败阈值=2")
        assert_true(dc.auto_fallback, "自动切换=enabled")

        # 适配器注册表
        assert_in("zhaobiao", dc._adapters, "注册了zhaobiao")
        assert_in("gd_zbtb", dc._adapters, "注册了gd_zbtb")
        assert_in("gd_ygp", dc._adapters, "注册了gd_ygp")

        assert_true(dc._adapters["zhaobiao"]["enabled"], "zhaobiao已启用")
        assert_true(dc._adapters["gd_ygp"]["enabled"] is False, "gd_ygp已禁用")

    finally:
        os.unlink(tmp_path)


def test_adapter_loading():
    """测试组 2: 适配器动态加载"""
    print("\n📌 测试组 2: 适配器动态加载")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(MINIMAL_CONFIG)
        tmp_path = f.name

    try:
        dc = DataCollector(tmp_path)

        # 加载 zhaobiao
        adapter = dc._load_adapter("zhaobiao")
        assert_true(adapter is not None, "zhaobiao实例化成功")
        assert_equal(adapter.get_source_name(), "zhaobiao", "get_source_name()")
        assert_equal(adapter.name, "中国招标网", "显示名称=中国招标网")
        assert_true(hasattr(adapter, "fetch_list"), "有fetch_list")
        assert_true(hasattr(adapter, "parse_list"), "有parse_list")
        assert_true(hasattr(adapter, "fetch_detail"), "有fetch_detail")
        assert_true(hasattr(adapter, "parse_detail"), "有parse_detail")
        assert_true(hasattr(adapter, "run"), "有run")

        # 加载 gd_zbtb
        adapter2 = dc._load_adapter("gd_zbtb")
        assert_equal(adapter2.get_source_name(), "gd_zbtb", "gd_zbtb::get_source_name()")
        assert_equal(adapter2.name, "广东招标投标监管网", "显示名称")

        # 缓存命中
        assert_true(dc._load_adapter("zhaobiao") is adapter, "缓存命中(同一实例)")

        # 禁用适配器抛出异常
        try:
            dc._load_adapter("gd_ygp")
            assert_true(False, "禁用适配器应抛出异常")
        except RuntimeError as e:
            assert_true("禁用" in str(e), "RuntimeError: 已禁用")

        # 不存在的适配器
        try:
            dc._load_adapter("nonexistent")
            assert_true(False, "不存在的适配器应抛出异常")
        except ValueError as e:
            assert_true("未在配置中找到" in str(e), "ValueError: 未找到")

        adapter.close()
        adapter2.close()

    finally:
        os.unlink(tmp_path)


def test_fallback_logic():
    """测试组 3: 容错切换逻辑"""
    print("\n📌 测试组 3: 容错切换逻辑")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(MINIMAL_CONFIG)
        tmp_path = f.name

    try:
        dc = DataCollector(tmp_path)

        # 初始状态：0 次失败
        assert_equal(dc._failure_counts.get("zhaobiao", 0), 0, "初始失败计数=0")

        # 模拟失败计数累积但不触发
        dc._failure_counts["zhaobiao"] = 1
        # threshold=2, 1次失败 → 不切换
        assert_true(not dc._should_fallback("zhaobiao", Exception("test")),
                    "1次失败不触发切换")

        # 2次失败 → 触发切换
        dc._failure_counts["zhaobiao"] = 2
        assert_true(dc._should_fallback("zhaobiao", Exception("test")),
                    "2次失败触发切换(threshold=2)")

        # 已经是备用适配器，不再切换
        assert_true(not dc._should_fallback("gd_zbtb", Exception("test")),
                    "备用适配器不切换(防循环)")

        # 致命错误不切换（ImportError）
        dc._failure_counts["zhaobiao"] = 5
        assert_true(not dc._should_fallback("zhaobiao", ImportError("no module")),
                    "ImportError不触发切换")

        # 致命错误不切换（ValueError）
        assert_true(not dc._should_fallback("zhaobiao", ValueError("bad config")),
                    "ValueError不触发切换")

        # auto_fallback=false
        dc.auto_fallback = False
        assert_true(not dc._should_fallback("zhaobiao", Exception("test")),
                    "auto_fallback=false不切换")

        # 恢复
        dc.auto_fallback = True
        dc.reset_failures()
        # reset_failures 清空整个 dict，后续 get 用 0 兜底
        assert_equal(dc._failure_counts.get("zhaobiao", 0), 0, "reset后计数=0")

    finally:
        os.unlink(tmp_path)


def test_task_logging():
    """测试组 4: 任务日志记录"""
    print("\n📌 测试组 4: 任务执行日志")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(MINIMAL_CONFIG)
        tmp_path = f.name

    try:
        dc = DataCollector(tmp_path)

        # 初始为空
        assert_equal(len(dc.get_task_log()), 0, "初始日志为空")

        # 模拟 collect 失败 — 会添加到日志
        try:
            dc.collect(adapter_name="zhaobiao", save_to_db=False)
        except Exception:
            pass  # 预期失败（无网络）

        logs = dc.get_task_log()
        assert_true(len(logs) >= 1, "至少1条任务日志")
        if logs:
            last = logs[-1]
            assert_equal(last["adapter"], "zhaobiao", "日志记录了适配器名称")
            # 状态可能是 success 或 failed（取决于网络）
            assert_in(last["status"], ["success", "failed", "running"],
                      "日志状态有效")
            assert_true("elapsed" in last, "日志有耗时字段")

    finally:
        os.unlink(tmp_path)


def test_list_adapters():
    """测试组 5: 适配器列表 + 辅助方法"""
    print("\n📌 测试组 5: 适配器列表")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(MINIMAL_CONFIG)
        tmp_path = f.name

    try:
        dc = DataCollector(tmp_path)

        adapters = dc.list_adapters()
        assert_equal(len(adapters), 3, "3个适配器")

        names = [a["name"] for a in adapters]
        assert_in("zhaobiao", names, "列表含zhaobiao")
        assert_in("gd_zbtb", names, "列表含gd_zbtb")
        assert_in("gd_ygp", names, "列表含gd_ygp")

        # 状态字段
        zhaobiao = next(a for a in adapters if a["name"] == "zhaobiao")
        assert_true(zhaobiao["enabled"], "zhaobiao=enabled")
        assert_equal(zhaobiao["class"], "ZhaobiaoAdapter", "class=ZhaobiaoAdapter")

        ygp = next(a for a in adapters if a["name"] == "gd_ygp")
        assert_true(not ygp["enabled"], "gd_ygp=disabled")

    finally:
        os.unlink(tmp_path)


def test_guess_class_name():
    """测试组 6: 类名推断"""
    print("\n📌 测试组 6: 类名推断 (_guess_class_name)")

    mapping = {
        "zhaobiao": "ZhaobiaoAdapter",
        "gd_zbtb": "GzZbtbAdapter",
        "gd_ygp": "GdYgpAdapter",
        "b2b_10086": "B2b10086Adapter",
    }
    for name, expected in mapping.items():
        assert_equal(DataCollector._guess_class_name(name), expected,
                     f"{name} → {expected}")


# ============================================================
# 入口
# ============================================================

def run_tests():
    global passed, failed
    passed = 0
    failed = 0

    print("=" * 60)
    print("DataCollector 统一调度器 — 集成测试")
    print("=" * 60)

    test_config_loading()
    test_adapter_loading()
    test_fallback_logic()
    test_task_logging()
    test_list_adapters()
    test_guess_class_name()

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
