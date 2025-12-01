import sys
sys.path.insert(0, '/var/www/mml_python_code')
from flask import Blueprint, request, jsonify
import os, json, time, base64, datetime, requests
from bs4 import BeautifulSoup as bs
from playwright.sync_api import sync_playwright
import urllib3
from common_code import common_module as cm
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

json_output = '/var/www/mml_python_code/output/madras_causelist'
os.makedirs(json_output, exist_ok=True)

log_output = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
os.makedirs(log_output, exist_ok=True)

log_file = os.path.join(log_output, 'madras_high_court.txt')
if not os.path.exists(log_file):
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("Log initialized\n")

madras_bp = Blueprint('madras_bp', __name__)

def clean_html_list(html_list):
    clean_list = []
    for item in html_list:
        soup = bs(item, "html.parser")
        clean_list.append(soup.get_text(separator=' ', strip=True))
    return clean_list

def scraper(html):
    court_no_tag = html.find('tr', {'class': 'court_heading'}).find('span', {'class': 'court'})
    court_no = court_no_tag.text.strip() if court_no_tag else ''

    judge_name_tag = html.find('span', {'class': "head_judge"})
    judge_name = [k for k in clean_html_list(str(judge_name_tag).split('<br/>')) if k]

    rows = html.find_all('tr')
    current_matter_type = None
    last_sno = 0
    sub_sno_counter = 0
    matter_groups = []

    for row in rows:
        if 'stagename' in row.get('class', []):
            current_matter_type = row.get_text(strip=True)
            matter_groups.append({"matter_type": current_matter_type, "datas": []})
            continue
        if 'shown' not in row.get('class', []):
            continue

        sol = {}
        sno_td = row.find('td')
        sno_text = sno_td.text.strip() if sno_td else ''
        if sno_text:
            last_sno = sno_text
            sol['sno'] = last_sno
            sub_sno_counter = 0
        else:
            sub_sno_counter += 1
            sol['sno'] = f"{last_sno}.{sub_sno_counter}"

        case_no = sno_td.find_next('td') if sno_td else None
        case_num = case_no.text if case_no else ''
        sol['case_type'] = case_num.split(' ')[0] if case_num else ''
        sol['case_no'] = case_num.split(' ')[-1].split('/')[0] if case_num else ''
        sol['case_year'] = case_num.split(' ')[-1].split('/')[-1] if case_num else ''

        party_name = case_no.find_next('td') if case_no else None
        pet_resp = party_name.text.split('VS') if party_name else ['', '']
        sol['petitioner_name'] = [pet_resp[0].strip()]
        sol['respondent_name'] = [pet_resp[1].strip()] if len(pet_resp) > 1 else ''

        pet_adv = party_name.find_next('td') if party_name else None
        sol['petitioner_adv'] = [k.replace('  ', ' ').strip() for k in clean_html_list(str(pet_adv).split('<br/>')) if k] if pet_adv else []
        sol['respondent_adv'] = [k.replace('  ', ' ').strip() for k in clean_html_list(str(pet_adv.find_next('td')).split('<br/>')) if k] if pet_adv else []

        if current_matter_type and matter_groups:
            matter_groups[-1]["datas"].append(sol)
    return {"court_no": [court_no], "judge_name": judge_name, "clist": matter_groups}

def scrape_court_list(date, location):
    alter_date = datetime.strptime(date, '%d-%m-%Y').strftime('%Y-%m-%d')
    url = f'https://mhc.tn.gov.in/judis/clists/clists-{location}/courtlist.php'
    data = {'clistgroup': '1', 'ct_date': alter_date}
    response = requests.post(url, data=data, verify=False)
    soup = bs(response.text, 'html.parser')
    court_no_options = soup.find('select', {'id': 'courtnolist'}).find_all('option')
    court_no_list = [k.text.strip() for k in court_no_options if k.text.strip()]
    return court_no_list, alter_date

def merge_results(old_results, new_results):
    merged = old_results.copy()
    existing_cases = set()
    for item in old_results:
        for group in item.get('clist', []):
            for data in group.get('datas', []):
                key = (data['case_no'], data['case_year'], item['location'])
                existing_cases.add(key)

    for new_item in new_results:
        add_item = False
        for group in new_item.get("clist", []):
            for data in group.get("datas", []):
                key = (data['case_no'], data['case_year'], new_item['location'])
                if key not in existing_cases:
                    existing_cases.add(key)
                    add_item = True
        if add_item:
            merged.append(new_item)
    return merged

def run_madras_scraper(date, update=True):
    file_name = os.path.join(json_output, f"{date}.json")
    old_data = {}
    if os.path.exists(file_name):
        with open(file_name, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
    old_results = old_data.get("result", [])

    if not update:
        if old_results:
            return old_data
        else:
            return {"message": "No record found for this date"}

    locations = ['madras', 'madurai']
    all_results = []
    error_occurred = False

    with sync_playwright() as playwright:
        chromium = playwright.chromium
        browser = chromium.launch(headless=True)
        page = browser.new_page()

        for location in locations:
            court_no_list, alter_date = scrape_court_list(date, location)
            for cou_no in court_no_list:
                results_file = f'cause_{date.replace("-", "")}.xml'
                results_encoded = base64.b64encode(results_file.encode('utf-8')).decode('utf-8')
                date_encoded = base64.b64encode(alter_date.encode('utf-8')).decode('utf-8')
                url = f'https://mhc.tn.gov.in/judis/clists/clists-{location}/views/a.php?result={results_encoded}&cdate={date_encoded}&ft=1&fil={cou_no}'

                try:
                    page.goto(url, timeout=60000)
                    time.sleep(6)
                    html = bs(page.content(), 'html.parser')
                    tbody = html.find('tbody', {'id': 'tbl'})
                    if tbody:
                        court_data = scraper(tbody)
                        court_data["location"] = location
                        all_results.append(court_data)
                except Exception as e:
                    error_occurred = True
                    with open(log_file, 'a', encoding='utf-8') as lf:
                        lf.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] | {date} | Error | {cou_no} - {str(e)}\n")
                    continue

        browser.close()

    final_results = merge_results(old_results, all_results)
    total_count = sum(len(data.get("datas", [])) for court_item in final_results for data in court_item.get("clist", []))

    with open(log_file, 'a', encoding='utf-8') as lf:
        status = "Completed" if not error_occurred else "Completed with Errors"
        lf.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] | {date} | {status} | {total_count} cases\n")

    response_data = {"scrape_date": date, "total_count": total_count, "result": final_results}

    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(response_data, f, ensure_ascii=False, indent=2)

    return response_data

@madras_bp.route('', methods=['GET'])
def madras_causelist_route():
    date = request.args.get('date')
    update = request.args.get('update', 'false').lower() == 'true'
    if not date:
        return jsonify({"error": "Please provide date in DD-MM-YYYY format"}), 400

    result = run_madras_scraper(date, update)
    return jsonify(result)