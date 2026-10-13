import urllib.request
import json
import codecs

backend_url = 'https://datalens-backend-jt3p.onrender.com'
origin = 'https://data-lens-analytics.vercel.app'
dataset_id = 'fdc5b036-7742-4426-84ba-86a227243c29'

chat_payload = json.dumps({
    'dataset_id': dataset_id,
    'question': 'What is the total sales?',
    'history': []
}).encode('utf-8')

req = urllib.request.Request(
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
    with urllib.request.urlopen(req, timeout=30) as res:
        print('CHAT status:', res.status)
        data = json.loads(res.read().decode('utf-8'))
        print('CHAT response keys:', list(data.keys()))
        print('CHAT answer:\n', data.get('response') or data.get('answer'))
        print('CHAT citations:\n', data.get('citations'))
except Exception as e:
    print('CHAT failed:', e)
    if hasattr(e, 'read'):
        print('Error body:', e.read().decode('utf-8', errors='ignore'))
