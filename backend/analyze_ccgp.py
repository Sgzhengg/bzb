"""保存 ccgp.gov.cn 列表页 HTML 用于分析"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adapters.ccgp_adapter import CcgpAdapter
from bs4 import BeautifulSoup

adapter = CcgpAdapter({"max_pages": 1, "min_delay": 2, "max_delay": 3})
url = adapter._get_list_url("gkzb", 1, "local")
print(f"Fetching: {url}")
html = adapter._fetch_list_page(url)
print(f"HTML: {len(html)} chars" if html else "EMPTY")

if html:
    with open("ccgp_sample.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    soup = BeautifulSoup(html, "html.parser")
    # Find all list-like structures
    for tag in ["ul", "ol", "table", "div"]:
        for el in soup.find_all(tag, class_=True):
            cls = " ".join(el.get("class", []))
            if any(kw in cls.lower() for kw in ["list", "result", "item", "bid", "news", "content"]):
                children = len(list(el.find_all("li"))) or len(list(el.find_all("tr")))
                if children > 0:
                    print(f"  <{tag} class='{cls[:80]}'> items={children}")
                    # Show first child
                    first = el.find("li") or el.find("tr")
                    if first:
                        print(f"    first child text: {first.get_text(strip=True)[:100]}")
                    break
    
    # Also try to find ANY li elements with links
    lis = soup.find_all("li")
    li_with_links = [li for li in lis if li.find("a")]
    print(f"\nTotal <li> with <a>: {len(li_with_links)}")
    for li in li_with_links[:5]:
        a = li.find("a")
        print(f"  {a.get_text(strip=True)[:80]}")
        print(f"    href={a.get('href', '')[:80]}")
