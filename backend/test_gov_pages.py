"""
测试政府平台的实际可访问页面
"""
import httpx
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_gd_ygp_pages():
    """测试广东公共资源交易平台的页面"""
    print("=" * 60)
    print("测试 gd_ygp (广东公共资源交易平台) 页面结构")
    print("=" * 60)

    base_url = "https://ygp.gdzwfw.gov.cn"

    # 测试不同的页面路径
    test_urls = [
        f"{base_url}/",  # 主页
        f"{base_url}/#/ggzy-portal/search/index",  # 搜索页面
        f"{base_url}/ggzy-portal/",  # 门户入口
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }

    for url in test_urls:
        print(f"\n测试: {url}")
        try:
            with httpx.Client(timeout=15, headers=headers, follow_redirects=True) as client:
                response = client.get(url)
                print(f"  状态码: {response.status_code}")
                print(f"  最终URL: {response.url}")
                print(f"  响应长度: {len(response.content)} 字节")

                if response.status_code == 200:
                    content = response.text
                    # 查找可能的API端点
                    import re
                    api_patterns = re.findall(r'["\']([^"\']*(?:api|search)[^"\']*)["\']', content[:5000])
                    if api_patterns:
                        print(f"  可能的API路径: {set(api_patterns[:10])}")
        except Exception as e:
            print(f"  ❌ 错误: {e}")


def test_gd_zbtb_pages():
    """测试广东招标投标监管网的页面"""
    print("\n" + "=" * 60)
    print("测试 gd_zbtb (广东招标投标监管网) 页面结构")
    print("=" * 60)

    base_url = "https://zbtb.gd.gov.cn"

    # 测试不同的页面路径
    test_urls = [
        f"{base_url}/",  # 主页
        f"{base_url}/cms/",  # CMS入口
        f"{base_url}/cms/xxgk/",  # 信息公开
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }

    for url in test_urls:
        print(f"\n测试: {url}")
        try:
            with httpx.Client(timeout=15, headers=headers, follow_redirects=True) as client:
                response = client.get(url)
                print(f"  状态码: {response.status_code}")
                print(f"  最终URL: {response.url}")
                print(f"  响应长度: {len(response.content)} 字节")

                if response.status_code == 200:
                    content = response.text
                    # 查找可能的搜索入口
                    import re
                    search_forms = re.findall(r'action=["\']([^"\']+)["\']', content[:3000])
                    if search_forms:
                        print(f"  搜索表单: {set(search_forms)}")
        except Exception as e:
            print(f"  ❌ 错误: {e}")


if __name__ == "__main__":
    test_gd_ygp_pages()
    test_gd_zbtb_pages()
