import httpx
r = httpx.get("http://localhost:8000/api/v1/announcements?page_size=5")
data = r.json()
print(f"总数: {data['total']}")
for i in data["items"]:
    src = i.get("data_source", "")
    title = (i.get("title", "") or "")[:70]
    date = i.get("announce_date", "")
    cat = i.get("project_category", "")
    print(f"  [{src}] {title} | {date} | {cat}")
