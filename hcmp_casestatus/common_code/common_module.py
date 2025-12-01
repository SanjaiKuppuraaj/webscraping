import random
import requests
from bs4 import BeautifulSoup

USE_PROXY = False

PROXY_USER = 'jbkinfotech25-res-in'
PROXY_PASSWORD = 'Ip1fsukDrglaz0M'
PROXY_URL = 'gw-open.netnut.net'
PROXY_PORTS = ['5959']

BASE_DIR = '/var/www/mml_python_code'
BASE_DIR_LOGS = BASE_DIR +'/logs'
BASE_DIR_OUTPUTS = BASE_DIR +'/output'

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
