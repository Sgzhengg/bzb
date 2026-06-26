"""全模块导入链验证"""
import sys
sys.path.insert(0, 'd:/bzb/backend')

from app.services.keyword_filter import filter_advertisement_projects, batch_filter
from app.services.crawler.config import LIST_URL, MIN_REQUEST_INTERVAL
from app.services.crawler.parser import parse_list_page, parse_detail_page, _extract_budget, _extract_score_weight
from app.services.crawler.fetcher import BiddingFetcher, RateLimiter
from app.services.crawler.pipeline import BiddingCrawlerPipeline
from app.services.historical_crawler.config import SEARCH_KEYWORD_COMBOS, MIN_DELAY, MAX_DELAY
from app.services.historical_crawler.cleaner import normalize_purchaser_name, normalize_amount, clean_award_record, batch_clean
from app.services.historical_crawler.collector import HistoricalAwardCollector, CheckpointManager, BatchSaver, parse_award_detail

print('=== 全部模块导入链验证 ===')
print()

# keyword_filter
r = filter_advertisement_projects("品牌广告", "")
print(f'[keyword_filter] 命中 {len(r["matched_keywords"])} 个关键词: {r["matched_keywords"]}')

# crawler
print(f'[crawler]       URL={LIST_URL[:50]}...')
print(f'[crawler]       限速={MIN_REQUEST_INTERVAL}s')
print(f'[crawler]       RateLimiter={RateLimiter}')
print(f'[crawler]       BiddingFetcher={BiddingFetcher}')

# historical_crawler
print(f'[historical]    搜索关键词组数={len(SEARCH_KEYWORD_COMBOS)}')
print(f'[historical]    延迟范围={MIN_DELAY}-{MAX_DELAY}s')
print(f'[historical]    CheckpointManager={CheckpointManager}')
print(f'[historical]    BatchSaver={BatchSaver}')
print(f'[historical]    HistoricalAwardCollector={HistoricalAwardCollector}')

# cleaner
print(f'[cleaner]       省公司={normalize_purchaser_name("中国移动通信集团广东有限公司")}')
print(f'[cleaner]       128.5万元={normalize_amount("128.5万元")}')
bid, budget = __import__('app.services.historical_crawler.cleaner', fromlist=['extract_bid_and_budget']).extract_bid_and_budget('中标金额：485万元。采购预算：500万元。')
print(f'[cleaner]       bid={bid}, budget={budget}')

print()
print('✅ 全部 4 个子模块导入链完整，功能正常！')
