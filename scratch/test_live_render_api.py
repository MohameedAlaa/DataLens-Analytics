import urllib.request
import urllib.error
import json

boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
csv_data = "country,product,sales,customers,date\nUSA,Laptop,1200,10,2026-01-01\nUSA,Phone,800,8,2026-01-02\nEgypt,Laptop,900,7,2026-01-03\n"
body = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="file"; filename="test_sales.csv"\r\n'
    f'Content-Type: text/csv\r\n\r\n'
    f'{csv_data}'
    f'\r\n--{boundary}--\r\n'
).encode('utf-8')

print("1. Testing POST https://datalens-backend-jt3p.onrender.com/upload ...")
req = urllib.request.Request(
    'https://datalens-backend-jt3p.onrender.com/upload',
    data=body,
    headers={
        'Content-Type': f'multipart/form-data; boundary={boundary}',
    },
    method='POST'
)
try:
    res = urllib.request.urlopen(req, timeout=30)
    data = json.loads(res.read().decode('utf-8'))
    dataset_id = data.get('dataset_id')
    print(f"   -> Status: {res.status}, dataset_id: {dataset_id}")
    print(f"   -> Summary: {data.get('shape')}, columns: {list(data.get('dtypes', {}).keys())}")
except urllib.error.HTTPError as e:
    print(f"   -> FAILED: {e.code}, {e.read().decode()}")
    exit(1)

print(f"\n2. Testing GET https://datalens-backend-jt3p.onrender.com/stats/{dataset_id} ...")
req_stats = urllib.request.Request(
    f'https://datalens-backend-jt3p.onrender.com/stats/{dataset_id}',
    method='GET'
)
try:
    res_stats = urllib.request.urlopen(req_stats, timeout=20)
    stats_data = json.loads(res_stats.read().decode('utf-8'))
    print(f"   -> Status: {res_stats.status}, row_count: {stats_data.get('row_count')}")
except urllib.error.HTTPError as e:
    print(f"   -> FAILED: {e.code}, {e.read().decode()}")

print(f"\n3. Testing POST https://datalens-backend-jt3p.onrender.com/filter ...")
filter_payload = json.dumps({
    "dataset_id": dataset_id,
    "filters": {"country": ["USA"]}
}).encode('utf-8')
req_filter = urllib.request.Request(
    'https://datalens-backend-jt3p.onrender.com/filter',
    data=filter_payload,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    res_filter = urllib.request.urlopen(req_filter, timeout=20)
    filtered = json.loads(res_filter.read().decode('utf-8'))
    print(f"   -> Status: {res_filter.status}, filtered rows: {len(filtered.get('filtered_data', []))}")
except urllib.error.HTTPError as e:
    print(f"   -> FAILED: {e.code}, {e.read().decode()}")
