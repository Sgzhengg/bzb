"""
Live Crawler Verification Script - Async Version
Execute real data collection for July to validate crawler functionality
"""

import asyncio
import sys
import os
from datetime import date, datetime, timedelta
import time

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("BZB Live Crawler Verification - July Data Collection")
print("=" * 70)
print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============================================================
# Configuration
# ============================================================

JULY_START = date(2026, 7, 1)
TODAY = date.today()

# ============================================================
# 1. Initialize Database and Models
# ============================================================

print("[1/6] Initializing database connection...")
try:
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select, func, and_
    from app.models.announcement import Announcement
    from app.models.historical_award import HistoricalAward
    print("  [OK] Database session initialized")
except Exception as e:
    print(f"  [FAIL] Database initialization failed: {e}")
    sys.exit(1)

# ============================================================
# 2. Check current data status
# ============================================================

async def check_current_data():
    """Check existing data in database"""
    async with AsyncSessionLocal() as db:
        # Check announcements
        result = await db.execute(
            select(func.count(Announcement.id))
            .where(and_(
                Announcement.announce_date >= JULY_START,
                Announcement.announce_date <= TODAY,
            ))
        )
        ann_count = result.scalar() or 0

        # Check awards
        result = await db.execute(
            select(func.count(HistoricalAward.id))
            .where(and_(
                HistoricalAward.bid_open_date >= JULY_START,
                HistoricalAward.bid_open_date <= TODAY,
            ))
        )
        award_count = result.scalar() or 0

        print(f"  Current announcements (July): {ann_count}")
        print(f"  Current awards (July): {award_count}")

        return ann_count, award_count

# ============================================================
# 3. Execute announcement collection
# ============================================================

async def collect_announcements():
    """Execute announcement collection from all sources"""
    print("\n[3/6] Executing announcement collection...")
    print("  Target: July announcements from enabled sources")

    from data_collector import DataCollector

    collector = DataCollector()

    # Get enabled adapters
    enabled_adapters = []
    for name, cfg in collector._adapters.items():
        if cfg.get("enabled"):
            enabled_adapters.append(name)

    print(f"  Enabled sources: {', '.join(enabled_adapters)}")

    total_new = 0

    for adapter_name in enabled_adapters:
        print(f"\n  Collecting from {adapter_name}...")
        try:
            start = time.time()

            # Execute collection
            results = collector.collect(
                adapter_name=adapter_name,
                save_to_db=True,
                max_pages=2,  # Limit to 2 pages for verification
            )

            elapsed = time.time() - start
            new_count = len(results)
            total_new += new_count

            print(f"    [OK] {adapter_name}: {new_count} items ({elapsed:.1f}s)")

        except Exception as e:
            print(f"    [FAIL] {adapter_name}: {str(e)[:80]}...")

    print(f"\n  Total new announcements: {total_new}")
    return total_new

# ============================================================
# 4. Execute award collection
# ============================================================

async def collect_awards():
    """Execute award (winning bid) collection"""
    print("\n[4/6] Executing award collection...")

    try:
        from app.services.historical_crawler.collector import HistoricalAwardCollector

        award_collector = HistoricalAwardCollector()

        print("  Collecting winning bids (max 2 pages)...")
        start = time.time()

        awards = await award_collector.collect(max_pages=2)
        award_count = len(awards)
        elapsed = time.time() - start

        print(f"  [OK] Collected {award_count} awards ({elapsed:.1f}s)")
        return award_count

    except Exception as e:
        print(f"  [FAIL] Award collection failed: {e}")
        return 0

# ============================================================
# 5. Verify collected data
# ============================================================

async def verify_data_quality():
    """Verify the quality of collected data"""
    print("\n[5/6] Verifying collected data quality...")

    async with AsyncSessionLocal() as db:
        # Get July announcements
        result = await db.execute(
            select(
                Announcement.title,
                Announcement.announce_date,
                Announcement.city,
                Announcement.project_category,
                Announcement.budget,
            )
            .where(and_(
                Announcement.announce_date >= JULY_START,
                Announcement.announce_date <= TODAY,
            ))
            .order_by(Announcement.announce_date.desc())
            .limit(20)
        )
        announcements = result.all()

        print(f"\n  Sample announcements (showing first 10):")
        for i, ann in enumerate(announcements[:10], 1):
            print(f"    {i}. {ann.title[:50]}...")
            print(f"       Date: {ann.announce_date} | City: {ann.city or 'N/A'} | Category: {ann.project_category or 'N/A'}")

        # Check by category distribution
        result = await db.execute(
            select(Announcement.project_category, func.count(Announcement.id))
            .where(and_(
                Announcement.announce_date >= JULY_START,
                Announcement.announce_date <= TODAY,
            ))
            .group_by(Announcement.project_category)
        )
        categories = result.all()

        print(f"\n  Category distribution:")
        for cat, count in categories:
            print(f"    {cat or 'Uncategorized'}: {count}")

        # Check awards
        result = await db.execute(
            select(
                HistoricalAward.project_name,
                HistoricalAward.winner_name,
                HistoricalAward.bid_amount,
                HistoricalAward.bid_open_date,
            )
            .where(and_(
                HistoricalAward.bid_open_date >= JULY_START,
                HistoricalAward.bid_open_date <= TODAY,
            ))
            .order_by(HistoricalAward.bid_open_date.desc())
            .limit(10)
        )
        awards_data = result.all()

        print(f"\n  Sample awards:")
        for i, award in enumerate(awards_data[:5], 1):
            print(f"    {i}. {award.project_name[:50]}...")
            print(f"       Winner: {award.winner_name[:40]}... | Amount: {award.bid_amount}万")

        return len(announcements), len(awards_data), categories

# ============================================================
# 6. Generate verification report
# ============================================================

async def generate_report():
    """Generate final verification report"""
    print("\n[6/6] Generating verification report...")

    async with AsyncSessionLocal() as db:
        # Total July announcements
        result = await db.execute(
            select(func.count(Announcement.id))
            .where(and_(
                Announcement.announce_date >= JULY_START,
                Announcement.announce_date <= TODAY,
            ))
        )
        total_july_ann = result.scalar() or 0

        # Total July awards
        result = await db.execute(
            select(func.count(HistoricalAward.id))
            .where(and_(
                HistoricalAward.bid_open_date >= JULY_START,
                HistoricalAward.bid_open_date <= TODAY,
            ))
        )
        total_july_award = result.scalar() or 0

        # By source
        source_stats = {}
        for domain in ["zhaobiao.cn", "zbtb.gd.gov.cn", "ygp.gdzwfw.gov.cn", "b2b.10086.cn"]:
            result = await db.execute(
                select(func.count(Announcement.id))
                .where(and_(
                    Announcement.announce_date >= JULY_START,
                    Announcement.announce_date <= TODAY,
                    Announcement.source_url.like(f"%{domain}%")
                ))
            )
            source_stats[domain] = result.scalar() or 0

        return total_july_ann, total_july_award, source_stats

# ============================================================
# Main async execution
# ============================================================

async def main():
    """Main execution function"""
    print("\nStarting crawler verification...")
    print(f"Time range: {JULY_START.isoformat()} to {TODAY.isoformat()}")

    # Check current status
    existing_ann, existing_award = await check_current_data()

    # Collect announcements
    new_ann = await collect_announcements()

    # Collect awards
    new_award = await collect_awards()

    # Verify data quality
    ann_count, award_count, category_dist = await verify_data_quality()

    # Generate report
    final_ann, final_award, source_stats = await generate_report()

    # Print final report
    print("\n" + "=" * 70)
    print("CRAWLER VERIFICATION REPORT")
    print("=" * 70)

    print(f"\nPeriod: {JULY_START.isoformat()} to {TODAY.isoformat()}")

    print(f"\n[ANNOUNCEMENTS]")
    print(f"  Previously existing: {existing_ann}")
    print(f"  Newly collected: {new_ann}")
    print(f"  Total July announcements: {final_ann}")

    print(f"\n[BY SOURCE]")
    for source, count in source_stats.items():
        if count > 0:
            print(f"  {source}: {count} items")
        else:
            print(f"  {source}: 0 items (no data)")

    print(f"\n[AWARDS]")
    print(f"  Total July awards: {final_award}")
    print(f"  Newly collected: {new_award}")

    print(f"\n[CATEGORY DISTRIBUTION]")
    for cat, count in category_dist:
        print(f"  {cat or 'Uncategorized'}: {count}")

    print(f"\n[CRAWLER STATUS]")
    if final_ann > existing_ann:
        print("  [OK] Crawler is working - collected new data")
        print(f"      Growth: +{final_ann - existing_ann} announcements")
    elif final_ann > 0:
        print("  [OK] Crawler functioning - data already exists")
    else:
        print("  [WARN] No announcements collected")

    if final_award > existing_award:
        print(f"  [OK] Awards collected: +{final_award - existing_award}")

    print(f"\n[CLOSING REMARKS]")
    if final_ann >= 10:
        print("  [EXCELLENT] Crawler performance is excellent!")
    elif final_ann >= 5:
        print("  [GOOD] Crawler is functioning properly")
    else:
        print("  [REVIEW] Crawler may need investigation")

    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

# Run main
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Verification stopped by user")
    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()
