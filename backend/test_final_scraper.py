"""
测试最终优化的 b2b 刮削器

运行：python backend/test_final_scraper.py
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.b2b_scraper_final import scrape_from_announcement_title, _extract_smart_keyword
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_final_scraper():
    """测试最终优化的刮削器"""

    # 测试公告标题（实际从数据库中的例子）
    test_titles = [
        "中国移动通信集团广东有限公司中山分公司2026年至2028年集团客户活动公开询比采购项目",
        "中国移动广东公司深圳分公司2025-2027年广告宣传服务采购项目",
        "中国移动通信集团广东有限公司东莞分公司网络优化服务项目",
    ]

    for i, title in enumerate(test_titles, 1):
        logger.info(f"\n{'='*70}")
        logger.info(f"Test {i}/{len(test_titles)}")
        logger.info(f"{'='*70}")
        logger.info(f"公告标题: {title[:60]}...")

        # 1. 测试关键词提取
        keyword = _extract_smart_keyword(title)
        logger.info(f"提取关键词: {keyword}")

        # 2. 执行刮削
        logger.info(f"启动刮削流程...")

        try:
            result = await scrape_from_announcement_title(title, timeout=120)

            if result:
                logger.info(f"✅ 刮削成功:")
                logger.info(f"  - 方法: {result.get('method', 'unknown')}")
                logger.info(f"  - 内容长度: {len(result.get('content', ''))}")
                logger.info(f"  - URL: {result.get('url', '')[:80]}")
                logger.info(f"  - 标题: {result.get('title', '')[:50]}")

                # 显示内容片段
                content = result.get('content', '')
                if content:
                    logger.info(f"  - 内容预览: {content[:300]}...")

                    # 检查是否包含预算相关信息
                    budget_keywords = ["预算", "万元", "元", "保证金", "标书费"]
                    found_budget = any(kw in content for kw in budget_keywords)
                    logger.info(f"  - 包含预算信息: {found_budget}")

                # 如果成功提取到长内容，可以停止测试
                if len(content) > 3000:
                    logger.info("✅ 成功提取到详情页级别内容 (>3000 字符)")
                    logger.info("🎯 测试成功！可以停止测试其他项目")
                    break
            else:
                logger.warning(f"❌ 刮削失败（用户取消或超时）")

        except Exception as e:
            logger.error(f"❌ 测试异常: {e}")
            import traceback
            traceback.print_exc()

        # 如果成功提取到长内容，停止测试
        if result and len(result.get('content', '')) > 3000:
            logger.info("SUCCESS: Extracted detail-level content (>3000 chars)")
            logger.info("Test successful! Stopping further tests.")
            break

        # 询问是否继续测试下一个
        if i < len(test_titles):
            try:
                user_input = input("\nContinue to next announcement? (y/n): ")
                if user_input.lower() != 'y':
                    break
            except EOFError:
                # 非交互模式，自动继续
                pass

    logger.info(f"\n{'='*70}")
    logger.info("测试完成")
    logger.info(f"{'='*70}")


if __name__ == "__main__":
    print("""
    b2b Final Scraper Test - Optimized Manual Assisted Mode

    This test will:
    1. Extract smart keywords from announcement titles
    2. Pre-validate targets via API
    3. Launch optimized browser workflow
    4. Provide enhanced user guidance
    5. Extract detail page content with multi-detection

    Please ensure:
    - Edge browser is installed
    - Network connection is available
    - Follow the on-screen instructions
    """)

    asyncio.run(test_final_scraper())