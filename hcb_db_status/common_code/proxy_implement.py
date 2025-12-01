import random

PROXY_USER = 'jbkinfotech25-res-in'
PROXY_PASSWORD = 'Ip1fsukDrglaz0M'
PROXY_URL = 'gw-open.netnut.net'
PROXY_PORT = ['5959']
USE_PROXY = True

def get_playwright_proxy():
    if not USE_PROXY:
        return None
    port = random.choice(PROXY_PORT)
    return {
        "server": f"http://{PROXY_URL}:{port}",
        "username": PROXY_USER,
        "password": PROXY_PASSWORD
    }

def get_requests_proxy():
    if not USE_PROXY:
        return None
    port = random.choice(PROXY_PORT)
    proxy_url = f"http://{PROXY_USER}:{PROXY_PASSWORD}@{PROXY_URL}:{port}"
    return {
        "http": proxy_url,
        "https": proxy_url,
    }
