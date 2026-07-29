"""测试修复后的ccgp适配器"""
import sys, os
import logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters.ccgp_adapter import CcgpAdapter

logging.basicConfig(level=logging.INFO)

config = {
    'max_pages': 1,
    'min_delay': 2.0,
    'max_delay': 4.0,
}

adapter = CcgpAdapter(config)
print('Testing ccgp adapter with fixed selector...')

# Test with central government public bidding page
html = adapter._fetch_list_page('https://www.ccgp.gov.cn/cggg/zygg/gkzb/index.htm')
if html:
    items = adapter.parse_list(html)
    print(f'Parsed {len(items)} items from page')
    for i, item in enumerate(items[:5]):
        print(f'[{i+1}] {item.get("title", "N/A")[:60]}')
else:
    print('Failed to fetch page')
