import random
import requests
from bs4 import BeautifulSoup

USE_PROXY = False

PROXY_USER = 'spi9y4pc3u'
PROXY_PASSWORD = 'EhOKgfh53Ryaxky52c'
PROXY_URL = 'in.smartproxy.com'
PROXY_PORTS = ["10001", "10002", "10003", "10004", "10005", "10006", "10007", "10008", "10009", "10010"]


BASE_DIR = '/var/www/mml_python_code'


# BASE_DIR_LOGS = '/var/www/mml_python_code'
BASE_DIR_LOGS = BASE_DIR+'/logs'

# BASE_DIR_OUTPUTS = '/var/www/mml_python_code'
BASE_DIR_OUTPUTS = BASE_DIR+'/output'

def get_proxy():
    proxy_port = random.choice(PROXY_PORTS)
    return f'http://{PROXY_USER}:{PROXY_PASSWORD}@{PROXY_URL}:{proxy_port}'


def make_request(url, method='GET', headers=None, payload=None, verify=None):
    method = method.upper()
    if method not in ['GET', 'POST']:
        raise ValueError("Invalid method. Please use 'GET' or 'POST'.")
    proxies = {'http': get_proxy(),'https': get_proxy()} if USE_PROXY else {}

    if method == 'POST':
        response = requests.post(url, headers=headers, data=payload, verify=verify, proxies=proxies)
    elif method == 'GET':
        response = requests.get(url, headers=headers, params=payload, verify=verify, proxies=proxies)

    if response.status_code == 200:
        return BeautifulSoup(response.text, 'html.parser')
    else:
        print(f"Failed to retrieve page, status code: {response.status_code}")
        return None
