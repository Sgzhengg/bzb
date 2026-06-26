"""
历史中标公告采集 — 入口脚本

用法:
    # 开始采集（支持断点续传）
    python -m app.services.historical_crawler.run

    # 重置断点从头采集
    python -m app.services.historical_crawler.run --reset

    # 单元测试
    python -m app.services.historical_crawler.run --test
"""

import os
import sys
import asyncio
import logging
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def main():
    parser = argparse.ArgumentParser(description="标中宝 — 历史中标公告批量采集")
    parser.add_argument("--reset", action="store_true", help="重置断点，从头采集")
    parser.add_argument("--test", action="store_true", help="运行单元测试")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    if args.test:
        logger.info("🧪 运行单元测试...")
        from app.services.historical_crawler.test_historical import run_all_tests
        success = run_all_tests()
        sys.exit(0 if success else 1)
        return

    from app.services.historical_crawler.config import CHECKPOINT_DIR, CHECKPOINT_FILE
    from app.services.historical_crawler.collector import HistoricalAwardCollector

    if args.reset:
        checkpoint_path = os.path.join(CHECKPOINT_DIR, CHECKPOINT_FILE)
        if os.path.exists(checkpoint_path):
            os.remove(checkpoint_path)
            logger.info("🔄 断点已重置")

    collector = HistoricalAwardCollector()
    results = await collector.run()
    logger.info(f"\n✅ 采集完成！共获取 {len(results)} 条历史中标记录")


if __name__ == "__main__":
    asyncio.run(main())
