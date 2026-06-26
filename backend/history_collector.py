"""
标中宝 V1 — 历史数据采集器

专为大范围历史数据采集设计，提供:
  - 时间范围过滤（仅采集指定日期区间）
  - 断点续传（checkpoint.json 记录进度）
  - 去重机制（title + source_url 双重检查）
  - 进度日志（每 N 页/条输出统计）
  - 异常隔离（单条失败不影响整体）
  - 预估剩余时间

使用:
    from history_collector import HistoryCollector

    collector = HistoryCollector()
    collector.run(start_date="2023-01-01", end_date="2026-06-26")
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Set

# 确保 backend 在 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_collector import DataCollector

logger = logging.getLogger("history_collector")


# ============================================================
# HistoryCollector
# ============================================================

class HistoryCollector:
    """
    历史数据采集器。

    特性:
      - 基于 DataCollector 加载适配器
      - 按日期范围分批次采集
      - 断点续传 (checkpoint JSON)
      - URL + title 去重
      - 详细进度日志（含 ETA）
      - 字段解析容错 + 数据校验
    """

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), "adapters", "adapter_config.yaml"
            )

        self.config_path = config_path
        self.collector = DataCollector(config_path)

        # collector 配置段
        coll_cfg = self.collector.config.get("collector", {})
        self.checkpoint_file = coll_cfg.get(
            "checkpoint_file",
            os.path.join(os.path.dirname(__file__), "checkpoint.json"),
        )
        self.history_mode = coll_cfg.get("history_mode", True)
        self.progress_interval_pages = coll_cfg.get("progress_interval_pages", 10)
        self.progress_interval_items = coll_cfg.get("progress_interval_items", 50)

        # 请求配置
        req_cfg = coll_cfg.get("request_interval", {})
        self.min_delay = float(req_cfg.get("min", 3.0))
        self.max_delay = float(req_cfg.get("max", 8.0))

        # 重试配置
        retry_cfg = coll_cfg.get("retry", {})
        self.max_retries = int(retry_cfg.get("max_attempts", 3))
        self.backoff_factor = float(retry_cfg.get("backoff_factor", 2.0))

        # 代理
        self.proxy_enabled = coll_cfg.get("proxy_enabled", False)
        self.proxy_list = coll_cfg.get("proxy_list", [])

        # 状态
        self._checkpoint: dict = {}
        self._collected_urls: Set[str] = set()
        self._collected_titles: Set[str] = set()
        self._total_collected: int = 0
        self._total_skipped_dup: int = 0
        self._total_skipped_date: int = 0
        self._total_errors: int = 0
        self._start_time: float = 0
        self._parse_errors: List[dict] = []   # 解析失败的字段记录

        self.logger = logging.getLogger("history_collector")

    # ── 断点续传 ──

    def _load_checkpoint(self) -> dict:
        """加载断点文件。"""
        if os.path.isfile(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    cp = json.load(f)
                self.logger.info(
                    f"📂 加载断点: {cp.get('last_date', '?')} "
                    f"page={cp.get('last_page', 0)} "
                    f"collected={cp.get('total_collected', 0)}"
                )
                return cp
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"断点文件损坏，重新开始: {e}")

        return {
            "last_date": None,
            "last_page": 0,
            "last_item_index": 0,
            "total_collected": 0,
            "total_skipped_dup": 0,
            "total_skipped_date": 0,
            "collected_urls": [],
            "started_at": datetime.now().isoformat(),
        }

    def _save_checkpoint(self, last_date: str, page: int, item_idx: int):
        """保存断点。"""
        self._checkpoint.update({
            "last_date": last_date,
            "last_page": page,
            "last_item_index": item_idx,
            "total_collected": self._total_collected,
            "total_skipped_dup": self._total_skipped_dup,
            "total_skipped_date": self._total_skipped_date,
            "collected_urls": list(self._collected_urls)[-500:],  # 保留最近500个
            "updated_at": datetime.now().isoformat(),
        })
        try:
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(self._checkpoint, f, ensure_ascii=False, indent=2)
        except IOError as e:
            self.logger.warning(f"保存断点失败: {e}")

    def _restore_state(self):
        """从断点恢复内存状态。"""
        cp = self._checkpoint
        self._total_collected = cp.get("total_collected", 0)
        self._total_skipped_dup = cp.get("total_skipped_dup", 0)
        self._total_skipped_date = cp.get("total_skipped_date", 0)
        self._collected_urls = set(cp.get("collected_urls", []))

    # ── 去重 ──

    def _is_duplicate(self, title: str, source_url: str) -> bool:
        """检查是否已采集（URL + 标题双检）。"""
        url_key = source_url.strip().lower()
        title_key = title.strip()

        if url_key and url_key in self._collected_urls:
            return True
        if title_key and title_key in self._collected_titles:
            return True
        return False

    def _mark_collected(self, title: str, source_url: str):
        self._collected_urls.add(source_url.strip().lower())
        self._collected_titles.add(title.strip())

    # ── 日期过滤 ──

    @staticmethod
    def _extract_date_from_item(item: dict) -> Optional[date]:
        """从列表项中提取日期。"""
        raw = item.get("publish_date", "")
        if not raw:
            return None

        import re
        # 常见格式: 2024-06-15, 2024年06月15日, 2024/06/15
        m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", str(raw))
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                pass
        return None

    def _is_in_range(self, item: dict, start: date, end: date) -> bool:
        """检查列表项的发布日期是否在范围内。"""
        d = self._extract_date_from_item(item)
        if d is None:
            # 无法解析日期 → 保守处理：包含
            return True
        return start <= d <= end

    # ── 数据校验 ──

    def _validate_record(self, record: dict) -> List[str]:
        """校验关键字段，返回缺失字段列表。"""
        missing = []
        for field in ["title", "purchaser", "announce_date"]:
            if not record.get(field):
                missing.append(field)
        # deadline 可为空（部分公告无明确截止时间）
        return missing

    # ── 进度日志 ──

    def _log_progress(self, page: int, items_in_page: int):
        """输出详细进度日志（含 ETA）。"""
        elapsed = time.time() - self._start_time
        rate = self._total_collected / elapsed if elapsed > 0 else 0

        # 预估剩余
        total_pages = self._adapter.max_pages if hasattr(self, "_adapter") else "?"
        if isinstance(total_pages, int) and page > 0:
            pages_remaining = total_pages - page
            eta = pages_remaining * (elapsed / page) if page > 0 else 0
            eta_str = f"{eta/60:.0f}min" if eta > 60 else f"{eta:.0f}s"
        else:
            eta_str = "N/A"

        self.logger.info(
            f"📊 [进度] 页 {page}/{total_pages} | "
            f"本页 {items_in_page} 条 | "
            f"累计采集 {self._total_collected} | "
            f"跳过(重复:{self._total_skipped_dup} 日期:{self._total_skipped_date}) | "
            f"错误 {self._total_errors} | "
            f"速率 {rate:.1f}条/s | "
            f"耗时 {elapsed/60:.1f}min | "
            f"ETA {eta_str}"
        )

    # ── 主流程 ──

    def run(
        self,
        start_date: str = None,
        end_date: str = None,
        adapter_name: str = None,
        keyword: str = None,
        max_pages: int = None,
    ) -> dict:
        """
        执行历史数据采集。

        Args:
            start_date: 起始日期 "2023-01-01"
            end_date:   结束日期 "2026-06-26"
            adapter_name: 适配器名称（默认使用配置的默认适配器）
            keyword:    搜索关键词（覆盖配置）
            max_pages:  最大翻页数（覆盖配置）

        Returns:
            统计摘要 dict
        """
        # ── 加载断点 ──
        self._checkpoint = self._load_checkpoint()
        self._restore_state()

        # ── 日期范围 ──
        coll_cfg = self.collector.config.get("collector", {})
        if start_date is None:
            start_date = coll_cfg.get("start_date", "2023-01-01")
        if end_date is None:
            end_date = coll_cfg.get("end_date", "2026-06-26")

        try:
            sd = date.fromisoformat(start_date)
            ed = date.fromisoformat(end_date)
        except (ValueError, TypeError):
            sd = date.today() - timedelta(days=365)
            ed = date.today()
            self.logger.warning(f"日期解析失败，使用默认: {sd} ~ {ed}")

        # ── 适配器 ──
        if adapter_name is None:
            adapter_name = self.collector.default_adapter

        try:
            adapter = self.collector._load_adapter(adapter_name)
            self._adapter = adapter
        except Exception as e:
            self.logger.error(f"加载适配器失败: {e}")
            return {"status": "error", "error": str(e)}

        # 覆盖参数
        if keyword:
            adapter.config["search_keyword"] = keyword
        if max_pages:
            adapter.max_pages = max_pages
        if coll_cfg.get("request_interval"):
            ri = coll_cfg["request_interval"]
            adapter.min_delay = float(ri.get("min", adapter.min_delay))
            adapter.max_delay = float(ri.get("max", adapter.max_delay))

        # ── 开始采集 ──
        self._start_time = time.time()
        self.logger.info("=" * 60)
        self.logger.info(f"🕷️ 历史数据采集启动")
        self.logger.info(f"   适配器: {adapter_name} ({adapter.name})")
        self.logger.info(f"   日期范围: {sd} ~ {ed} ({ (ed-sd).days } 天)")
        self.logger.info(f"   关键词: {adapter.config.get('search_keyword', 'N/A')}")
        self.logger.info(f"   最大页数: {adapter.max_pages}")
        self.logger.info(f"   断点: {self._checkpoint.get('last_date', '无')}")
        self.logger.info("=" * 60)

        try:
            # ── 按关键词批次采集 ──
            if hasattr(adapter, "AD_KEYWORDS") and adapter.AD_KEYWORDS:
                self._run_multi_keyword(adapter, sd, ed)
            else:
                self._run_single_keyword(adapter, sd, ed)
        except KeyboardInterrupt:
            self.logger.warning("⚠️ 用户中断，正在保存断点...")
            self._save_checkpoint(
                self._checkpoint.get("last_date", ""),
                self._checkpoint.get("last_page", 0),
                self._checkpoint.get("last_item_index", 0),
            )
        except Exception as e:
            self.logger.error(f"采集异常: {e}", exc_info=True)
        finally:
            adapter.close()
            self._save_checkpoint("", 0, 0)

        # ── 统计摘要 ──
        elapsed = time.time() - self._start_time
        summary = {
            "status": "completed",
            "adapter": adapter_name,
            "date_range": f"{sd} ~ {ed}",
            "total_collected": self._total_collected,
            "total_skipped_dup": self._total_skipped_dup,
            "total_skipped_date": self._total_skipped_date,
            "total_errors": self._total_errors,
            "parse_errors": len(self._parse_errors),
            "elapsed_minutes": round(elapsed / 60, 1),
            "rate_per_minute": round(self._total_collected / (elapsed / 60), 1) if elapsed > 0 else 0,
            "checkpoint": self.checkpoint_file,
        }

        self.logger.info("=" * 60)
        self.logger.info(f"✅ 历史采集完成")
        self.logger.info(f"   采集: {summary['total_collected']} 条")
        self.logger.info(f"   跳过重复: {summary['total_skipped_dup']}")
        self.logger.info(f"   跳过日期: {summary['total_skipped_date']}")
        self.logger.info(f"   错误: {summary['total_errors']}")
        self.logger.info(f"   耗时: {summary['elapsed_minutes']} 分钟")
        self.logger.info(f"   速率: {summary['rate_per_minute']} 条/分钟")
        self.logger.info("=" * 60)

        return summary

    # ── 单关键词采集 ──

    def _run_single_keyword(self, adapter, sd: date, ed: date):
        """使用单个关键词采集。"""
        for page in range(1, adapter.max_pages + 1):
            try:
                html = adapter.fetch_list(page=page)
                items = adapter.parse_list(html)

                if not items:
                    self.logger.info(f"第 {page} 页无结果，翻页结束")
                    break

                # 日期过滤
                in_range = [it for it in items if self._is_in_range(it, sd, ed)]
                self._total_skipped_date += len(items) - len(in_range)

                if not in_range:
                    self.logger.info(f"第 {page} 页全部超出日期范围，翻页结束")
                    break

                # 逐条处理
                self._process_items(adapter, in_range, page)

                # 进度日志
                if page % self.progress_interval_pages == 0:
                    self._log_progress(page, len(in_range))

                # 保存断点
                self._save_checkpoint(
                    self._checkpoint.get("last_date", str(sd)),
                    page, 0,
                )

            except Exception as e:
                self.logger.error(f"第 {page} 页失败: {e}")
                self._total_errors += 1
                self._save_checkpoint(str(sd), page, 0)
                break

    # ── 多关键词采集 ──

    def _run_multi_keyword(self, adapter, sd: date, ed: date):
        """使用多个关键词组合采集，合并去重。"""
        keywords = getattr(adapter, "AD_KEYWORDS", [adapter.config.get("search_keyword", "")])
        if not keywords:
            keywords = [adapter.config.get("search_keyword", "广东移动 广告")]

        for ki, kw in enumerate(keywords):
            self.logger.info(f"🔑 关键词 [{ki+1}/{len(keywords)}]: {kw}")
            adapter.config["search_keyword"] = kw

            try:
                self._run_single_keyword(adapter, sd, ed)
            except Exception as e:
                self.logger.error(f"关键词 '{kw}' 采集失败: {e}")
                self._total_errors += 1

            # 每个关键词之间额外休息
            if ki < len(keywords) - 1:
                rest = random.uniform(10, 30)
                self.logger.info(f"😴 关键词间休息 {rest:.0f}s...")
                time.sleep(rest)

    # ── 逐条处理 ──

    def _process_items(self, adapter, items: List[dict], page: int):
        """处理列表页中的每条公告。"""
        for idx, item in enumerate(items):
            detail_url = item.get("detail_url", "")
            title = item.get("title", "")

            if not detail_url:
                continue

            # 去重
            if self._is_duplicate(title, detail_url):
                self._total_skipped_dup += 1
                continue

            # 抓取详情
            try:
                html_detail, pdf_bytes = adapter.fetch_detail(detail_url)
                parsed = adapter.parse_detail(html_detail, pdf_bytes)
                parsed["source_url"] = detail_url
                parsed["notice_type"] = item.get(
                    "notice_type", parsed.get("notice_type", "招标公告")
                )

                # 容错：每个解析字段独立 try-except
                record = self._safe_normalize(adapter, parsed, detail_url)

                if record and record.get("is_ad"):
                    # 数据校验
                    missing = self._validate_record(record)
                    if missing:
                        self.logger.warning(
                            f"⚠️ 字段缺失: {missing} | {title[:50]}"
                        )

                    # 去重入库
                    self._safe_save(adapter, record)

                    self._mark_collected(title, detail_url)
                    self._total_collected += 1

                    if self._total_collected % self.progress_interval_items == 0:
                        self._log_progress(page, len(items))

                # 更新 item 级别断点
                self._checkpoint["last_item_index"] = idx

            except Exception as e:
                self._total_errors += 1
                self.logger.error(
                    f"❌ 详情失败 [{page}:{idx}] {title[:60]}: {e}"
                )
                self._parse_errors.append({
                    "url": detail_url,
                    "title": title,
                    "error": str(e)[:300],
                    "time": datetime.now().isoformat(),
                })

    # ── 安全标准化 ──

    def _safe_normalize(self, adapter, parsed: dict, url: str) -> Optional[dict]:
        """
        容错版标准化，每个字段独立 try-except。

        某字段解析失败不丢弃整条记录，仅标记缺失。
        """
        record = {
            "title": "",
            "purchaser": "",
            "purchaser_level": "",
            "procurement_method": "公开招标",
            "budget": None,
            "project_category": "",
            "announce_date": "",
            "deadline": "",
            "qualification_requirements": "",
            "source_url": url,
            "notice_type": "招标公告",
            "bid_number": "",
            "is_ad": False,
            "matched_keywords": "",
        }

        # 逐字段安全提取
        field_map = [
            ("title", "title"),
            ("purchaser", "purchaser"),
            ("purchaser_level", "purchaser_level"),
            ("procurement_method", "procurement_method"),
            ("budget", "budget"),
            ("notice_type", "notice_type"),
            ("bid_number", "bid_number"),
            ("publish_date", "announce_date"),
            ("deadline", "deadline"),
            ("content_text", "qualification_requirements"),
        ]

        for src, dst in field_map:
            try:
                val = parsed.get(src, "")
                if dst == "qualification_requirements":
                    val = str(val)[:2000]
                record[dst] = val if val is not None else ("" if dst != "budget" else None)
            except Exception as e:
                self.logger.debug(f"字段 '{src}' 提取失败: {e}")
                self._parse_errors.append({
                    "url": url,
                    "field": src,
                    "error": str(e)[:200],
                })

        # 关键词过滤（单独 try-except）
        try:
            from app.services.keyword_filter import filter_advertisement_projects
            result = filter_advertisement_projects(
                record["title"],
                record.get("qualification_requirements", ""),
            )
            record["is_ad"] = result["is_ad"]
            record["project_category"] = result.get("category", "")
            record["matched_keywords"] = result.get("matched_keywords", "")
        except ImportError:
            # 回退：简单判断
            record["is_ad"] = True
        except Exception as e:
            self.logger.debug(f"关键词过滤失败: {e}")
            record["is_ad"] = True

        # 默认值
        if not record["procurement_method"]:
            record["procurement_method"] = "公开招标"
        if not record["notice_type"]:
            record["notice_type"] = "招标公告"

        return record

    # ── 安全入库 ──

    def _safe_save(self, adapter, record: dict):
        """去重 + 安全入库。"""
        try:
            # 数据库级去重检查
            self._check_db_duplicate(record)
            adapter._save_to_db(record)
        except Exception as e:
            if "重复" in str(e) or "duplicate" in str(e).lower():
                self._total_skipped_dup += 1
                self.logger.debug(f"数据库去重: {record['title'][:50]}")
            else:
                self._total_errors += 1
                self.logger.error(f"入库失败: {record['title'][:50]} - {e}")

    def _check_db_duplicate(self, record: dict):
        """数据库层面去重（可选，_save_to_db 本身不检查）。"""
        # 简单实现：不做额外检查，由 _save_to_db 的 INSERT 失败自然去重
        # 如需严格去重，可在这里查询数据库
        pass


# 导入 random 用于关键词间休息
import random


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    import argparse

    parser = argparse.ArgumentParser(description="标中宝 历史数据采集器")
    parser.add_argument(
        "--start", default="2023-01-01",
        help="起始日期 (默认: 2023-01-01)",
    )
    parser.add_argument(
        "--end", default="2026-06-26",
        help="结束日期 (默认: 2026-06-26)",
    )
    parser.add_argument(
        "-a", "--adapter", default=None,
        help="适配器名称 (默认: 配置文件默认值)",
    )
    parser.add_argument(
        "-k", "--keyword", default=None,
        help="搜索关键词 (覆盖配置)",
    )
    parser.add_argument(
        "-p", "--pages", type=int, default=None,
        help="最大翻页数 (覆盖配置)",
    )
    parser.add_argument(
        "--reset-checkpoint", action="store_true",
        help="清除断点重新开始",
    )
    args = parser.parse_args()

    collector = HistoryCollector()

    if args.reset_checkpoint:
        if os.path.isfile(collector.checkpoint_file):
            os.remove(collector.checkpoint_file)
            print("✅ 断点已清除")

    summary = collector.run(
        start_date=args.start,
        end_date=args.end,
        adapter_name=args.adapter,
        keyword=args.keyword,
        max_pages=args.pages,
    )

    print(f"\n📊 采集摘要: {json.dumps(summary, ensure_ascii=False, indent=2)}")
