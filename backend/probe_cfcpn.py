"""探测 cfcpn.com 的 API 接口"""
import httpx, json

# Try common API patterns
base = "http://www.cfcpn.com"
apis = [
    "/jcw/sys/notice/list",
    "/jcw/api/notice/query",
    "/api/notice/list",
    "/api/announcement/list",
    "/jcw/notice/queryList",
]

client = httpx.Client(timeout=10, follow_redirects=True)
headers = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
}

for api in apis:
    for method in ["GET", "POST"]:
        try:
            if method == "GET":
                r = client.get(base + api, headers=headers)
            else:
                r = client.post(base + api, headers=headers, json={"pageNum": 1, "pageSize": 5, "keyword": "广告"})
            
            ct = r.headers.get("content-type", "")
            if "json" in ct:
                print(f"✅ {method} {api} → JSON {len(r.text)} chars")
                data = r.json()
                print(f"   keys: {list(data.keys())[:5]}")
            elif r.status_code == 200:
                print(f"   {method} {api} → HTML {len(r.text)} chars")
        except Exception as e:
            pass

# Also try the main page to see what HTML it returns
r = client.get(base + "/jcw/sys/index", headers=headers)
print(f"\nMain page: {len(r.text)} chars, title in {'Yes' if '金采' in r.text else 'No'}")
