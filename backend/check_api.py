import httpx
r = httpx.get("http://localhost:8000/api/v1/announcements?page_size=3")
data = r.json()
print("total:", data["total"])
for i in data.get("items", [])[:3]:
    it = i.get("industry_type", "")
    cat = (i.get("project_category", "") or "")[:25]
    title = (i.get("title", "") or "")[:50]
    print(f"  industry_type={it}, cat={cat}")
    print(f"  title={title}")
