from flask import Blueprint, request, jsonify
import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime
from common_code import common_module as cm
from common_code import proxy_implement
import re
import os
aptel_bp = Blueprint('aptel', __name__)

CASE_AJAX_URL = "https://www.aptel.gov.in/en/casestatusapi/tab2?ajax_form=1&_wrapper_format=drupal_ajax"
DFR_AJAX_URL = "https://www.aptel.gov.in/en/casestatusapi?ajax_form=1&_wrapper_format=drupal_ajax"
case_type_option = {'APL': '1', 'OP': '4', 'EP': '5', 'RP': '6', 'CP': '7'}

proxy_mood = proxy_implement.get_requests_proxy()

session = requests.Session()
session.headers.update({"user-agent": "Mozilla/5.0"})

def log_case(case_identifier, case_status):
    log_dir = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'apt_log.txt')
    log_entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {case_identifier} | Status: {case_status}\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)

def clean_td(td):
    if td is None:
        return ''
    if isinstance(td, str):
        return td.strip()
    for card in td.find_all('div', class_='card'):
        card.decompose()
    return td.get_text(separator=' ', strip=True)
def extract_data_from_soup(soup, ci_url=''):
    sol = dict()
    soup = soup.find('table', {'class': "table table-bordered table-striped"})
    sol['cin'] = str(ci_url).split('/')[-1] if ci_url else ''
    dfr_no = [j for k in soup.find_all('tr') if 'DFR No' in str(k) for j in k.find_all('td') if j][1].text.split('/')
    sol['dfr_no'] = dfr_no[0]
    sol['dfr_year'] = dfr_no[1]
    case_details = [j for k in soup.find_all('tr') if 'Case Type/Case No' in str(k) for j in k.find_all('td') if j][1].text.split('/')

    case_type = case_details[0].split('-')
    sol['case_type'] = case_type[0] if case_type else ''
    sol['case_no'] = case_type[1] if len(case_type) > 1 else ''
    sol['case_year'] = case_details[1] if len(case_details) > 1 else ''
    # sol['date_of_filing'] = [j for k in soup.find_all('tr') if 'Date of Filing' in str(k) for j in k.find_all('td') if j][1].text
    raw_filing_date = [j for k in soup.find_all('tr') if 'Date of Filing' in str(k) for j in k.find_all('td') if j][1].text.strip()
    sol['case_filed_date'] = datetime.strptime(raw_filing_date, "%d/%m/%Y").strftime("%Y-%m-%d")

    sol['case_status'] = [j for k in soup.find_all('tr') if 'Case Status' in str(k) for j in k.find_all('td') if j][-1].text
    sol['next_bench_nature'] = [j for k in soup.find_all('tr') if 'Next Bench Nature' in str(k) for j in k.find_all('td') if j][1].text
    sol['next_court'] = [j for k in soup.find_all('tr') if 'Next Court' in str(k) for j in k.find_all('td') if j][1].text
    # sol['next_listing_date'] = [j for k in soup.find_all('tr') if 'Next Listing Date' in str(k) for j in k.find_all('td') if j][1].text
    next_listing_date =[j for k in soup.find_all('tr') if 'Next Listing Date' in str(k) for j in k.find_all('td') if j][1].text.strip()
    sol['next_listing_date'] = datetime.strptime(next_listing_date, "%d/%m/%Y").strftime("%Y-%m-%d")
    sol['next_listing_purpose'] = [j for k in soup.find_all('tr') if 'Next Listing Purpose' in str(k) for j in k.find_all('td') if j][1].text
    sol['ia_no'] = [j for k in soup.find_all('tr') if 'IA No' in str(k) for j in k.find_all('td') if j][1].text
    sol['petitioner'] = [ [j for k in soup.find_all('tr') if 'Appellant/Petitioner Name' in str(k) for j in k.find_all('td') if j][1].text.strip()]
    sol['petparty_name'] = [j for k in soup.find_all('tr') if 'Additional Party(Pet.)' in str(k) for j in k.find_all('td') if j][1].text.strip()
    pet_adv = [j for k in soup.find_all('tr') if 'Pet. Advocate Name' in str(k) for j in k.find_all('td') if j][1].text.strip()
    pet_adv = [k.strip() for k in pet_adv.split(',') if k] if len(pet_adv) > 1 else ''
    sol['pet_adv'] = [re.sub(r'\([A-Za-z0-9\-]+\)', '', name).strip() for name in pet_adv]
    additional_advocate_petitioner = [j for k in soup.find_all('tr') if 'Additional Advocate(Pet.)' in str(k) for j in k.find_all('td') if j][1]
    # sol['petNameAdd'] = list(dict.fromkeys([k.replace('<td colspan="3">', '').replace('</td>', '').strip() for k in  str(additional_advocate_petitioner).split('<br/>') if  k.replace('<td colspan="3">', '').replace('</td>', '').strip()]))
    pet_name = [j for k in soup.find_all('tr') if 'Appellant/Petitioner Name' in str(k) for j in k.find_all('td') if j][ 1].text.strip()
    respon_name = [j for k in soup.find_all('tr') if 'Respondent Name' in str(k) for j in k.find_all('td') if j][1].text
    sol['title'] = str(pet_name) + ' Vs ' + str(respon_name)
    sol['respondent'] = [[j for k in soup.find_all('tr') if 'Respondent Name' in str(k) for j in k.find_all('td') if j][1].text.strip()]
    sol['resparty_name'] = [j for k in soup.find_all('tr') if 'Additional Party(Res.)' in str(k) for j in k.find_all('td') if j][ 1].text.strip()

    res_adv = [j for k in soup.find_all('tr') if 'Respondent Advocate' in str(k) for j in k.find_all('td') if j][1].text.strip().split(',')
    res_adv = [k.strip() for k in res_adv if k]
    sol['res_adv'] = [re.sub(r'\([A-Za-z0-9\-]+\)', '', name).strip() for name in res_adv]

    additional_res_adv = [j for k in soup.find_all('tr') if 'Additional Advocate(Res.):' in str(k) for j in k.find_all('td') if j][1]
    # sol['resNameAdd'] = sorted( [s.strip() for s in str(additional_res_adv).replace('<td colspan="3">', '').replace('</td>', '').split('<br/>') if s.strip()])

    sol['next_hearing_date'] = {}
    bench_rows = [k.find_next('tr') for k in soup.find_all('tr') if 'Bench No' in str(k)]

    for idx, bench_tr in enumerate(bench_rows):
        tds = bench_tr.find_all('td')
        sol['next_hearing_date'][str(idx)] = {
            "bench_no": tds[0].text.strip() if len(tds) > 0 else '',
            "next_hearing": tds[1].text.strip() if len(tds) > 1 else '',
            "purpose": tds[2].text.strip() if len(tds) > 2 else '',
            "stage": tds[3].text.strip() if len(tds) > 3 else '',
            "order_link": tds[4].find('a')['href'].strip() if len(tds) > 4 and tds[4].find('a') else ''
        }

    return sol

# def extract_data_from_soup(soup, ci_url=''):
#     sol = dict()
#     soup = soup.find('table', {'class': "table table-bordered table-striped"})
#     sol['cin'] = str(ci_url).split('/')[-1] if ci_url else ''
#     dfr_no = [j for k in soup.find_all('tr') if 'DFR No' in str(k) for j in k.find_all('td') if j][1].text.split('/')
#     sol['dfr_no'] = dfr_no[0]
#     sol['dfr_year'] = dfr_no[1]
#     case_details = [j for k in soup.find_all('tr') if 'Case Type/Case No' in str(k) for j in k.find_all('td') if j][1].text.split('/')
#
#     case_type = case_details[0].split('-')
#     sol['case_type'] = case_type[0] if case_type else ''
#     sol['case_no'] = case_type[1] if len(case_type) > 1 else ''
#     sol['case_year'] = case_details[1] if len(case_details) > 1 else ''
#     # sol['date_of_filing'] = [j for k in soup.find_all('tr') if 'Date of Filing' in str(k) for j in k.find_all('td') if j][1].text
#     raw_filing_date = [j for k in soup.find_all('tr') if 'Date of Filing' in str(k) for j in k.find_all('td') if j][1].text.strip()
#     sol['case_filed_date'] = datetime.strptime(raw_filing_date, "%d/%m/%Y").strftime("%Y-%m-%d")
#
#     sol['case_status'] = [j for k in soup.find_all('tr') if 'Case Status' in str(k) for j in k.find_all('td') if j][-1].text
#     sol['next_bench_nature'] = [j for k in soup.find_all('tr') if 'Next Bench Nature' in str(k) for j in k.find_all('td') if j][1].text
#     sol['next_court'] = [j for k in soup.find_all('tr') if 'Next Court' in str(k) for j in k.find_all('td') if j][1].text
#     # sol['next_listing_date'] = [j for k in soup.find_all('tr') if 'Next Listing Date' in str(k) for j in k.find_all('td') if j][1].text
#     next_listing_date =[j for k in soup.find_all('tr') if 'Next Listing Date' in str(k) for j in k.find_all('td') if j][1].text.strip()
#     sol['next_listing_date'] = datetime.strptime(next_listing_date, "%d/%m/%Y").strftime("%Y-%m-%d")
#     sol['next_listing_purpose'] = [j for k in soup.find_all('tr') if 'Next Listing Purpose' in str(k) for j in k.find_all('td') if j][1].text
#     sol['ia_no'] = [j for k in soup.find_all('tr') if 'IA No' in str(k) for j in k.find_all('td') if j][1].text
#     sol['petitioner'] = [ [j for k in soup.find_all('tr') if 'Appellant/Petitioner Name' in str(k) for j in k.find_all('td') if j][1].text.strip()]
#     sol['petparty_name'] = [j for k in soup.find_all('tr') if 'Additional Party(Pet.)' in str(k) for j in k.find_all('td') if j][1].text.strip()
#     pet_adv = [j for k in soup.find_all('tr') if 'Pet. Advocate Name' in str(k) for j in k.find_all('td') if j][1].text.strip()
#     sol['pet_adv'] = [k.strip() for k in pet_adv.split(',') if k] if len(pet_adv) > 1 else ''
#     # sol['pet_adv'] = [j for k in soup.find_all('tr') if 'Pet. Advocate Name' in str(k) for j in k.find_all('td') if j][1].text.strip()
#     additional_advocate_petitioner = [j for k in soup.find_all('tr') if 'Additional Advocate(Pet.)' in str(k) for j in k.find_all('td') if j][1]
#     sol['petNameAdd'] = list(dict.fromkeys([k.replace('<td colspan="3">', '').replace('</td>', '').strip() for k in  str(additional_advocate_petitioner).split('<br/>') if  k.replace('<td colspan="3">', '').replace('</td>', '').strip()]))
#     pet_name = [j for k in soup.find_all('tr') if 'Appellant/Petitioner Name' in str(k) for j in k.find_all('td') if j][ 1].text.strip()
#     respon_name = [j for k in soup.find_all('tr') if 'Respondent Name' in str(k) for j in k.find_all('td') if j][1].text
#     sol['title'] = str(pet_name) + ' Vs ' + str(respon_name)
#     sol['respondent'] = [[j for k in soup.find_all('tr') if 'Respondent Name' in str(k) for j in k.find_all('td') if j][1].text.strip()]
#     sol['resparty_name'] = [j for k in soup.find_all('tr') if 'Additional Party(Res.)' in str(k) for j in k.find_all('td') if j][ 1].text.strip()
#     sol['res_adv'] = [j for k in soup.find_all('tr') if 'Respondent Advocate' in str(k) for j in k.find_all('td') if j][1].text.strip()
#     additional_res_adv = [j for k in soup.find_all('tr') if 'Additional Advocate(Res.):' in str(k) for j in k.find_all('td') if j][1]
#     sol['resNameAdd'] = sorted( [s.strip() for s in str(additional_res_adv).replace('<td colspan="3">', '').replace('</td>', '').split('<br/>') if s.strip()])
#
#     sol['next_hearing_date'] = {}
#     bench_rows = [k.find_next('tr') for k in soup.find_all('tr') if 'Bench No' in str(k)]
#
#     for idx, bench_tr in enumerate(bench_rows):
#         tds = bench_tr.find_all('td')
#         sol['next_hearing_date'][str(idx)] = {
#             "bench_no": tds[0].text.strip() if len(tds) > 0 else '',
#             "next_hearing": tds[1].text.strip() if len(tds) > 1 else '',
#             "purpose": tds[2].text.strip() if len(tds) > 2 else '',
#             "stage": tds[3].text.strip() if len(tds) > 3 else '',
#             "order_link": tds[4].find('a')['href'].strip() if len(tds) > 4 and tds[4].find('a') else ''
#         }
#
#     return sol

def scrape_by_cino(ci_no):
    if not ci_no:
        return {}
    ci_url = f"https://www.aptel.gov.in/en/caseapidetails/{ci_no}"
    response = session.get(ci_url,proxies=proxy_mood)
    if response.status_code != 200:
        return {}
    soup = bs(response.text, 'html.parser')
    return extract_data_from_soup(soup, ci_url)

def scrape_using_ajax(payload, url):
    response = session.post(url, data=payload)
    try:
        json_data = response.json()
        html_data = json_data[2]['data']
        soup = bs(html_data, 'html.parser')
        table = soup.find("table", {'class': "table table-bordered table-striped"})
        if not table:
            return {"error": "No matching case found for given parameters"}
        ci_no = table.find('a')['href'].split('/')[-1]
        return scrape_by_cino(ci_no)
    except:
        soup = bs(response.text, 'html.parser')
        notice = soup.find('div', {'class': 'messages'})
        if notice:
            return {"error": clean_td(notice)}
        return {"error": "Invalid response from APTEL server, possibly case not found."}


def scrape_case(case_type, case_no, case_year):
    if not (case_type and case_no and case_year):
        return {}
    resp = session.get('https://www.aptel.gov.in/en/casestatusapi/tab2')
    soup = bs(resp.text, 'html.parser')
    form_build_id_tag = soup.find('input', {'name': 'form_build_id'})
    if not form_build_id_tag or case_type not in case_type_option:
        return {}
    payload = {
        'form_build_id': form_build_id_tag['value'],
        'form_id': 'case_order_casenowise_form',
        'case_type': case_type_option[case_type],
        'case_no': case_no,
        'diary_year': case_year,
        '_triggering_element_name': 'op',
        '_triggering_element_value': 'Submit',
        '_drupal_ajax': '1',
        'ajax_page_state[theme]': 'delhi_gov',
        'ajax_page_state[theme_token]': '',
        'ajax_page_state[libraries]': ''
    }
    return scrape_using_ajax(payload, CASE_AJAX_URL)


def scrape_by_dfr(dfr_no, dfr_year):
    if not (dfr_no and dfr_year):
        return {}
    resp = session.get('https://www.aptel.gov.in/en/casestatusapi')
    soup = bs(resp.text, 'html.parser')
    form_build_id_tag = soup.find('input', {'name': 'form_build_id'})
    if not form_build_id_tag:
        return {}
    payload = {
        'form_build_id': form_build_id_tag['value'],
        'form_id': 'Case_order_dfrnowise_form',
        'diary_no': dfr_no,
        'diary_year': dfr_year,
        '_triggering_element_name': 'op',
        '_triggering_element_value': 'Submit',
        '_drupal_ajax': '1',
        'ajax_page_state[theme]': 'delhi_gov',
        'ajax_page_state[theme_token]': '',
        'ajax_page_state[libraries]': ''
    }
    return scrape_using_ajax(payload, DFR_AJAX_URL)

@aptel_bp.route('', methods=['GET'])
def api_scrape():
    ci_no = request.args.get('cin')
    dfr_no = request.args.get('dfr_no')
    case_type = request.args.get('case_type')
    case_no = request.args.get('case_no')
    case_year = request.args.get('case_year')

    if ci_no:
        data = scrape_by_cino(ci_no)
    elif dfr_no and case_year:
        data = scrape_by_dfr(dfr_no, case_year)
    elif case_type and case_no and case_year:
        data = scrape_case(case_type, case_no, case_year)
    else:
        return jsonify({"result": "error", "message": "Insufficient parameters"}), 400

    if not data or "error" in data:
        return jsonify({"result": "error", "message": data.get("error", "No data found")}), 404

    case_identifier = data.get('cin') or f"{data.get('case_type', '')}/{data.get('case_no', '')}/{data.get('case_year', '')}"
    case_status = data.get('case_status', 'Unknown')
    log_case(case_identifier, case_status)

    return jsonify({"result": data})





















# from flask import Blueprint, request, jsonify
# import requests
# from bs4 import BeautifulSoup as bs
# from datetime import datetime
# from common_code import common_module as cm
# from common_code import proxy_implement
# import os
# aptel_bp = Blueprint('aptel', __name__)
#
# CASE_AJAX_URL = "https://www.aptel.gov.in/en/casestatusapi/tab2?ajax_form=1&_wrapper_format=drupal_ajax"
# DFR_AJAX_URL = "https://www.aptel.gov.in/en/casestatusapi?ajax_form=1&_wrapper_format=drupal_ajax"
# case_type_option = {'APL': '1', 'OP': '4', 'EP': '5', 'RP': '6', 'CP': '7'}
#
# proxy_mood = proxy_implement.get_requests_proxy()
#
# session = requests.Session()
# session.headers.update({"user-agent": "Mozilla/5.0"})
#
# def log_case(case_identifier, case_status):
#     log_dir = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
#     os.makedirs(log_dir, exist_ok=True)
#     log_file = os.path.join(log_dir, 'apt_log.txt')
#     log_entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {case_identifier} | Status: {case_status}\n"
#     with open(log_file, "a", encoding="utf-8") as f:
#         f.write(log_entry)
#
# def clean_td(td):
#     if td is None:
#         return ''
#     if isinstance(td, str):
#         return td.strip()
#     for card in td.find_all('div', class_='card'):
#         card.decompose()
#     return td.get_text(separator=' ', strip=True)
#
# def extract_data_from_soup(soup, ci_url=''):
#     sol = dict()
#     soup = soup.find('table', {'class': "table table-bordered table-striped"})
#     sol['cin'] = str(ci_url).split('/')[-1] if ci_url else ''
#     dfr_no = [j for k in soup.find_all('tr') if 'DFR No' in str(k) for j in k.find_all('td') if j][1].text.split('/')
#     sol['dfr_no'] = dfr_no[0]
#     sol['dfr_year'] = dfr_no[1]
#     case_details = [j for k in soup.find_all('tr') if 'Case Type/Case No' in str(k) for j in k.find_all('td') if j][
#         1].text.split('/')
#
#     case_type = case_details[0].split('-')
#     sol['case_type'] = case_type[0] if case_type else ''
#     sol['case_no'] = case_type[1] if len(case_type) > 1 else ''
#     sol['case_year'] = case_details[1] if len(case_details) > 1 else ''
#     # sol['date_of_filing'] = [j for k in soup.find_all('tr') if 'Date of Filing' in str(k) for j in k.find_all('td') if j][1].text
#     raw_filing_date = [j for k in soup.find_all('tr') if 'Date of Filing' in str(k) for j in k.find_all('td') if j][
#         1].text.strip()
#     sol['case_filed_date'] = datetime.strptime(raw_filing_date, "%d/%m/%Y").strftime("%Y-%m-%d")
#
#     sol['case_status'] = [j for k in soup.find_all('tr') if 'Case Status' in str(k) for j in k.find_all('td') if j][
#         -1].text
#     sol['next_bench_nature'] = \
#     [j for k in soup.find_all('tr') if 'Next Bench Nature' in str(k) for j in k.find_all('td') if j][1].text
#     sol['next_court'] = [j for k in soup.find_all('tr') if 'Next Court' in str(k) for j in k.find_all('td') if j][
#         1].text
#     # sol['next_listing_date'] = [j for k in soup.find_all('tr') if 'Next Listing Date' in str(k) for j in k.find_all('td') if j][1].text
#     next_listing_date = \
#     [j for k in soup.find_all('tr') if 'Next Listing Date' in str(k) for j in k.find_all('td') if j][1].text.strip()
#     sol['next_listing_date'] = datetime.strptime(next_listing_date, "%d/%m/%Y").strftime("%Y-%m-%d")
#     sol['next_listing_purpose'] = \
#     [j for k in soup.find_all('tr') if 'Next Listing Purpose' in str(k) for j in k.find_all('td') if j][1].text
#     sol['ia_no'] = [j for k in soup.find_all('tr') if 'IA No' in str(k) for j in k.find_all('td') if j][1].text
#     sol['petitioner'] = [
#         [j for k in soup.find_all('tr') if 'Appellant/Petitioner Name' in str(k) for j in k.find_all('td') if j][
#             1].text.strip()]
#     sol['petparty_name'] = \
#     [j for k in soup.find_all('tr') if 'Additional Party(Pet.)' in str(k) for j in k.find_all('td') if j][
#         1].text.strip()
#     pet_adv = [j for k in soup.find_all('tr') if 'Pet. Advocate Name' in str(k) for j in k.find_all('td') if j][
#         1].text.strip()
#     sol['pet_adv'] = [k.strip() for k in pet_adv.split(',') if k] if len(pet_adv) > 1 else ''
#     # sol['pet_adv'] = [j for k in soup.find_all('tr') if 'Pet. Advocate Name' in str(k) for j in k.find_all('td') if j][1].text.strip()
#     additional_advocate_petitioner = \
#     [j for k in soup.find_all('tr') if 'Additional Advocate(Pet.)' in str(k) for j in k.find_all('td') if j][1]
#     sol['petNameAdd'] = list(dict.fromkeys([k.replace('<td colspan="3">', '').replace('</td>', '').strip() for k in
#                                             str(additional_advocate_petitioner).split('<br/>') if
#                                             k.replace('<td colspan="3">', '').replace('</td>', '').strip()]))
#     pet_name = [j for k in soup.find_all('tr') if 'Appellant/Petitioner Name' in str(k) for j in k.find_all('td') if j][
#         1].text.strip()
#     respon_name = [j for k in soup.find_all('tr') if 'Respondent Name' in str(k) for j in k.find_all('td') if j][1].text
#     sol['title'] = str(pet_name) + ' Vs ' + str(respon_name)
#     sol['respondent'] = [
#         [j for k in soup.find_all('tr') if 'Respondent Name' in str(k) for j in k.find_all('td') if j][1].text.strip()]
#     sol['resparty_name'] = \
#     [j for k in soup.find_all('tr') if 'Additional Party(Res.)' in str(k) for j in k.find_all('td') if j][
#         1].text.strip()
#     sol['res_adv'] = [j for k in soup.find_all('tr') if 'Respondent Advocate' in str(k) for j in k.find_all('td') if j][
#         1].text.strip()
#     additional_res_adv = \
#     [j for k in soup.find_all('tr') if 'Additional Advocate(Res.):' in str(k) for j in k.find_all('td') if j][1]
#     sol['resNameAdd'] = sorted(
#         [s.strip() for s in str(additional_res_adv).replace('<td colspan="3">', '').replace('</td>', '').split('<br/>')
#          if s.strip()])
#
#     sol['next_hearing_date'] = {}
#     bench_rows = [k.find_next('tr') for k in soup.find_all('tr') if 'Bench No' in str(k)]
#
#     for idx, bench_tr in enumerate(bench_rows):
#         tds = bench_tr.find_all('td')
#         sol['next_hearing_date'][str(idx)] = {
#             "bench_no": tds[0].text.strip() if len(tds) > 0 else '',
#             "next_hearing": tds[1].text.strip() if len(tds) > 1 else '',
#             "purpose": tds[2].text.strip() if len(tds) > 2 else '',
#             "stage": tds[3].text.strip() if len(tds) > 3 else '',
#             "order_link": tds[4].find('a')['href'].strip() if len(tds) > 4 and tds[4].find('a') else ''
#         }
#
#     return sol
#
# def scrape_by_cino(ci_no):
#     if not ci_no:
#         return {}
#     ci_url = f"https://www.aptel.gov.in/en/caseapidetails/{ci_no}"
#     response = session.get(ci_url)
#     if response.status_code != 200:
#         return {}
#     soup = bs(response.text, 'html.parser')
#     return extract_data_from_soup(soup, ci_url)
#
# def scrape_using_ajax(payload, url):
#     response = session.post(url, data=payload,proxies=proxy_mood)
#     try:
#         json_data = response.json()
#         html_data = json_data[2]['data']
#         soup = bs(html_data, 'html.parser')
#         table = soup.find("table", {'class': "table table-bordered table-striped"})
#         if not table:
#             return {"error": "No matching case found for given parameters"}
#         ci_no = table.find('a')['href'].split('/')[-1]
#         return scrape_by_cino(ci_no)
#     except:
#         soup = bs(response.text, 'html.parser')
#         notice = soup.find('div', {'class': 'messages'})
#         if notice:
#             return {"error": clean_td(notice)}
#         return {"error": "Invalid response from APTEL server, possibly case not found."}
#
#
# def scrape_case(case_type, case_no, case_year):
#     if not (case_type and case_no and case_year):
#         return {}
#     resp = session.get('https://www.aptel.gov.in/en/casestatusapi/tab2',proxies=proxy_mood)
#     soup = bs(resp.text, 'html.parser')
#     form_build_id_tag = soup.find('input', {'name': 'form_build_id'})
#     if not form_build_id_tag or case_type not in case_type_option:
#         return {}
#     payload = {
#         'form_build_id': form_build_id_tag['value'],
#         'form_id': 'case_order_casenowise_form',
#         'case_type': case_type_option[case_type],
#         'case_no': case_no,
#         'diary_year': case_year,
#         '_triggering_element_name': 'op',
#         '_triggering_element_value': 'Submit',
#         '_drupal_ajax': '1',
#         'ajax_page_state[theme]': 'delhi_gov',
#         'ajax_page_state[theme_token]': '',
#         'ajax_page_state[libraries]': ''
#     }
#     return scrape_using_ajax(payload, CASE_AJAX_URL)
#
#
# def scrape_by_dfr(dfr_no, dfr_year):
#     if not (dfr_no and dfr_year):
#         return {}
#     resp = session.get('https://www.aptel.gov.in/en/casestatusapi',proxies=proxy_mood)
#     soup = bs(resp.text, 'html.parser')
#     form_build_id_tag = soup.find('input', {'name': 'form_build_id'})
#     if not form_build_id_tag:
#         return {}
#     payload = {
#         'form_build_id': form_build_id_tag['value'],
#         'form_id': 'Case_order_dfrnowise_form',
#         'diary_no': dfr_no,
#         'diary_year': dfr_year,
#         '_triggering_element_name': 'op',
#         '_triggering_element_value': 'Submit',
#         '_drupal_ajax': '1',
#         'ajax_page_state[theme]': 'delhi_gov',
#         'ajax_page_state[theme_token]': '',
#         'ajax_page_state[libraries]': ''
#     }
#     return scrape_using_ajax(payload, DFR_AJAX_URL)
#
# @aptel_bp.route('', methods=['GET'])
# def api_scrape():
#     ci_no = request.args.get('cin')
#     dfr_no = request.args.get('dfr_no')
#     case_type = request.args.get('case_type')
#     case_no = request.args.get('case_no')
#     case_year = request.args.get('case_year')
#
#     if ci_no:
#         data = scrape_by_cino(ci_no)
#     elif dfr_no and case_year:
#         data = scrape_by_dfr(dfr_no, case_year)
#     elif case_type and case_no and case_year:
#         data = scrape_case(case_type, case_no, case_year)
#     else:
#         return jsonify({"result": "error", "message": "Insufficient parameters"}), 400
#
#     if not data or "error" in data:
#         return jsonify({"result": "error", "message": data.get("error", "No data found")}), 404
#
#     case_identifier = data.get('cin') or f"{data.get('case_type', '')}/{data.get('case_no', '')}/{data.get('case_year', '')}"
#     case_status = data.get('case_status', 'Unknown')
#     log_case(case_identifier, case_status)
#
#     return jsonify({"result": data})
