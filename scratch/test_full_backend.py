import urllib.request
import json
import uuid

backend_url = 'https://datalens-backend-jt3p.onrender.com'
origin = 'https://data-lens-analytics.vercel.app'

def run_post(endpoint, data, headers):
    req = urllib.request.Request(
        f'{backend_url}{endpoint}',
        data=data,
        method='POST',
        headers={**headers, 'Origin': origin, 'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req, timeout=35) as res:
        return res.status, json.loads(res.read().decode('utf-8'))

def run_get(endpoint):
    req = urllib.request.Request(
        f'{backend_url}{endpoint}',
        method='GET',
        headers={'Origin': origin, 'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req, timeout=35) as res:
        return res.status, json.loads(res.read().decode('utf-8'))

# 1. Upload uat_sales.csv
boundary = f'----WebKitFormBoundary{uuid.uuid4().hex}'
csv1 = """country,product,sales,customers,date
USA,Laptop,1200,10,2026-01-01
USA,Phone,800,8,2026-01-02
Egypt,Laptop,900,7,2026-01-03
Egypt,Phone,600,6,2026-01-04
""".encode('utf-8')

body1 = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="file"; filename="uat_sales.csv"\r\n'
    f'Content-Type: text/csv\r\n\r\n'
).encode('utf-8') + csv1 + f'\r\n--{boundary}--\r\n'.encode('utf-8')

print("Uploading Dataset 1...")
status1, resp1 = run_post('/upload', body1, {'Content-Type': f'multipart/form-data; boundary={boundary}'})
d1_id = resp1.get('dataset_id')
print(f"Dataset 1 ID: {d1_id}")

# 2. Stats
print("\nFetching Dataset 1 Stats...")
stats_status, stats_data = run_get(f'/stats/{d1_id}')
print("Numeric summary keys:", stats_data.get('numeric_summary', {}).keys())
print("Sales stats:", stats_data.get('numeric_summary', {}).get('sales'))

# 3. Filter sales >= 800
print("\nFiltering Dataset 1 (sales >= 800)...")
filter_status, filter_data = run_post('/filter', json.dumps({
    'dataset_id': d1_id,
    'filters': {'sales': {'operator': '>=', 'value': 800}}
}).encode('utf-8'), {'Content-Type': 'application/json'})
print("Filtered row count:", len(filter_data.get('filtered_data', [])))
print("Filtered sales values:", [r['sales'] for r in filter_data.get('filtered_data', [])])

# 4. Chat questions on Dataset 1
questions = [
    "What is the total sales?",
    "What are the total sales in the USA?",
    "What are the total sales in Egypt?",
    "Which products were sold in the USA?",
    "Compare sales between USA and Egypt."
]
for q in questions:
    print(f"\nAsking: '{q}'...")
    try:
        c_status, c_data = run_post('/chat', json.dumps({
            'dataset_id': d1_id,
            'question': q,
            'history': []
        }).encode('utf-8'), {'Content-Type': 'application/json'})
        print("Answer:", c_data.get('answer'))
        print("Citations count:", len(c_data.get('citations', [])))
    except Exception as e:
        print("Chat failed:", e)

# 5. Upload Dataset 2 (Cross-dataset isolation)
csv2 = """region,tier,revenue,units,quarter
North,Enterprise,5000,20,Q1
South,SMB,3000,15,Q2
""".encode('utf-8')
body2 = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="file"; filename="uat_second.csv"\r\n'
    f'Content-Type: text/csv\r\n\r\n'
).encode('utf-8') + csv2 + f'\r\n--{boundary}--\r\n'.encode('utf-8')

print("\nUploading Dataset 2 (Cross-dataset isolation)...")
status2, resp2 = run_post('/upload', body2, {'Content-Type': f'multipart/form-data; boundary={boundary}'})
d2_id = resp2.get('dataset_id')
print(f"Dataset 2 ID: {d2_id}")

print("\nAsking Dataset 2: 'What is the revenue in the North region?'...")
c2_status, c2_data = run_post('/chat', json.dumps({
    'dataset_id': d2_id,
    'question': 'What is the revenue in the North region?',
    'history': []
}).encode('utf-8'), {'Content-Type': 'application/json'})
print("Answer 2:", c2_data.get('answer'))
print("Contains dataset 1 info (USA/Egypt/Laptop)?", any(w in c2_data.get('answer', '').lower() for w in ['usa', 'egypt', 'laptop', 'phone']))
