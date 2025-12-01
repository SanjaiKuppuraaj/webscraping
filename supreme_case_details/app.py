from flask import Flask, Blueprint, jsonify, request
import json
import re
import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime
from common_code import common_module as cm

BASE_URL = 'https://www.sci.gov.in/wp-admin/admin-ajax.php'
LOG_FILE = cm.BASE_DIR_LOGS + '/'+datetime.now().strftime('%Y-%m-%d')+'/' +'supreme_case_details.txt'

supreme_case_bp = Blueprint('case', __name__)
def convert_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%d-%m-%Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""

def clean_list(lst):
    cleaned = [re.sub(r"<.*?>", "", x).strip() for x in lst]
    return [x for x in cleaned if x]

def fetch_soup(params: dict):
    response = requests.get(BASE_URL, params=params)
    data = response.json()['data']
    return bs(data, 'html.parser')

def write_log(diary_no, diary_year, status, error_msg=None):
    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{dt} | {diary_no}/{diary_year} | Status: {status}"
    if error_msg:
        log_entry += f" | Error: {error_msg}"
    log_entry += "\n"

    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)

def parse_case_details(diary_no: str, diary_year: str) -> dict:
    sol = {}
    response = fetch_soup(
        {'diary_no': diary_no, 'diary_year': diary_year, 'action': 'get_case_details', 'es_ajax_request': 1,
         'language': 'en'})
    tbody = response.find('table', {'class': 'caseDetailsTable no-responsive'}).find('tbody')

    dairy_num = [k.find_next('td') for k in response.find_all('td') if 'Diary Number' in str(k)][0]
    sol['case_status'] = dairy_num.find('div', {'class': ['push-right caseStatus p','push-right caseStatus d']}).text
    dairy_nums = dairy_num.find('font').text.split('/') if dairy_num else ''
    sol['diaryno'] = dairy_nums[0]
    sol['diaryyear'] = dairy_nums[1]
    times = [k.decompose() for k in dairy_num.find_all(['font', 'div']) if k]
    new_times = dairy_num.text.strip().replace('Filed on', '').strip().split(' ')[0]
    sol['case_filed_date'] = convert_date(new_times) if new_times else ''
    title_div = response.find('div', {'class': "mr-top15 text-center uppercase"})
    sol['case_title'] = title_div.find('h4').text.strip() if title_div else ''
    case_num = next(k.find_next('td') for k in tbody.find_all('td') if 'Case Number' in str(k)).text.split('Registered')[0].strip()
    sol['case_type'] = case_num.split('No.')[0] + 'No.'
    sol['case_no'] = case_num.replace(sol['case_type'], '').split('/')[0].strip()
    sol['case_year'] = case_num.replace(sol['case_type'], '').replace(sol['case_no'], '').replace('/', '').strip()
    status_td = next((k for k in tbody.find_all('td') if 'Status/Stage' in k.text), None)
    if status_td:
        next_td = status_td.find_next('td')
        if next_td and 'dt' in next_td.text:
            sol['case_stage'] = 'dt' + next_td.text.split('dt')[1]
        else:
            sol['case_stage'] = ''
    else:
        sol['case_stage'] = ''

    sol['caseno'] = f"{sol['case_type']}/{sol['case_no']}/{sol['case_year']}"
    sol['category'] = next(k.find_next('td') for k in tbody.find_all('td') if 'Category' in str(k)).text
    sol['petitioner'] = clean_list(str(next(k.find_next('td') for k in tbody.find_all('td') if 'Petitioner(s)' in str(k))).split('<br/>'))
    sol['respondent'] = clean_list(str(next(k.find_next('td') for k in tbody.find_all('td') if 'Respondent(s)' in str(k))).split('<br/>'))
    sol['petitioner_adv'] = clean_list( str(next(k.find_next('td') for k in tbody.find_all('td') if 'Petitioner Advocate(s)' in str(k))).replace('<font color="red">', '').replace('</font>', '').split('<br/>'))
    sol['respondent_adv'] = clean_list(str(next(k.find_next('td') for k in tbody.find_all('td') if 'Respondent Advocate(s)' in str(k))).split('<br/>'))
    return sol if sol else ''

def parse_connected_matters(diary_no: str, diary_year: str) -> list:
    tag_response = fetch_soup(
        {'diary_no': diary_no, 'diary_year': diary_year, 'tab_name': 'tagged_matters', 'action': 'get_case_details',
         'es_ajax_request': 1, 'language': 'en'})
    matters_list = []
    if tag_response.find('tbody'):
        for row in tag_response.find('tbody').find_all('tr'):
            cols = row.find_all('td')
            if not cols:
                continue
            mat = {}
            mat['type'] = cols[0].text
            diary_nums = cols[1].find('font').find_next('font').text.split('/')
            mat['conn_diaryno'], mat['conn_dairyyear'] = diary_nums
            pet_values = cols[2].text.strip().replace('\n', '').split('vs.')
            mat['con_petitioner'] = [pet_values[0].strip()]
            mat['con_respondent'] = [pet_values[1].strip()]
            mat['list'] = cols[3].text
            mat['status'] = cols[4].text
            mat['status_info'] = cols[5].text.replace('\n', '').strip()
            ia_details = [bs(k, 'html.parser').text.strip() for k in str(cols[6]).split('<br/>') if k.strip()]
            mat['ia_details'] = [f"{a} {b}" for a, b in zip(ia_details[::2], ia_details[1::2])]
            mat['connected_date'] = str(cols[7]).split('<br/>')[0].split('>')[-1]
            matters_list.append(mat)
    return matters_list if matters_list else ''

def parse_judgements(diary_no: str, diary_year: str) -> list:
    jud_response = fetch_soup(
        {'diary_no': diary_no, 'diary_year': diary_year, 'tab_name': 'judgement_orders', 'action': 'get_case_details',
         'es_ajax_request': 1, 'language': 'en'})
    jud_list = []
    if jud_response.find_all('tr'):
        for row in jud_response.find_all('tr'):
            link = row.find('a')
            if link:
                jud_list.append({'pdf_link': link['href'], 'order_date': link.text.strip()})
    return jud_list if jud_list else ''

def parse_listing_dates(diary_no: str, diary_year: str) -> list:
    listing_response = fetch_soup(
        {'diary_no': diary_no, 'diary_year': diary_year, 'tab_name': 'listing_dates', 'action': 'get_case_details',
         'es_ajax_request': 1, 'language': 'en'})
    listing_list = []
    if listing_response.find('tbody') :
        for row in listing_response.find('tbody').find_all('tr'):
            cols = row.find_all('td')
            if not cols:
                continue
            listing_list.append({
                'Hearing_Date': cols[0].text,
                'Misc./Regular': cols[1].text,
                'stage': cols[2].text.strip(),
                'purpose': cols[3].text,
                'proposed': cols[4].text.strip(),
                'coram': [j.strip() for k in cols[5].text.split(',') for j in k.split('and') if j.strip()],
                'ia': cols[6].text if len(cols) > 6 else '',
                'remarks': cols[7].text if len(cols) > 7 else '',
                'listed': cols[8].text if len(cols) > 8 else ''
            })
    return listing_list if listing_list else ''

@supreme_case_bp.route('', methods=['GET'])
def get_case_details():
    diary_no = request.args.get('diary_no')
    diary_year = request.args.get('diary_year')
    type_param = request.args.get('type', '').lower()

    if not diary_no or not diary_year:
        write_log(diary_no or "N/A", diary_year or "N/A", "Failed", "Missing diary_no or diary_year")
        return jsonify({'error': 'Please provide diary_no and diary_year'}), 400

    try:
        sol = parse_case_details(diary_no, diary_year)
        if not type_param or 'all' in type_param:
            sol['connected_matter'] = parse_connected_matters(diary_no, diary_year)
            sol['judgement'] = parse_judgements(diary_no, diary_year)
            sol['listing_details'] = parse_listing_dates(diary_no, diary_year)
        else:
            type_map = {
                'connected': parse_connected_matters,
                'judgement': parse_judgements,
                'listing': parse_listing_dates
            }
            types = [t.strip() for t in type_param.split(',') if t.strip()]
            for t in types:
                if t in type_map:
                    key_map = {'connected': 'connected_matter', 'judgement': 'judgement', 'listing': 'listing_details'}
                    sol[key_map[t]] = type_map[t](diary_no, diary_year)

        write_log(diary_no, diary_year, "Completed")
        return jsonify({'result': sol})

    except Exception as e:
        write_log(diary_no, diary_year, "Failed", str(e))
        return jsonify({'error': 'An error occurred while fetching case details', 'details': str(e)}), 500
