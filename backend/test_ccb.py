"""测试 ibuy.ccb.com HTML 是否包含数据"""
import httpx
client = httpx.Client(timeout=10, follow_redirects=True)
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
r = client.get("https://ibuy.ccb.com/cms/index.html", headers=headers)
print(f"Status: {r.status_code}, Length: {len(r.text)}")

from bs4 import BeautifulSoup
soup = BeautifulSoup(r.text, "html.parser")
text = soup.get_text()
lines = [l.strip() for l in text.splitlines() if l.strip() and len(l.strip()) > 10]
print(f"Visible text lines: {len(lines)}")
for l in lines[:20]:
    print(f"  {l[:100]}")

# Check if any bank ad keywords
ad_lines = [l for l in lines if any(k in l for k in ["广告", "宣传", "营销", "品牌"])]
print(f"\nLines with ad keywords: {len(ad_lines)}")
for l in ad_lines[:10]:
    print(f"  {l[:100]}")
