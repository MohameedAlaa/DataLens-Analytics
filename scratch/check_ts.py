import urllib.request

url = 'https://data-lens-analytics.vercel.app/assets/index-CMYMynbc.js'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
content = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')

idx = content.find('persistent FastAPI backend')
print('Index:', idx)
if idx != -1:
    print(content[max(0, idx-300):min(len(content), idx+300)])
