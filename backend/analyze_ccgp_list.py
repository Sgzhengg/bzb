"""
深入分析ccgp公告列表页的结构
"""
import httpx
from bs4 import BeautifulSoup
import re

def analyze_ccgp_list_page():
    """分析ccgp公告列表页的实际结构"""
    print("=" * 70)
    print("深入分析 ccgp (中国政府采购网) 公告列表页")
    print("=" * 70)

    base_url = "https://www.ccgp.gov.cn"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # 测试多个公告列表页面
    list_pages = [
        "/cggg/zygg/gkzb/index.htm",           # 中央公开招标
        "/cggg/zygg/gkzb/index_2.htm",         # 第2页
        "/cggg/dfgg/gkzb/index.htm",           # 地方公开招标
        "/cggg/zygg/jzxcs/index.htm",          # 竞争性磋商
    ]

    for page_path in list_pages:
        print(f"\n[1] 分析页面: {page_path}")
        try:
            with httpx.Client(timeout=20, headers=headers, follow_redirects=True) as client:
                response = client.get(f"{base_url}{page_path}")
                print(f"  状态码: {response.status_code}")

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # 查找包含公告列表的主要容器
                    print(f"  [2] 查找公告列表容器...")

                    # 尝试多种常见的列表容器选择器
                    list_containers = [
                        ('ul.vF_list', soup.select('ul.vF_list')),
                        ('ul.c_list', soup.select('ul.c_list')),
                        ('ul.list', soup.select('ul.list')),
                        ('div.vTender', soup.select('div.vTender')),
                        ('li', soup.find_all('li')),
                    ]

                    for selector, elements in list_containers:
                        if elements:
                            print(f"    找到 {selector}: {len(elements)} 个元素")

                            # 查找链接
                            links_found = 0
                            for elem in elements[:5]:
                                links = elem.find_all('a', href=True)
                                if links:
                                    links_found += len(links)
                                    for link in links[:2]:
                                        title = link.get_text(strip=True)
                                        href = link.get('href', '')
                                        if len(title) > 10 and '公告' in title or '招标' in title:
                                            print(f"      公告: {title[:60]}")
                                            print(f"        链接: {href[:80]}")

                            if links_found > 0:
                                print(f"    共找到 {links_found} 个链接")
                                break

                    # 检查是否有分页
                    print(f"  [3] 检查分页...")
                    pagination_links = soup.find_all('a', href=re.compile(r'index_\d+\.htm'))
                    if pagination_links:
                        print(f"    找到分页链接: {len(pagination_links)} 个")
                        for link in pagination_links[:3]:
                            print(f"      {link.get('href')}")

                    # 检查是否有日期信息
                    print(f"  [4] 检查日期信息...")
                    date_elements = soup.find_all(['span', 'time', 'em'], class_=re.compile(r'date|time', re.I))
                    if date_elements:
                        print(f"    找到日期元素: {len(date_elements)} 个")
                        for elem in date_elements[:3]:
                            date_text = elem.get_text(strip=True)
                            if re.search(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}', date_text):
                                print(f"      日期: {date_text}")

        except Exception as e:
            print(f"  错误: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    analyze_ccgp_list_page()

    print("\n" + "=" * 70)
    print("分析完成！")
    print("=" * 70)
