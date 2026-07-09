"""
测试改进后的 b2b 自动刮削器

运行：python backend/test_b2b_auto.py
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.b2b_auto_scraper import scrape_auto
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_auto_scraper():
    """Test auto scraper functionality"""

    # Test keywords (using more general terms that likely exist)
    test_keywords = [
        "集团客户",        # More generic keyword
        "广告宣传",        # Common project type
        "网络优化",        # Technical project
        "采购"            # Most generic keyword
    ]

    for keyword in test_keywords:
        logger.info(f"\n{'='*60}")
        logger.info(f"Test Keyword: {keyword}")
        logger.info(f"{'='*60}")

        try:
            result = await scrape_auto(keyword, timeout=30)

            if result:
                logger.info(f"Success:")
                logger.info(f"  - Method: {result.get('method', 'unknown')}")
                logger.info(f"  - Content Length: {len(result.get('content', ''))}")
                logger.info(f"  - URL: {result.get('url', '')[:80]}")
                logger.info(f"  - Title: {result.get('title', '')[:50]}")

                # Show content preview
                content = result.get('content', '')
                if content:
                    logger.info(f"  - Content Preview: {content[:200]}...")

                # If successful, stop testing more keywords
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
    b2b Auto Scraper Test

    This test will:
    1. Search announcements via queryList API
    2. Open Edge browser
    3. Try auto navigation to detail page
    4. Extract announcement content

    Please ensure:
    - Edge browser is installed
    - Network connection is available
    - Don't close browser window if manual operation needed
    """)

    asyncio.run(test_auto_scraper())