import requests
from requests.auth import HTTPProxyAuth

use_proxy = False

PROXY_USER = 'spi9y4pc3u'
PROXY_PASSWORD = 'y4CbKye7b7F3P=kosr'
PROXY_URL = 'in.smartproxy.com'
PROXY_PORT = 10001

proxy_url = f"http://{PROXY_USER}:{PROXY_PASSWORD}@{PROXY_URL}:{PROXY_PORT}"
proxies = {
    "http": proxy_url,
    "https": proxy_url,
}

url = 'https://checkip.amazonaws.com'

session = requests.Session()
if use_proxy:
    session.proxies.update(proxies)
    session.auth = HTTPProxyAuth(PROXY_USER, PROXY_PASSWORD)

try:
    response = session.get(url, timeout=10)
    print("IP:", response.text.strip())
except requests.exceptions.ProxyError as e:
    print("Proxy Error:", e)