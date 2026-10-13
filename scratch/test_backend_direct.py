import urllib.request
import urllib.parse
import mimetypes
import uuid
import json

backend_url = 'https://datalens-backend-jt3p.onrender.com'
origin = 'https://data-lens-analytics.vercel.app'

print('--- 1. Testing OPTIONS /upload (Preflight) ---')
req = urllib.request.Request(
    f'{backend_url}/upload',
    method='OPTIONS',
    headers={
        'Origin': origin,
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type',
        'User-Agent': 'Mozilla/5.0'
    }
)
try:
    with urllib.request.urlopen(req, timeout=15) as res:
        print('OPTIONS status:', res.status)
        print('CORS headers:')
        for h, v in res.getheaders():
            if 'cors' in h.lower() or 'access-control' in h.lower():
                print(f'  {h}: {v}')
except Exception as e:
    print('OPTIONS failed:', e)

print('\n--- 2. Testing POST /upload with uat_sales.csv ---')
boundary = f'----WebKitFormBoundary{uuid.uuid4().hex}'
csv_content = """country,product,sales,customers,date
USA,Laptop,1200,10,2026-01-01
USA,Phone,800,8,2026-01-02
Egypt,Laptop,900,7,2026-01-03
Egypt,Phone,600,6,2026-01-04
""".encode('utf-8')

body = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="file"; filename="uat_sales.csv"\r\n'
    f'Content-Type: text/csv\r\n\r\n'
).encode('utf-8') + csv_content + f'\r\n--{boundary}--\r\n'.encode('utf-8')

req2 = urllib.request.Request(
    f'{backend_url}/upload',
    data=body,
    method='POST',
    headers={
        'Origin': origin,
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'User-Agent': 'Mozilla/5.0'
    }
)

dataset_id = None
try:
    with urllib.request.urlopen(req2, timeout=25) as res:
        print('POST status:', res.status)
        resp_data = res.read().decode('utf-8')
        print('POST response snippet:', resp_data[:500])
        parsed = json.loads(resp_data)
        dataset_id = parsed.get('dataset_id') or parsed.get('id')
except Exception as e:
    print('POST failed:', e)
    if hasattr(e, 'read'):
        print('Error body:', e.read().decode('utf-8', errors='ignore'))

if dataset_id:
    print(f'\n--- 3. Testing POST /chat on dataset_id={dataset_id} ---')
    chat_payload = json.dumps({
        'dataset_id': dataset_id,
        'message': 'What is the total sales?',
        'history': []
    }).encode('utf-8')
    req3 = urllib.request.Request(
        f'{backend_url}/chat',
        data=chat_payload,
        method='POST',
        headers={
            'Origin': origin,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }
    )
    try:
        with urllib.request.urlopen(req3, timeout=30) as res:
            print('CHAT status:', res.status)
            print('CHAT response snippet:', res.read().decode('utf-8')[:500])
    except Exception as e:
        print('CHAT failed:', e)
        if hasattr(e, 'read'):
            print('Error body:', e.read().decode('utf-8', errors='ignore'))
