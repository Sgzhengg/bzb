"""
回填公告的 deadline 和 bid_date 字段 (同步版本)
使用修复后的 classify_and_extract 重新提取

用法: python backfill_dates.py [--limit N] [--dry-run]
"""
import sys
import argparse
import logging
import sqlite3
from datetime import datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

from app.services.llm_classifier import classify_and_extract


def backfill(db_path: str, limit: int = 20, dry_run: bool = False):
    """回填缺失的日期字段"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # 查询 deadline 缺失且有内容的公告（优先处理长内容）
    cursor = conn.execute("""
        SELECT id, title, original_content, deadline, bid_date
        FROM announcements 
        WHERE (deadline IS NULL OR deadline < '2000-01-01')
          AND original_content IS NOT NULL 
          AND original_content != ''
          AND LENGTH(original_content) >= 20
        ORDER BY LENGTH(original_content) DESC, announce_date DESC
        LIMIT ?
    """, (limit,))

    candidates = cursor.fetchall()
    total = len(candidates)
    logger.info(f"待处理: {total} 条公告")

    updated = 0
    skipped_not_ad = 0
    skipped_no_dates = 0
    errors = 0

    for i, row in enumerate(candidates):
        aid = row["id"]
        title = row["title"] or ""
        content = row["original_content"] or ""

        logger.info(f"[{i+1}/{total}] ID={aid} {title[:60]}... (content={len(content)}chars)")

        try:
            # 调用修复后的 LLM 提取
            unified = classify_and_extract(title, content)

            is_ad = unified.get("is_ad", False)
            new_deadline = unified.get("deadline")
            new_bid_date = unified.get("bid_date")

            if not is_ad:
                skipped_not_ad += 1
                reason = unified.get("reason", "")
                logger.info(f"  ⏭️ 非广告类: {reason}")
                continue

            if not new_deadline and not new_bid_date:
                skipped_no_dates += 1
                logger.info(f"  ⏭️ LLM未提取到日期")
                continue

            # 更新数据库
            updates = []
            params = []

            if new_deadline:
                try:
                    dt.strptime(new_deadline, "%Y-%m-%d")
                    updates.append("deadline = ?")
                    params.append(new_deadline)
                    logger.info(f"  📅 deadline → {new_deadline}")
                except ValueError:
                    logger.warning(f"  ⚠️ deadline格式无效: {new_deadline}")

            if new_bid_date:
                try:
                    dt.strptime(new_bid_date, "%Y-%m-%d")
                    updates.append("bid_date = ?")
                    params.append(new_bid_date)
                    logger.info(f"  📅 bid_date → {new_bid_date}")
                except ValueError:
                    logger.warning(f"  ⚠️ bid_date格式无效: {new_bid_date}")

            if updates:
                params.append(aid)
                sql = f"UPDATE announcements SET {', '.join(updates)} WHERE id = ?"
                if not dry_run:
                    conn.execute(sql, params)
                    conn.commit()
                updated += 1
            else:
                skipped_no_dates += 1

        except Exception as e:
            errors += 1
            logger.error(f"  ❌ 失败: {e}")

        # 每10条输出进度
        if (i + 1) % 10 == 0:
            logger.info(f"进度: {i+1}/{total} | 更新={updated} 非广告={skipped_not_ad} 无日期={skipped_no_dates} 错误={errors}")

    logger.info(f"\n{'='*50}")
    logger.info(f"回填完成{' (DRY RUN)' if dry_run else ''}:")
    logger.info(f"  总计: {total}")
    logger.info(f"  已更新: {updated}")
    logger.info(f"  跳过-非广告: {skipped_not_ad}")
    logger.info(f"  跳过-LLM未提取到日期: {skipped_no_dates}")
    logger.info(f"  错误: {errors}")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="回填公告日期字段")
    parser.add_argument("--limit", type=int, default=10, help="最多处理条数")
    parser.add_argument("--dry-run", action="store_true", help="仅分析不写入")
    parser.add_argument("--db", type=str, default="biaozhongbao.db", help="数据库路径")
    args = parser.parse_args()

    db_path = args.db
    if not Path(db_path).is_absolute():
        db_path = str(Path(__file__).parent / db_path)

    logger.info(f"数据库: {db_path}")
    logger.info(f"模式: {'DRY RUN' if args.dry_run else '正式写入'}")
    logger.info(f"限制: {args.limit} 条")

    backfill(db_path, limit=args.limit, dry_run=args.dry_run)
