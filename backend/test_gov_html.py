"""
检查政府平台的HTML页面结构和搜索表单
"""
import httpx
from bs4 import BeautifulSoup
import re

def check_gd_ygp_html():
    """检查gd_ygp的HTML页面结构"""
    print("=" * 70)
    print("检查 gd_ygp (广东公共资源交易平台) HTML结构")
    print("=" * 70)

    base_url = "https://ygp.gdzwfw.gov.cn"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    }

    # 检查搜索页面
    search_pages = [
        "/#/ggzy-portal/search/index",
        "/ggzy-portal/search/index",
        "/search/index",
    ]

    for page_path in search_pages:
        print(f"\n[1] 检查页面: {page_path}")
        try:
            with httpx.Client(timeout=15, headers=headers, follow_redirects=True) as client:
                response = client.get(f"{base_url}{page_path}")
                print(f"  状态码: {response.status_code}")
                print(f"  最终URL: {response.url}")

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # 查找搜索表单
                    forms = soup.find_all('form')
                    if forms:
                        print(f"  找到 {len(forms)} 个表单:")
                        for i, form in enumerate(forms[:3]):
                            action = form.get('action', '')
                            method = form.get('method', 'GET')
                            print(f"    表单{i+1}: action={action}, method={method}")

                            # 查找输入字段
                            inputs = form.find_all('input')
                            for inp in inputs[:5]:
                                name = inp.get('name', '')
                                input_type = inp.get('type', '')
                                if name:
                                    print(f"      输入: name={name}, type={input_type}")

                    # 查找搜索按钮/链接
                    search_buttons = soup.find_all(['button', 'a'], string=re.compile(r'搜索|查询|search', re.I))
                    if search_buttons:
                        print(f"  找到 {len(search_buttons)} 个搜索按钮")

        except Exception as e:
            print(f"  错误: {e}")


def check_gd_zbtb_html():
    """检查gd_zbtb的HTML页面结构"""
    print("\n" + "=" * 70)
    print("检查 gd_zbtb (广东招标投标监管网) HTML结构")
    print("=" * 70)

    base_url = "https://zbtb.gd.gov.cn"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    }

    # 检查主页和可能的搜索页面
    pages = [
        "/",
        "/search",
        "/index",
        "/xxgk",
    ]

    for page_path in pages:
        print(f"\n[1] 检查页面: {page_path}")
        try:
            with httpx.Client(timeout=15, headers=headers, follow_redirects=True) as client:
                response = client.get(f"{base_url}{page_path}")
                print(f"  状态码: {response.status_code}")
                print(f"  最终URL: {response.url}")

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # 查找搜索框
                    search_inputs = soup.find_all('input', {'type': ['search', 'text']})
                    if search_inputs:
                        print(f"  找到 {len(search_inputs)} 个搜索输入框")
                        for inp in search_inputs[:3]:
                            name = inp.get('name', '')
                            placeholder = inp.get('placeholder', '')
                            print(f"    输入框: name={name}, placeholder={placeholder}")

                    # 查找可能的搜索链接
                    search_links = soup.find_all('a', href=re.compile(r'search|query|cx', re.I))
                    if search_links:
                        print(f"  找到 {len(search_links)} 个搜索相关链接")
                        for link in search_links[:3]:
                            href = link.get('href', '')
                            text = link.get_text(strip=True)
                            print(f"    链接: {text} -> {href}")

        except Exception as e:
            print(f"  错误: {e}")


def check_ccgp_html():
    """检查ccgp的HTML页面结构"""
    print("\n" + "=" * 70)
    print("检查 ccgp (中国政府采购网) HTML结构")
    print("=" * 70)

    base_url = "https://www.ccgp.gov.cn"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    }

    # 检查公开招标页面
    pages = [
        "/cggg/zygg/gkzb/index.htm",  # 中央公开招标
        "/cggg/dfgg/index.htm",       # 地方公告
        "/search",                    # 搜索页面
    ]

    for page_path in pages:
        print(f"\n[1] 检查页面: {page_path}")
        try:
            with httpx.Client(timeout=15, headers=headers, follow_redirects=True) as client:
                response = client.get(f"{base_url}{page_path}")
                print(f"  状态码: {response.status_code}")

                if response.status_code == 200:
                    # 检查是否有反爬
                    if "验证" in response.text or "captcha" in response.text.lower():
                        print(f"  ⚠️  触发反爬验证")
                        continue

                    soup = BeautifulSoup(response.text, 'html.parser')

                    # 查找列表项
                    list_items = soup.find_all('li')
                    if list_items:
                        print(f"  找到 {len(list_items)} 个列表项")
                        for item in list_items[:3]:
                            link = item.find('a')
                            if link:
                                title = link.get_text(strip=True)
                                href = link.get('href', '')
                                print(f"    项目: {title[:50]}")
                                print(f"    链接: {href[:80]}")

                    # 查找分页链接
                    pagination = soup.find_all('a', href=re.compile(r'page|index_\d+', re.I))
                    if pagination:
                        print(f"  找到分页链接")

                elif response.status_code == 403:
                    print(f"  ⚠️  访问被拒绝（可能触发反爬）")
                else:
                    print(f"  状态码: {response.status_code}")

        except Exception as e:
            print(f"  错误: {e}")


if __name__ == "__main__":
    check_gd_ygp_html()
    check_gd_zbtb_html()
    check_ccgp_html()

    print("\n" + "=" * 70)
    print("检查完成！")
    print("=" * 70)
