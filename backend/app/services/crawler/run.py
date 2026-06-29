"""
标中宝爬虫 — 入口脚本

用法:
    # 标准模式（列表页翻页）
    python -m app.services.crawler.run

    # 搜索模式
    python -m app.services.crawler.run --search

    # 限制翻页数
    python -m app.services.crawler.run --max-pages 5

    # 单元测试模式（使用 Mock HTML）
    python -m app.services.crawler.run --test
"""

import sys
import os
import asyncio
import logging
import argparse

# 确保包路径正确
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.crawler.pipeline import BiddingCrawlerPipeline


def setup_logging(verbose: bool = False):
    """配置日志。"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def main():
    parser = argparse.ArgumentParser(description="标中宝 — 招标公告爬虫")
    parser.add_argument(
        "--search", action="store_true",
        help="使用搜索模式（搜索'广东移动'+'广告'）",
    )
    parser.add_argument(
        "--max-pages", type=int, default=3,
        help="最大翻页数（默认 3）",
    )
    parser.add_argument(
        "--test", action="store_true",
        help="运行单元测试（使用 Mock 数据）",
    )
    parser.add_argument(
        "--ai", action="store_true",
        help="使用 AI 增强模式（Crawl4AI Chromium）抓取详情页",
    )
    parser.add_argument(
        "--ai-urls", type=str, nargs="*",
        help="AI 直采模式：直接指定详情 URL 列表",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="详细日志输出",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    if args.test:
        logger.info("🧪 运行单元测试模式...")
        from app.services.crawler.test_crawler import run_all_tests
        run_all_tests()
        return

    logger.info(f"配置: max_pages={args.max_pages}, search={args.search}, ai={args.ai}")

    pipeline = BiddingCrawlerPipeline()
    results = await pipeline.run(
        max_pages=args.max_pages,
        use_search=args.search,
        use_ai=args.ai,
        ai_detail_urls=args.ai_urls,
    )

    logger.info(f"✅ 采集完成，共获取 {len(results)} 条广告类招标项目")


if __name__ == "__main__":
    asyncio.run(main())
