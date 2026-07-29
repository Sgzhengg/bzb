"""解析 cfcpn.com 公告列表 HTML"""
import httpx
from bs4 import BeautifulSoup

client = httpx.Client(timeout=10)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
r = client.get("http://www.cfcpn.com/jcw/sys/notice/list", headers=headers)
print(f"HTML: {len(r.text)} chars")

soup = BeautifulSoup(r.text, "html.parser")

# Find all links with titles
links = soup.find_all("a", href=True)
notice_links = []
for a in links:
    title = a.get_text(strip=True)
    href = a.get("href", "")
    if len(title) > 10 and "javascript" not in href:
        notice_links.append((title[:80], href[:80]))

print(f"\nNotice links: {len(notice_links)}")
for t, h in notice_links[:20]:
    print(f"  {t}")
    print(f"    -> {h}")

# Find any text that looks like a notice list
text_blocks = []
for tag in ["li", "tr", "div"]:
    for el in soup.find_all(tag, class_=True):
        text = el.get_text(strip=True)
        if "银行" in text and len(text) > 20:
            text_blocks.append(text[:150])
            break

print(f"\nText blocks with '银行': {len(text_blocks)}")
for t in text_blocks[:10]:
    print(f"  {t}")
