"""
标中宝 V1 — 统一数据采集调度器

功能:
  - 配置化管理：通过 config.yaml 定义和切换数据源
  - 统一接口：所有适配器遵循 BaseAdapter 协议
  - 容错切换：主适配器连续失败超过阈值 → 自动切换备用适配器
  - 任务日志：每次采集的执行情况（成功/失败、耗时、数据量）

使用:
    from data_collector import DataCollector

    collector = DataCollector("backend/adapters/adapter_config.yaml")
    results = collector.collect()                        # 使用默认适配器
    results = collector.collect(adapter_name="gd_zbtb")   # 指定适配器
"""

import logging
import time
import importlib
import sys
import os
from typing import List, Dict, Optional, Type

import yaml

# 确保 backend 在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger("data_collector")


# ============================================================
# DataCollector
# ============================================================

class DataCollector:
    """
    统一数据采集调度器。

    职责:
      1. 解析配置文件，获取可用适配器列表
      2. 按名称动态加载/缓存适配器实例
      3. 执行采集任务并记录日志
      4. 主适配器连续失败 ≥ 阈值时自动切换到备用适配器
    """

    def __init__(self, config_path: str = None):
        """
        Args:
            config_path: config.yaml 路径。默认自动查找。
        """
        if config_path is None:
            config_path = self._find_config()

        self.config_path = config_path
        self.config: dict = self._load_config(config_path)

        # data_collector 段
        dc = self.config.get("data_collector", {})
        self.default_adapter: str = dc.get("default_adapter", "zhaobiao")
        self.fallback_adapter: str = dc.get("fallback_adapter", "gd_zbtb")
        self.failure_threshold: int = dc.get("failure_threshold", 3)
        self.auto_fallback: bool = dc.get("auto_fallback", True)

        # 适配器注册表
        self._adapters: Dict[str, dict] = dc.get("adapters", {})
        self._instances: Dict[str, object] = {}          # 缓存实例
        self._failure_counts: Dict[str, int] = {}         # 各适配器连续失败计数
        self._task_log: List[dict] = []                   # 任务执行日志

        self.logger = logging.getLogger("data_collector")

    # ── 配置加载 ──

    @staticmethod
    def _find_config() -> str:
        """自动查找配置文件。"""
        candidates = [
            os.path.join(os.path.dirname(__file__), "adapters", "adapter_config.yaml"),
            os.path.join(os.path.dirname(__file__), "config.yaml"),
        ]
        for p in candidates:
            if os.path.isfile(p):
                return p
        raise FileNotFoundError("找不到 adapter_config.yaml 或 config.yaml")

    @staticmethod
    def _load_config(path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    # ── 适配器动态加载 ──

    def _load_adapter(self, adapter_name: str):
        """
        动态导入模块并实例化适配器。

        配置示例:
            zhaobiao:
              enabled: true
              module: "adapters.zhaobiao_adapter"
              class_name: "ZhaobiaoAdapter"
              config:
                base_url: "https://www.zhaobiao.cn"
                max_pages: 5
        """
        if adapter_name in self._instances:
            return self._instances[adapter_name]

        # 1. 查找配置
        adapter_cfg = self._adapters.get(adapter_name)
        if not adapter_cfg:
            # 回退：在 config 顶层查找
            adapter_cfg = self.config.get(adapter_name, {})

        if not adapter_cfg:
            raise ValueError(f"适配器 '{adapter_name}' 未在配置中找到")

        if not adapter_cfg.get("enabled", True):
            raise RuntimeError(f"适配器 '{adapter_name}' 已在配置中禁用")

        # 2. 动态导入
        module_path = adapter_cfg.get("module", f"adapters.{adapter_name}_adapter")
        class_name = adapter_cfg.get("class_name", self._guess_class_name(adapter_name))

        try:
            mod = importlib.import_module(module_path)
            cls: Type = getattr(mod, class_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(
                f"无法加载适配器 '{adapter_name}': "
                f"module={module_path}, class={class_name} — {e}"
            )

        # 3. 合并配置
        merged_config: dict = {}
        merged_config.update(adapter_cfg.get("config", {}))
        # 顶层键也合并进去（base_url, min_delay 等）
        for key in ("base_url", "min_delay", "max_delay", "max_retries",
                     "timeout", "max_pages", "search_keyword", "search_region",
                     "name"):
            if key in adapter_cfg and key not in merged_config:
                merged_config[key] = adapter_cfg[key]

        # 4. 实例化并缓存
        instance = cls(merged_config)
        self._instances[adapter_name] = instance
        self._failure_counts[adapter_name] = 0

        self.logger.info(f"✅ 适配器已加载: {adapter_name} ({class_name})")
        return instance

    @staticmethod
    def _guess_class_name(name: str) -> str:
        mapping = {
            "zhaobiao": "ZhaobiaoAdapter",
            "gd_zbtb": "GzZbtbAdapter",
            "gd_ygp": "GdYgpAdapter",
            "b2b_10086": "B2b10086Adapter",
            "telecom": "TelecomAdapter",
            "unicom": "UnicomAdapter",
            "bank": "BankAdapter",
        }
        return mapping.get(name, name.title().replace("_", "") + "Adapter")

    # ── 核心采集方法 ──

    def collect(
        self,
        adapter_name: str = None,
        save_to_db: bool = True,
        progress_callback: callable = None,
        **kwargs,
    ) -> List[Dict]:
        """
        执行完整采集流程。

        Args:
            adapter_name: 适配器名称。None 则使用默认适配器。
            save_to_db: 是否自动入库。
            progress_callback: 进度回调函数，接收 (progress_percent, message)。
            **kwargs: 传递给适配器 run() 的额外参数。

        Returns:
            采集到的广告类项目列表。
        """
        if adapter_name is None:
            adapter_name = self.default_adapter

        start = time.time()
        task_entry = {
            "adapter": adapter_name,
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "running",
            "items": 0,
            "elapsed": 0,
            "error": None,
        }

        self.logger.info(f"🕷️ ===== 开始采集: {adapter_name} =====")

        try:
            # 加载适配器
            adapter = self._load_adapter(adapter_name)

            # 设置进度回调（如果提供）
            if progress_callback and hasattr(adapter, 'set_progress_callback'):
                adapter.set_progress_callback(progress_callback)

            # 覆盖 max_pages（如果传入）
            if "max_pages" in kwargs:
                adapter.max_pages = kwargs["max_pages"]

            # 执行采集（传递 kwargs 如 province）
            results = adapter.run(save_to_db=save_to_db, **kwargs)

            # 日期过滤
            date_from = kwargs.get("date_from")
            date_to = kwargs.get("date_to")
            if date_from or date_to:
                filtered = []
                for r in results:
                    pub_date = r.get("publish_date") or ""
                    if pub_date:
                        if date_from and pub_date < date_from:
                            continue
                        if date_to and pub_date > date_to:
                            continue
                    filtered.append(r)
                if len(filtered) < len(results):
                    self.logger.info(f"  日期过滤: {len(results)} → {len(filtered)} 条 ({date_from or ''} ~ {date_to or ''})")
                results = filtered

            elapsed = round(time.time() - start, 1)
            task_entry["status"] = "success"
            task_entry["items"] = len(results)
            task_entry["elapsed"] = elapsed

            # 重置失败计数
            self._failure_counts[adapter_name] = 0

            self.logger.info(
                f"✅ 采集完成: {adapter_name} | "
                f"{len(results)} 条 | 耗时 {elapsed}s"
            )

            return results

        except Exception as e:
            elapsed = round(time.time() - start, 1)
            task_entry["status"] = "failed"
            task_entry["elapsed"] = elapsed
            task_entry["error"] = str(e)[:500]

            # 累加失败计数
            self._failure_counts[adapter_name] = \
                self._failure_counts.get(adapter_name, 0) + 1
            fc = self._failure_counts[adapter_name]

            self.logger.error(
                f"❌ 采集失败: {adapter_name} | "
                f"连续失败 {fc}/{self.failure_threshold} | {e}"
            )

            # 判断是否触发容错切换
            if self._should_fallback(adapter_name, e):
                self.logger.warning(
                    f"⚠️ {adapter_name} 连续失败 {fc} 次，"
                    f"切换至备用适配器 {self.fallback_adapter}"
                )
                # 递归调用，但防止无限循环
                if adapter_name != self.fallback_adapter:
                    return self._fallback_collect(
                        failed_adapter=adapter_name,
                        save_to_db=save_to_db,
                        **kwargs,
                    )

            raise

        finally:
            self._task_log.append(task_entry)

    # ── 容错逻辑 ──

    def _should_fallback(self, adapter_name: str, error: Exception) -> bool:
        """
        判断是否应切换到备用适配器。

        条件:
          1. 自动切换已启用
          2. 当前适配器连续失败 ≥ 阈值
          3. 当前非备用适配器（防止循环）
          4. 错误非致命（如配置错误不切换）
        """
        if not self.auto_fallback:
            return False

        if adapter_name == self.fallback_adapter:
            return False  # 已经是备用，不再切换

        fc = self._failure_counts.get(adapter_name, 0)
        if fc < self.failure_threshold:
            return False

        # 致命错误不切换（如模块不存在、类未找到）
        fatal = isinstance(error, (ImportError, ValueError, RuntimeError))
        if fatal:
            self.logger.warning(f"⚠️ 致命错误，不切换: {error}")
            return False

        return True

    def _fallback_collect(
        self,
        failed_adapter: str,
        save_to_db: bool = True,
        **kwargs,
    ) -> List[Dict]:
        """使用备用适配器执行采集。"""
        self.logger.warning(
            f"🔄 容错切换: {failed_adapter} → {self.fallback_adapter}"
        )
        try:
            results = self.collect(
                adapter_name=self.fallback_adapter,
                save_to_db=save_to_db,
                **kwargs,
            )
            # 备用成功，手动恢复主适配器失败计数（给下次机会）
            self._failure_counts[failed_adapter] = 0
            return results
        except Exception as e:
            self.logger.critical(
                f"💥 备用适配器 {self.fallback_adapter} 也失败了: {e}"
            )
            raise

    # ── 便捷方法 ──

    def collect_all_enabled(self, save_to_db: bool = True, progress_callback: callable = None, category: str = None, **kwargs) -> Dict[str, List[Dict]]:
        """
        使用所有已启用的适配器分别采集。

        Args:
            save_to_db: 是否自动入库。
            progress_callback: 进度回调函数。
            category: 分类过滤 (operator/government)，None=全部。
            **kwargs: 传递给适配器的额外参数。

        Returns:
            {adapter_name: [records]}
        """
        all_results = {}
        enabled_adapters = [(name, cfg) for name, cfg in self._adapters.items() if cfg.get("enabled", True)]
        if category:
            enabled_adapters = [(n, c) for n, c in enabled_adapters if c.get("category") == category]

        for idx, (name, cfg) in enumerate(enabled_adapters):
            # 计算当前适配器在整体进度中的位置
            adapter_start_progress = idx * 100 // len(enabled_adapters)
            adapter_end_progress = (idx + 1) * 100 // len(enabled_adapters)

            try:
                # 为每个适配器创建一个带偏移的进度回调
                def adapter_progress_callback(progress, message):
                    if progress_callback:
                        # 将适配器的进度映射到整体进度范围
                        adjusted_progress = adapter_start_progress + (progress * (adapter_end_progress - adapter_start_progress) // 100)
                        progress_callback(adjusted_progress, f"[{name}] {message}")

                all_results[name] = self.collect(
                    adapter_name=name,
                    save_to_db=save_to_db,
                    progress_callback=adapter_progress_callback,
                    **{k: v for k, v in kwargs.items() if k in ("date_from", "date_to")},
                )
            except Exception as e:
                self.logger.error(f"{name} 采集失败: {e}")
                all_results[name] = []

        return all_results

    def list_adapters(self) -> List[dict]:
        """列出所有已配置的适配器及其状态。"""
        adapters = []
        for name, cfg in self._adapters.items():
            adapters.append({
                "name": name,
                "enabled": cfg.get("enabled", True),
                "class": cfg.get("class_name", self._guess_class_name(name)),
                "failures": self._failure_counts.get(name, 0),
            })
        return adapters

    def get_task_log(self, limit: int = 20) -> List[dict]:
        """获取最近的采集任务日志。"""
        return self._task_log[-limit:]

    def reset_failures(self, adapter_name: str = None):
        """重置失败计数。"""
        if adapter_name:
            self._failure_counts[adapter_name] = 0
        else:
            self._failure_counts.clear()

    # ── 异步包装（供 FastAPI 定时任务使用） ──

    async def collect_async(
        self,
        adapter_name: str = None,
        save_to_db: bool = True,
        **kwargs,
    ) -> List[Dict]:
        """异步包装 collect()，在线程池中运行。"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.collect(adapter_name=adapter_name, save_to_db=save_to_db, **kwargs),
        )

    async def collect_all_enabled_async(self, save_to_db: bool = True) -> Dict[str, List[Dict]]:
        """异步包装 collect_all_enabled()，在线程池中运行。"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.collect_all_enabled(save_to_db=save_to_db),
        )


# ============================================================
# 全局单例
# ============================================================

_collector: Optional[DataCollector] = None


def get_collector(config_path: str = None) -> DataCollector:
    """获取全局 DataCollector 单例。"""
    global _collector
    if _collector is None:
        _collector = DataCollector(config_path)
    return _collector


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    import argparse

    parser = argparse.ArgumentParser(description="标中宝 统一数据采集器")
    parser.add_argument(
        "-a", "--adapter",
        default=None,
        help="指定适配器名称（默认: 配置文件中的 default_adapter）",
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="列出所有适配器",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="不入库（仅打印结果）",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="使用所有已启用适配器采集",
    )
    args = parser.parse_args()

    collector = DataCollector()

    if args.list:
        print("\n📋 已注册适配器:")
        for ad in collector.list_adapters():
            status = "✅ 启用" if ad["enabled"] else "⛔ 禁用"
            print(f"  {ad['name']:15s} {ad['class']:25s} {status}  失败: {ad['failures']}")
        print(f"\n默认: {collector.default_adapter}  备用: {collector.fallback_adapter}")
        sys.exit(0)

    if args.all:
        all_results = collector.collect_all_enabled(save_to_db=not args.no_save)
        total = sum(len(v) for v in all_results.values())
        print(f"\n🎯 总计: {total} 条广告类公告")
    else:
        results = collector.collect(
            adapter_name=args.adapter,
            save_to_db=not args.no_save,
        )
        print(f"\n🎯 {len(results)} 条广告类公告")
        for r in results[:10]:
            print(f"  [{r.get('project_category', '')}] {r['title'][:70]}")
