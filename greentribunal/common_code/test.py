# import requests
# from common_code.proxy_implement import get_playwright_proxy,get_requests_proxy
# from common_module import
# from playwright.sync_api import sync_playwright
#
# proxies = get_requests_proxy()
#
# url = 'https://checkip.amazonaws.com'
#
# session = requests.Session()
# try:
#     response = session.get(url, timeout=10,proxies=proxies)
#     print("IP:", response.text.strip(),'normal method')
# except requests.exceptions.ProxyError as e:
#     print("Proxy Error:", e)
#
#
#
# with sync_playwright() as p:
#     proxy = get_playwright_proxy()
#     browser = p.chromium.launch(proxy=proxy, headless=True)
#     context = browser.new_context()
#     page = context.new_page()
#     page.goto("https://checkip.amazonaws.com")
#     print(page.content(),'playwright method')
#     browser.close()