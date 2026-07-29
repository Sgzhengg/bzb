"""
测试发现的政府平台API端点
"""
import httpx
import json

def test_gd_ygp_apis():
    """测试gd_ygp发现的API路径"""
    print("=" * 70)
    print("测试 gd_ygp (广东公共资源交易平台) API端点")
    print("=" * 70)

    base_url = "https://ygp.gdzwfw.gov.cn"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": base_url,
    }

    # 发现的API路径
    api_endpoints = [
        "/ggzy-portal/center/apis/",
        "/ggzy-portal/center/apis/search/",
        "/ggzy-portal/center/apis/stat/",
        "/ggzy-yhzx/mhyy-org/apis/",
        "/ggzy-portal/qrcode-apis/",
        "/ggzy-portal/api/",
        "/ggzy-portal/apis/",
        "/search/",
        "/api/",
    ]

    print("\n[1] 测试基础API路径...")
    for endpoint in api_endpoints:
        test_url = f"{base_url}{endpoint}"
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(test_url, headers=headers)
                if resp.status_code != 404:
                    print(f"  OK {endpoint} -> {resp.status_code}")
                    if len(resp.text) < 500:
                        print(f"     Response: {resp.text[:200]}")
                else:
                    print(f"  FAIL {endpoint} -> {resp.status_code}")
        except Exception as e:
            print(f"  ERROR {endpoint} -> {str(e)[:50]}")

    print("\n[2] Testing search APIs...")
    # Try specific search endpoints
    search_endpoints = [
        "/ggzy-portal/api/search/trade",
        "/ggzy-portal/api/tradeSearch",
        "/ggzy-portal/api/jyfw/search",
        "/ggzy-portal/api/search",
        "/ggzy-portal/apis/search",
        "/ggzy-portal/center/apis/search",
        "/api/search/trade",
        "/api/jyfwggzy/yycg-queryCgList",
        "/api/v1/jyfwggzy/yycg-queryCgList",
    ]

    for endpoint in search_endpoints:
        test_url = f"{base_url}{endpoint}"
        try:
            with httpx.Client(timeout=10) as client:
                # Try GET request
                resp = client.get(
                    test_url,
                    params={"keyword": "广东移动", "pageNo": 1, "pageSize": 20},
                    headers=headers
                )
                if resp.status_code == 200:
                    print(f"  OK GET {endpoint} -> 200")
                    try:
                        data = json.loads(resp.text)
                        print(f"     JSON keys: {list(data.keys())[:5]}")
                    except:
                        print(f"     Non-JSON: {resp.text[:100]}")
                elif resp.status_code != 404:
                    print(f"  WARN GET {endpoint} -> {resp.status_code}")
        except Exception as e:
            pass

        # Try POST request
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    test_url,
                    json={"keyword": "广东移动", "pageNo": 1, "pageSize": 20},
                    headers=headers
                )
                if resp.status_code == 200:
                    print(f"  OK POST {endpoint} -> 200")
                    try:
                        data = json.loads(resp.text)
                        print(f"     JSON keys: {list(data.keys())[:5]}")
                    except:
                        print(f"     Non-JSON: {resp.text[:100]}")
                elif resp.status_code != 404:
                    print(f"  WARN POST {endpoint} -> {resp.status_code}")
        except Exception as e:
            pass


def test_gd_zbtb_apis():
    """测试gd_zbtb发现的API路径"""
    print("\n" + "=" * 70)
    print("测试 gd_zbtb (广东招标投标监管网) API端点")
    print("=" * 70)

    base_url = "https://zbtb.gd.gov.cn"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": base_url,
    }

    # 测试发现的/search/路径
    print("\n[1] Testing /search/ path...")
    search_endpoints = [
        "/search/",
        "/search/api",
        "/api/search",
        "/api/search/list",
        "/search/list",
        "/api/cms/search",
        "/cms/api/search",
    ]

    for endpoint in search_endpoints:
        test_url = f"{base_url}{endpoint}"
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    test_url,
                    params={"keyword": "广东移动", "page": 1, "pageSize": 20},
                    headers=headers
                )
                if resp.status_code == 200:
                    print(f"  OK GET {endpoint} -> 200")
                    try:
                        data = json.loads(resp.text)
                        print(f"     JSON keys: {list(data.keys())[:5]}")
                    except:
                        print(f"     Non-JSON: {resp.text[:100]}")
                elif resp.status_code != 404:
                    print(f"  WARN GET {endpoint} -> {resp.status_code}")
        except Exception as e:
            pass

    # Try POST requests
    print("\n[2] Trying POST requests...")
    post_endpoints = [
        "/search/api",
        "/api/search",
        "/api/search/list",
    ]

    for endpoint in post_endpoints:
        test_url = f"{base_url}{endpoint}"
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    test_url,
                    json={"keyword": "广东移动", "page": 1, "pageSize": 20},
                    headers=headers
                )
                if resp.status_code == 200:
                    print(f"  OK POST {endpoint} -> 200")
                    try:
                        data = json.loads(resp.text)
                        print(f"     JSON keys: {list(data.keys())[:5]}")
                    except:
                        print(f"     Non-JSON: {resp.text[:100]}")
                elif resp.status_code != 404:
                    print(f"  WARN POST {endpoint} -> {resp.status_code}")
        except Exception as e:
            pass


def test_ccgp_search():
    """测试ccgp的搜索功能"""
    print("\n" + "=" * 70)
    print("测试 ccgp (中国政府采购网) 搜索功能")
    print("=" * 70)

    base_url = "https://www.ccgp.gov.cn"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # 测试搜索页面
    search_pages = [
        "/search",
        "/cggg/search",
        "/pubsearch",
    ]

    print("\n[1] Testing search pages...")
    for page in search_pages:
        test_url = f"{base_url}{page}"
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(test_url, headers=headers)
                if resp.status_code == 200:
                    print(f"  OK {page} -> 200")
                    if "keyword" in resp.text or "search" in resp.text.lower():
                        print(f"     Has search functionality")
                elif resp.status_code != 404:
                    print(f"  WARN {page} -> {resp.status_code}")
        except Exception as e:
            print(f"  ERROR {page} -> {str(e)[:50]}")


if __name__ == "__main__":
    test_gd_ygp_apis()
    test_gd_zbtb_apis()
    test_ccgp_search()

    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)
