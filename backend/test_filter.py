import urllib.request, json

# Test with industry_type filter
url = "http://localhost:8000/api/v1/announcements?industry_type=%E8%BF%90%E8%90%A5%E5%95%86&page_size=3"
r = urllib.request.urlopen(url)
d = json.loads(r.read())
print(f"运营商筛选: total={d['total']}")
for i in d.get("items", []):
    print(f"  [{i.get('industry_type','')}] {i.get('title','')[:50]}")

# Test without filter
url2 = "http://localhost:8000/api/v1/announcements?page_size=3"
r2 = urllib.request.urlopen(url2)
d2 = json.loads(r2.read())
print(f"\n全部行业: total={d2['total']}")
for i in d2.get("items", []):
    print(f"  [{i.get('industry_type','')}] {i.get('title','')[:50]}")
