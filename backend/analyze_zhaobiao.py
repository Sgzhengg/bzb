"""保存 zhaobiao.cn 搜索结果 HTML 用于分析"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters.zhaobiao_adapter import ZhaobiaoAdapter
adapter = ZhaobiaoAdapter({"search_keyword": "广东移动 广告", "max_pages": 1, "min_delay": 1.0, "max_delay": 2.0})
html = adapter.fetch_list(page=1)
with open("zhaobiao_sample.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"HTML saved: {len(html)} chars")

# 分析结构
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "lxml")

# 找所有链接
links = soup.find_all("a", href=True)
print(f"\nTotal links: {len(links)}")
print("\nSample links with titles:")
for a in links[:30]:
    title = a.get_text(strip=True)
    href = a.get("href", "")
    if len(title) > 8:
        print(f"  [{title[:60]}] -> {href[:80]}")

# 找主要容器
print("\nMajor containers:")
for tag in ["div", "ul", "li", "table"]:
    for el in soup.find_all(tag, class_=True):
        cls = " ".join(el.get("class", []))
        if any(kw in cls.lower() for kw in ["result", "search", "list", "item", "project"]):
            print(f"  <{tag} class='{cls[:80]}'> children={len(list(el.children))}")
            break
