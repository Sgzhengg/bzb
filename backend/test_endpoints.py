import urllib.request, json

endpoints = [
    '/api/v1/announcements?page_size=1',
    '/api/v1/awards?page_size=1',
    '/api/v1/relations/reminders',
    '/api/v1/overview/today',
    '/api/v1/announcements/fetch/status/test123',
]
for ep in endpoints:
    url = 'http://localhost:8000' + ep
    try:
        r = urllib.request.urlopen(url)
        print(f'200 {ep}')
    except urllib.error.HTTPError as e:
        print(f'{e.code} {ep}')
    except Exception as e:
        print(f'ERR {ep}: {e}')
