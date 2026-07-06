"""
标中宝 — zhaobiao.cn 广东移动广告招标爬虫

功能：从 www.zhaobiao.cn 爬取 2026年6月15日以来的广东移动广告类招标数据

使用：
    cd backend
    python crawl_gd_mobile_ads.py
"""
import sys
import os
import logging
from datetime import datetime, date
from typing import List, Dict

# 确保 backend 在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters.zhaobiao_adapter import ZhaobiaoAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("crawl_gd_mobile")


def filter_by_date(items: List[Dict], since: date) -> List[Dict]:
    """过滤2026-06-15之后的招标"""
    filtered = []
    for item in items:
        date_str = item.get("publish_date", "")
        if not date_str:
            # 无法解析日期的保留
            filtered.append(item)
            continue
        try:
            # 尝试多种日期格式
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m-%d", "%m月%d日"]:
                try:
                    d = datetime.strptime(date_str.strip(), fmt).date()
                    if fmt in ("%m-%d", "%m月%d日"):
                        d = d.replace(year=since.year)
                    if d >= since:
                        filtered.append(item)
                    break
                except ValueError:
                    continue
        except Exception:
            filtered.append(item)
    return filtered


def save_to_db(items: List[Dict]):
    """将采集结果保存到数据库"""
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.announcement import Announcement
        import asyncio

        async def _save():
            count = 0
            async with AsyncSessionLocal() as session:
                for item in items:
                    # 检查是否已存在 (按 source_url 去重)
                    if not item.get("detail_url"):
                        continue

                    from sqlalchemy import select
                    existing = await session.execute(
                        select(Announcement).where(
                            Announcement.source_url == item["detail_url"]
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                    ann = Announcement(
                        title=item.get("title", ""),
                        source_url=item.get("detail_url", ""),
                        announce_date=item.get("publish_date"),
                        industry=item.get("industry", "中国移动通信集团广东有限公司"),
                        province=item.get("province", "广东"),
                        city=item.get("city", ""),
                        project_category=item.get("category", ""),
                        notice_type=item.get("notice_type", ""),
                        budget=item.get("budget"),
                    )
                    session.add(ann)
                    count += 1

                await session.commit()
            return count

        count = asyncio.run(_save())
        logger.info(f"已保存 {count} 条新记录到数据库")
        return count
    except Exception as e:
        logger.error(f"保存数据库失败: {e}")
        return 0


def main():
    since_date = date(2026, 6, 15)
    logger.info(f"开始爬取 zhaobiao.cn，关键词: 广东移动广告，日期范围: {since_date} 至今")

    config = {
        "search_keyword": "广东移动 广告",
        "max_pages": 5,
        "min_delay": 3.0,
        "max_delay": 6.0,
        "max_retries": 3,
        "timeout": 30,
    }

    adapter = ZhaobiaoAdapter(config)
    all_items = []

    for page in range(1, config["max_pages"] + 1):
        logger.info(f"--- 第 {page} 页 ---")
        try:
            html = adapter.fetch_list(page=page)
            if not html:
                logger.warning(f"第 {page} 页获取失败，停止翻页")
                break

            items = adapter.parse_list(html)
            if not items:
                logger.info(f"第 {page} 页无结果，停止翻页")
                break

            # 过滤日期
            filtered = filter_by_date(items, since_date)
            logger.info(f"第 {page} 页: 解析 {len(items)} 条, 日期过滤后 {len(filtered)} 条")

            # 抓取详情页
            for item in filtered[:20]:  # 每页最多20条详情
                try:
                    detail_url = item.get("detail_url")
                    if detail_url:
                        logger.info(f"  抓取详情: {item['title'][:40]}...")
                        detail = adapter.fetch_detail(detail_url)
                        if detail:
                            item.update(detail)
                except Exception as e:
                    logger.warning(f"  详情抓取失败: {e}")

            all_items.extend(filtered)

        except Exception as e:
            logger.error(f"第 {page} 页异常: {e}")
            break

    logger.info(f"共采集 {len(all_items)} 条招标信息")

    if all_items:
        saved = save_to_db(all_items)
        logger.info(f"完成: 采集 {len(all_items)} 条, 入库 {saved} 条")
    else:
        logger.warning("未采集到任何数据")

    # 打印结果摘要
    for i, item in enumerate(all_items[:10]):
        print(f"\n{i+1}. {item.get('title', 'N/A')}")
        print(f"   日期: {item.get('publish_date', 'N/A')}")
        print(f"   链接: {item.get('detail_url', 'N/A')}")
        print(f"   类型: {item.get('notice_type', 'N/A')}")

    return all_items


if __name__ == "__main__":
    main()
