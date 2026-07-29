"""分析 ccgp 详情页 HTML 结构"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adapters.ccgp_adapter import CcgpAdapter
from bs4 import BeautifulSoup

adapter = CcgpAdapter({"max_pages": 1, "min_delay": 2, "max_delay": 3})
url = "https://www.ccgp.gov.cn/cggg/dfgg/gkzb/202607/t20260729_27027394.htm"

import httpx
client = adapter._get_client()
resp = client.get(url)
html = resp.text
with open("ccgp_detail.html", "w", encoding="utf-8") as f:
    f.write(html)

soup = BeautifulSoup(html, "html.parser")
# Find title
for selector in ["h1", "h2", ".title", "[class*=title]", "title"]:
    el = soup.select_one(selector)
    if el:
        print(f"  {selector}: {el.get_text(strip=True)[:100]}")

# Find content body
for cls in ["content", "article", "detail", "main"]:
    el = soup.find(class_=cls)
    if el:
        print(f"  .{cls}: {el.get_text(strip=True)[:100]}...")

# Print first 500 chars of text
body = soup.find("body")
if body:
    text = body.get_text(separator="\n", strip=True)
    print(f"\nBody text (first 500):\n{text[:500]}")
