"""
测试政府平台API接口的可用性
"""
import httpx
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_gd_ygp_api():
    """测试广东公共资源交易平台API"""
    print("=" * 60)
    print("测试 gd_ygp (广东公共资源交易平台)")
    print("=" * 60)

    base_url = "https://ygp.gdzwfw.gov.cn"

    # 测试的API接口
    api_urls = [
        f"{base_url}/ggzy-portal/api/search/news",
        f"{base_url}/api/search/announcement",
    ]

    for api_url in api_urls:
        print(f"\n测试接口: {api_url}")
        try:
            with httpx.Client(timeout=15) as client:
                params = {
                    "keyword": "广东移动",
                    "pageNum": 1,
                    "pageSize": 20,
                    "region": "广东",
                }
                response = client.get(api_url, params=params)
                print(f"  状态码: {response.status_code}")
                print(f"  响应长度: {len(response.content)} 字节")

                if response.status_code == 200:
                    content = response.text
                    print(f"  内容预览: {content[:200]}...")

                    # 检查是否是JSON
                    if content.strip().startswith("{"):
                        import json
                        try:
                            data = json.loads(content)
                            print(f"  JSON结构: {list(data.keys())}")
                        except:
                            print(f"  JSON解析失败")
                    else:
                        print(f"  非JSON响应")
                else:
                    print(f"  请求失败")
        except Exception as e:
            print(f"  ❌ 错误: {e}")


def test_gd_zbtb_api():
    """测试广东招标投标监管网API"""
    print("\n" + "=" * 60)
    print("测试 gd_zbtb (广东招标投标监管网)")
    print("=" * 60)

    base_url = "https://zbtb.gd.gov.cn"
    search_url = f"{base_url}/api/search/announcement"

    print(f"\n测试接口: {search_url}")
    try:
        with httpx.Client(timeout=15) as client:
            params = {
                "keyword": "广东移动",
                "page": 1,
                "pageSize": 20,
            }
            response = client.get(search_url, params=params)
            print(f"  状态码: {response.status_code}")
            print(f"  响应长度: {len(response.content)} 字节")

            if response.status_code == 200:
                content = response.text
                print(f"  内容预览: {content[:200]}...")
            else:
                print(f"  请求失败")
    except Exception as e:
        print(f"  ❌ 错误: {e}")


def test_ccgp_api():
    """测试中国政府采购网页面"""
    print("\n" + "=" * 60)
    print("测试 ccgp (中国政府采购网)")
    print("=" * 60)

    base_url = "https://www.ccgp.gov.cn"

    # 测试的页面URL
    page_urls = [
        f"{base_url}/cggg/zygg/gkzb/",  # 中央公开招标
    ]

    for page_url in page_urls:
        print(f"\n测试页面: {page_url}")
        try:
            with httpx.Client(timeout=15) as client:
                response = client.get(page_url)
                print(f"  状态码: {response.status_code}")
                print(f"  响应长度: {len(response.content)} 字节")

                if response.status_code == 200:
                    content = response.text
                    print(f"  内容预览: {content[:200]}...")

                    # 检查是否有反爬提示
                    if "频繁访问" in content or "过于频繁" in content:
                        print(f"  ⚠️ 触发反爬限制")
                    elif "ul" in content and "li" in content:
                        print(f"  ✅ 页面结构正常")
                    else:
                        print(f"  ⚠️ 页面结构可能有变化")
                else:
                    print(f"  请求失败")
        except Exception as e:
            print(f"  ❌ 错误: {e}")


if __name__ == "__main__":
    test_gd_ygp_api()
    test_gd_zbtb_api()
    test_ccgp_api()
