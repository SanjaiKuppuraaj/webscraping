import argparse
import requests
import json
from bs4 import BeautifulSoup as bs
from common_code import common_module as cm

def fetch_case_data(case_id, lst_case, txt_no, year):
    url = f'https://mphc.gov.in/php/hc/casestatus/casestatus_pro.php?id={case_id}&opt=1&lst_case={lst_case}&txtno={txt_no}&txtyear={year}&f=0.2222&csrf_token='
    headers = {'Accept': 'text/html, */*; q=0.01','Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8','Connection': 'keep-alive','DNT': '1', 'Referer': 'https://mphc.gov.in/causelist','User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)', 'X-Requested-With': 'XMLHttpRequest','Cookie': 'SSESS8c45314aadff2a84e50fe1a5f9b552c7=k8WMQlzzL4o0ztzXrm7cXHbjgFWehdm-2OMc2J15gFo; PHPSESSID=qj1p3qgo04efpskgheiqjfv032;'}
    proxies = None
    if cm.USE_PROXY:
        proxy_url = cm.get_proxy()
        proxies = {'http': proxy_url, 'https': proxy_url  }
    response = requests.get(url, headers=headers, proxies=proxies)
    soup = bs(response.text, 'html.parser')
    try:
        judical = [k for k in soup.find_all('div', {'class': 'dhtmlgoodies_aTab'}) if 'Judgement/Orders' in str(k)][0]
        data = judical.find_all('a')
        results = []
        for item in data:
            sol = {
                'pdf_link': 'https://mphc.gov.in' + str(item['href']).replace('./upload', '/upload'),
                'order_date': item.text.replace('Dt.', 'Date -')
            }
            results.append(sol)
        return {'result': results}

    except IndexError:
        return {"result": "error", "message": "No Record Found."}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scrape MPHC case orders using positional arguments")
    parser.add_argument('id', help='Bench ID')
    parser.add_argument('lst_case', help='Case type number')
    parser.add_argument('txt_no', help='Case number')
    parser.add_argument('year', help='Case year')
    args = parser.parse_args()
    output = fetch_case_data(args.id, args.lst_case, args.txt_no, args.year)
