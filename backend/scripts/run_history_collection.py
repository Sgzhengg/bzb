#!/usr/bin/env python
"""
标中宝 V1 — 历史数据采集启动脚本

用途:
  在部署到 Zeabur 平台前，通过此脚本采集 2023-2026 年的广东移动广告招标历史数据。

使用方法:

  # 基础用法（使用默认配置）
  python scripts/run_history_collection.py

  # 指定日期范围
  python scripts/run_history_collection.py --start 2024-01-01 --end 2024-12-31

  # 测试模式：仅采集少量数据验证流程
  python scripts/run_history_collection.py --start 2026-06-01 --end 2026-06-26 --pages 3

  # 清除断点重新开始
  python scripts/run_history_collection.py --reset-checkpoint

  # 使用备用适配器
  python scripts/run_history_collection.py -a gd_zbtb

前置条件:
  1. Python 3.11+
  2. 已安装依赖: pip install httpx beautifulsoup4 lxml pyyaml
  3. config.yaml 配置正确（default_adapter, collector 段）
  4. 网络可访问目标网站

输出:
  - checkpoint.json: 采集进度断点（支持中断恢复）
  - 控制台日志: 详细进度 + 预估剩余时间
  - 数据库: 采集的公告数据（需数据库可用）
"""

import os
import sys
import logging
import argparse

# 确保 backend 在 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from history_collector import HistoryCollector


def setup_logging():
    """配置日志：同时输出到控制台和文件。"""
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(
        log_dir,
        f"history_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )

    # 降低第三方库日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return log_file


def main():
    parser = argparse.ArgumentParser(
        description="标中宝 V1 — 历史数据采集脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 全量采集（2023-2026）
  python scripts/run_history_collection.py

  # 测试模式
  python scripts/run_history_collection.py --start 2026-06-01 --end 2026-06-26 --pages 3

  # 清除断点重新开始
  python scripts/run_history_collection.py --reset-checkpoint
        """,
    )
    parser.add_argument(
        "--start", type=str, default="2023-01-01",
        help="起始日期 YYYY-MM-DD (默认: 2023-01-01)",
    )
    parser.add_argument(
        "--end", type=str, default="2026-06-26",
        help="结束日期 YYYY-MM-DD (默认: 2026-06-26)",
    )
    parser.add_argument(
        "-a", "--adapter", type=str, default=None,
        help="适配器名称 (默认: 配置文件 data_collector.default_adapter)",
    )
    parser.add_argument(
        "-k", "--keyword", type=str, default=None,
        help="搜索关键词 (覆盖默认的广东移动广告类关键词)",
    )
    parser.add_argument(
        "-p", "--pages", type=int, default=None,
        help="最大翻页数 (默认: 配置文件中的 max_pages)",
    )
    parser.add_argument(
        "--reset-checkpoint", action="store_true",
        help="清除断点文件，强制从头开始采集",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="试运行：仅显示配置，不实际采集",
    )
    parser.add_argument(
        "--no-save", action="store_true",
        help="不入库（仅打印采集结果，用于测试）",
    )

    args = parser.parse_args()

    # 日志
    log_file = setup_logging()
    logger = logging.getLogger("run_history")

    logger.info("=" * 60)
    logger.info("  标中宝 V1 — 历史数据采集脚本")
    logger.info("=" * 60)
    logger.info(f"  日志文件: {log_file}")
    logger.info(f"  日期范围: {args.start} ~ {args.end}")
    if args.adapter:
        logger.info(f"  适配器:   {args.adapter}")
    if args.keyword:
        logger.info(f"  关键词:   {args.keyword}")
    if args.pages:
        logger.info(f"  最大页数: {args.pages}")
    logger.info(f"  试运行:   {'是' if args.dry_run else '否'}")
    logger.info("=" * 60)

    if args.dry_run:
        collector = HistoryCollector()
        logger.info(f"\n📋 配置摘要:")
        logger.info(f"  默认适配器: {collector.collector.default_adapter}")
        logger.info(f"  备用适配器: {collector.collector.fallback_adapter}")
        logger.info(f"  断点文件:   {collector.checkpoint_file}")
        logger.info(f"  可用适配器: {collector.collector.list_adapters()}")
        logger.info("\n✅ 试运行完成，未实际采集")
        return

    # 清除断点
    if args.reset_checkpoint:
        collector = HistoryCollector()
        if os.path.isfile(collector.checkpoint_file):
            os.remove(collector.checkpoint_file)
            logger.info("✅ 断点已清除")
        # 重建以加载新状态
        collector = HistoryCollector()
    else:
        collector = HistoryCollector()

    # 执行采集
    try:
        summary = collector.run(
            start_date=args.start,
            end_date=args.end,
            adapter_name=args.adapter,
            keyword=args.keyword,
            max_pages=args.pages,
        )

        logger.info(f"\n📊 最终统计:")
        logger.info(f"  状态:       {summary.get('status', 'unknown')}")
        logger.info(f"  采集:       {summary.get('total_collected', 0)} 条")
        logger.info(f"  跳过重复:   {summary.get('total_skipped_dup', 0)}")
        logger.info(f"  跳过日期:   {summary.get('total_skipped_date', 0)}")
        logger.info(f"  错误:       {summary.get('total_errors', 0)}")
        logger.info(f"  耗时:       {summary.get('elapsed_minutes', 0)} 分钟")
        logger.info(f"  速率:       {summary.get('rate_per_minute', 0)} 条/分钟")

        if summary.get("parse_errors", 0) > 0:
            logger.warning(f"  ⚠️ 解析错误: {summary['parse_errors']} 个字段，请检查日志")

    except KeyboardInterrupt:
        logger.warning("\n⚠️ 用户中断。断点已保存，重新运行将从断点继续。")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n💥 采集异常: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
