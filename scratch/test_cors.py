import urllib.request
import urllib.error

test_origins = [
    'https://data-lens-analytics.vercel.app',
    'https://data-lens-analytics.vercel.app/',
    'https://datalens-analytics.vercel.app',
    'https://datalens-analytics.vercel.app/',
    'https://datalens-backend-jt3p.onrender.com',
    'http://localhost:5173',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:5173',
]

for origin in test_origins:
    req = urllib.request.Request(
        'https://datalens-backend-jt3p.onrender.com/upload',
        headers={
            'Origin': origin,
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type'
        },
        method='OPTIONS'
    )
    try:
        res = urllib.request.urlopen(req, timeout=10)
        print(f"SUCCESS: {origin} -> {res.status}, ACAO: {res.headers.get('access-control-allow-origin')}")
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        print(f"FAILED:  {origin} -> {e.code}, {body[:50]}")
