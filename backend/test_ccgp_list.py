"""
直接测试ccgp公告列表页，获取实际的公告
"""
import httpx
from bs4 import BeautifulSoup
import time

def test_ccgp_list():
    """测试ccgp公告列表页，获取公告信息"""
    print("=" * 70)
    print("测试 ccgp (中国政府采购网) 获取公告列表")
    print("=" * 70)

    base_url = "https://www.ccgp.gov.cn"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    # 测试中央公开招标第1页
    page_path = "/cggg/zygg/gkzb/index.htm"

    print(f"\n[1] 获取页面: {page_path}")
    try:
        with httpx.Client(timeout=20, headers=headers, follow_redirects=True) as client:
            response = client.get(f"{base_url}{page_path}")
            print(f"  状态码: {response.status_code}")

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                print(f"\n[2] 分析页面结构...")

                # 直接查找所有链接
                all_links = soup.find_all('a', href=True)
                print(f"  找到 {len(all_links)} 个链接")

                # 筛选出可能是公告的链接
                announcement_links = []
                for link in all_links:
                    href = link.get('href', '')
                    title = link.get_text(strip=True)

                    # 跳过导航链接
                    if len(title) < 10 or not any(kw in title for kw in ['公告', '招标', '项目', '采购']):
                        continue

                    # 跳过首页等导航
                    if href.startswith('/') and len(href) < 20:
                        continue

                    # 跳过外部链接
                    if href.startswith('http') and 'ccgp.gov.cn' not in href:
                        continue

                    announcement_links.append({
                        'title': title,
                        'href': href
                    })

                print(f"  筛选出 {len(announcement_links)} 个可能的公告")

                print(f"\n[3] 前10条公告:")
                for i, item in enumerate(announcement_links[:10]):
                    print(f"  [{i+1}] {item['title'][:70]}")
                    print(f"       链接: {item['href'][:80]}")

                # 查找分页链接
                print(f"\n[4] 查找分页...")
                pagination = soup.find_all('a', href=lambda x: x and 'index_' in x and x.endswith('.htm'))
                if pagination:
                    print(f"  找到分页链接:")
                    for link in pagination:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        print(f"    {text} -> {href}")

                # 检查是否触发反爬
                if "频繁" in response.text or "验证" in response.text:
                    print(f"\n  WARNING: Triggered anti-scraping limit")

                # 测试第2页
                print(f"\n[5] 测试第2页...")
                time.sleep(5)  # 等待5秒
                response2 = client.get(f"{base_url}/cggg/zygg/gkzb/index_2.htm")
                print(f"  第2页状态码: {response2.status_code}")

                if response2.status_code == 200:
                    soup2 = BeautifulSoup(response2.text, 'html.parser')
                    links2 = soup2.find_all('a', href=True)
                    print(f"  第2页链接数: {len(links2)}")

    except Exception as e:
        print(f"  错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_ccgp_list()

    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)
