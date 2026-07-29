"""
深入分析政府平台，找到实际的API端点
通过检查主页的JavaScript文件和实际搜索功能
"""
import httpx
import re
import json
from urllib.parse import urljoin

def analyze_gd_ygp():
    """分析广东公共资源交易平台的实际API"""
    print("=" * 70)
    print("分析 gd_ygp (广东公共资源交易平台)")
    print("=" * 70)

    base_url = "https://ygp.gdzwfw.gov.cn"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        with httpx.Client(timeout=20, headers=headers, follow_redirects=True) as client:
            # 1. 获取主页内容，查找JavaScript文件
            print("\n[1] 获取主页内容，查找API端点...")
            response = client.get(f"{base_url}/")
            content = response.text

            # 2. 查找API相关的字符串
            api_patterns = [
                r'["\']([/\w\-]*(?:api|search|query)[/\w\-]*)["\']',
                r'url["\']:\s*["\']([^"\']+)["\']',
                r'baseURL["\']:\s*["\']([^"\']+)["\']',
                r'endpoint["\']:\s*["\']([^"\']+)["\']',
            ]

            found_apis = set()
            for pattern in api_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                found_apis.update(matches)

            print(f"  找到 {len(found_apis)} 个可能的API路径：")
            for api in sorted(found_apis)[:20]:
                if api.startswith('/') or 'api' in api.lower() or 'search' in api.lower():
                    print(f"    - {api}")

            # 3. 查找JavaScript文件
            js_files = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', content)
            print(f"\n[2] 找到 {len(js_files)} 个JavaScript文件")

            # 4. 检查主要的JS文件
            for js_file in js_files[:10]:  # 只检查前10个
                if js_file.startswith('http'):
                    js_url = js_file
                else:
                    js_url = urljoin(base_url, js_file)

                try:
                    js_response = client.get(js_url, timeout=10)
                    js_content = js_response.text

                    # 在JS文件中查找API端点
                    js_api_patterns = [
                        r'["\'](/[\w\-/]*(?:api|search|query))["\']',
                        r'["\']([^"\']*ggzy[^"\']*api[^"\']*)["\']',
                        r'["\']([^"\']*ygp[^"\']*api[^"\']*)["\']',
                    ]

                    for pattern in js_api_patterns:
                        matches = re.findall(pattern, js_content)
                        for match in matches:
                            if match.startswith('/') and len(match) > 5:
                                print(f"    从 {js_file.split('/')[-1]} 发现: {match}")
                except:
                    pass

            # 5. 尝试常见的API路径
            print(f"\n[3] 测试常见API路径...")
            test_paths = [
                "/api/v1/search",
                "/api/search/news",
                "/ggzy-portal/api/search",
                "/portal/api/search",
                "/ygp-ggzy-portal/api/search",
                "/gzyy-portal/api/search",
                "/api/jyfw/search",
                "/api/tradeSearch",
            ]

            for path in test_paths:
                test_url = f"{base_url}{path}"
                try:
                    resp = client.get(test_url, timeout=10)
                    if resp.status_code != 404:
                        print(f"    ✅ {path} → {resp.status_code}")
                        if len(resp.text) < 500:
                            print(f"       响应: {resp.text[:200]}")
                except:
                    pass

            # 6. 尝试POST请求（如果搜索是POST方式）
            print(f"\n[4] 尝试POST搜索请求...")
            post_endpoints = [
                "/api/search/news",
                "/ggzy-portal/api/search",
                "/api/v1/announcement/search",
            ]

            for endpoint in post_endpoints:
                try:
                    resp = client.post(
                        f"{base_url}{endpoint}",
                        json={"keyword": "广东移动", "pageNum": 1, "pageSize": 20},
                        timeout=10
                    )
                    if resp.status_code != 404:
                        print(f"    ✅ POST {endpoint} → {resp.status_code}")
                        print(f"       响应: {resp.text[:200]}")
                except:
                    pass

    except Exception as e:
        print(f"分析失败: {e}")


def analyze_gd_zbtb():
    """分析广东招标投标监管网的实际API"""
    print("\n" + "=" * 70)
    print("分析 gd_zbtb (广东招标投标监管网)")
    print("=" * 70)

    base_url = "https://zbtb.gd.gov.cn"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }

    try:
        with httpx.Client(timeout=20, headers=headers, follow_redirects=True) as client:
            print("\n[1] 获取主页内容...")
            response = client.get(f"{base_url}/")
            content = response.text

            # 2. 查找搜索相关的表单和接口
            print("\n[2] 查找搜索功能...")

            # 查找搜索表单
            forms = re.findall(r'<form[^>]*action=["\']([^"\']+)["\'][^>]*>', content)
            if forms:
                print(f"  找到搜索表单: {forms}")

            # 查找JavaScript中的搜索API
            api_patterns = [
                r'["\']([/\w\-]*(?:search|query|api)[/\w\-]*)["\']',
                r'url["\']:\s*["\']([^"\']+search[^"\']*)["\']',
            ]

            found_apis = set()
            for pattern in api_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                found_apis.update(matches)

            print(f"\n  找到 {len(found_apis)} 个可能的搜索路径：")
            for api in sorted(found_apis)[:15]:
                if api.startswith('/') or 'search' in api.lower():
                    print(f"    - {api}")

            # 3. 查找JavaScript文件
            js_files = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', content)
            print(f"\n[3] 分析JavaScript文件...")

            for js_file in js_files[:8]:
                if js_file.startswith('http'):
                    js_url = js_file
                else:
                    js_url = urljoin(base_url, js_file)

                try:
                    js_response = client.get(js_url, timeout=10)
                    js_content = js_response.text

                    # 在JS中查找搜索API
                    search_patterns = [
                        r'["\'](/[\w\-/]*search[\w\-/]*)["\']',
                        r'["\'](/[\w\-/]*api[\w\-/]*search[\w\-/]*)["\']',
                    ]

                    for pattern in search_patterns:
                        matches = re.findall(pattern, js_content, re.IGNORECASE)
                        for match in matches:
                            print(f"    从 {js_file.split('/')[-1]} 发现: {match}")
                except:
                    pass

            # 4. 测试可能的API端点
            print(f"\n[4] 测试可能的API端点...")
            test_endpoints = [
                "/api/search",
                "/api/search/list",
                "/search/api",
                "/cms/api/search",
                "/api/zbtb/search",
                "/api/announcement/search",
            ]

            for endpoint in test_endpoints:
                test_url = f"{base_url}{endpoint}"
                try:
                    resp = client.get(
                        test_url,
                        params={"keyword": "广东移动", "page": 1, "pageSize": 20},
                        timeout=10
                    )
                    if resp.status_code == 200:
                        print(f"    ✅ GET {endpoint} → 200 OK")
                        print(f"       响应: {resp.text[:200]}")
                    elif resp.status_code != 404:
                        print(f"    ⚠️  GET {endpoint} → {resp.status_code}")
                except Exception as e:
                    pass

    except Exception as e:
        print(f"分析失败: {e}")


def analyze_ccgp():
    """分析中国政府采购网的实际页面结构"""
    print("\n" + "=" * 70)
    print("分析 ccgp (中国政府采购网)")
    print("=" * 70)

    base_url = "https://www.ccgp.gov.cn"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }

    try:
        with httpx.Client(timeout=20, headers=headers, follow_redirects=True) as client:
            print("\n[1] 尝试访问主页...")
            response = client.get(f"{base_url}/")
            print(f"  状态码: {response.status_code}")
            print(f"  响应长度: {len(response.content)} 字节")

            if response.status_code == 200:
                content = response.text

                # 检查是否有反爬
                if "验证" in content or "captcha" in content.lower() or "频繁" in content:
                    print("  ⚠️  触发了反爬验证")
                    return

                # 2. 查找搜索入口
                print("\n[2] 查找搜索功能...")

                # 查找搜索链接
                search_links = re.findall(r'<a[^>]+href=["\']([^"\']*)["\'][^>]*>[^<]*(?:搜索|查询)[^<]*</a>', content)
                if search_links:
                    print(f"  找到搜索链接:")
                    for link in search_links[:5]:
                        full_url = urljoin(base_url, link)
                        print(f"    - {full_url}")

                # 3. 尝试访问搜索页面
                search_pages = [
                    "/search",
                    "/cggg/index.htm",
                    "/pubsearch",
                ]

                print("\n[3] 尝试访问搜索页面...")
                for page in search_pages:
                    try:
                        resp = client.get(f"{base_url}{page}", timeout=10)
                        if resp.status_code == 200:
                            print(f"    ✅ {page} → 200 OK")
                        elif resp.status_code != 404:
                            print(f"    ⚠️  {page} → {resp.status_code}")
                    except:
                        pass

    except Exception as e:
        print(f"分析失败: {e}")


if __name__ == "__main__":
    analyze_gd_ygp()
    analyze_gd_zbtb()
    analyze_ccgp()

    print("\n" + "=" * 70)
    print("分析完成！")
    print("=" * 70)
