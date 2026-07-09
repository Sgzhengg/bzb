"""
测试改进后的 b2b 自动刮削器 V2（网络拦截版本）

运行：python backend/test_b2b_v2.py
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.b2b_auto_scraper_v2 import scrape_auto_v2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_auto_scraper_v2():
    """测试网络拦截版本的自动刮削器"""

    # 测试关键词（更通用的关键词）
    test_keywords = [
        "采购",            # 最通用的关键词
        "集团客户",        # 常见项目类型
        "网络",            # 技术相关
    ]

    for keyword in test_keywords:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing Keyword: {keyword}")
        logger.info(f"{'='*60}")

        try:
            result = await scrape_auto_v2(keyword, timeout=30)

            if result:
                logger.info(f"SUCCESS:")
                logger.info(f"  - Method: {result.get('method', 'unknown')}")
                logger.info(f"  - Content Length: {len(result.get('content', ''))}")
                logger.info(f"  - URL: {result.get('url', '')[:80]}")
                logger.info(f"  - Title: {result.get('title', '')[:50]}")

                # 显示内容片段
                content = result.get('content', '')
                if content:
                    logger.info(f"  - Content Preview: {content[:300]}...")

                    # 检查是否包含预算相关关键词
                    budget_keywords = ["预算", "万元", "元", "保证金", "标书费", "限价"]
                    found_budget = any(kw in content for kw in budget_keywords)
                    logger.info(f"  - Contains Budget Info: {found_budget}")

                # 如果成功，可以停止测试更多关键词
                if len(content) > 3000:
                    logger.info("SUCCESS: Extracted detail page content (>3000 chars)")
                    break
            else:
                logger.warning(f"Failed for keyword: {keyword}")

        except Exception as e:
            logger.error(f"Exception during test: {e}")
            import traceback
            traceback.print_exc()

        logger.info("Moving to next keyword...\n")

    logger.info("\nTest completed")


if __name__ == "__main__":
    print("""
    b2b Auto Scraper V2 Test (Network Intercept Version)

    This test will:
    1. Search announcements via queryList API
    2. Intercept luceneSearchList requests and inject queryList results
    3. Click real DOM elements to trigger Vue Router navigation
    4. Extract detail page content

    Please ensure:
    - Edge browser is installed
    - Network connection is available
    - Don't close browser window
    """)

    asyncio.run(test_auto_scraper_v2())