from flask import Blueprint, jsonify, request
import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime
import traceback
from common_code import common_module as cm
import os

rct_rail_bp = Blueprint('rct_rail', __name__)

LOG_DIR = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "rct_rail.txt")

def log_case(case_number, status):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{time_stamp} | Case: {case_number} | Status: {status}\n")

def clean_list(items):
    return [bs(k, 'html.parser').text.strip() for k in items if k.strip()]

def fetch_case_details(case_number):
    session = requests.Session()
    url = 'https://rct.indianrail.gov.in/rct/case_position.jsp'
    main_case_type = str(case_number).split('/')
    payload = {"suitno": case_number,"rctval": "",
        "casetype": main_case_type[0],
        "rct": main_case_type[1],
        "caseno": main_case_type[2],
        "year": main_case_type[3],
        "mainCaptcha": "","txtInput": "", "Go": "Go"}
    headers = {'content-type': 'application/x-www-form-urlencoded','user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    response = session.post(url, data=payload, headers=headers)
    html = bs(response.text, 'html.parser')
    sol = {}

    if html.find('td', {'class': 'head'}):
        def get_val(label):
            return [k.find_next('td').text.strip() for k in html.find_all('td', {'class': 'head'}) if k.get_text(strip=True) == label][0]

        sol['case_fill_data'] = get_val('Case Filing Date')
        sol['case_registration_date'] = get_val('Case Registration Date')
        sol['cause'] = get_val('Cause')
        sol['sub_cause'] = get_val('Sub Cause')
        sol['filed_RCT'] = get_val('Filed in RCT')
        sol['amount_claim'] = get_val('Amount Claim Rs.')
        sol['date_of_accident'] = get_val('Date of Accident')
        sol['place_of_accident'] = get_val('Place of Accident')
        sol['from_station'] = get_val('From Station')
        sol['to_station'] = get_val('To Station')
        sol['victim_name'] = get_val('Victim Name')
        sol['victim_relation'] = get_val("Victim's Father/Husband Name")
        sol['applicant_name'] = get_val("Applicant Name & Address")
        sol['applicant_phone'] = get_val("Applicant Phone")
        sol['applicant_email'] = get_val("Applicant email")
        sol['applicant_adv_name'] = get_val("Applicant Advocate Name")

        response_name = [k.find_next('td') for k in html.find_all('td', {'class': 'head'}) if "Respondant name" in str(k)][0]
        response_name = [k for k in clean_list(str(response_name).split('<br/>')) if k]
        sol['respondant_name'] = response_name[0]
        sol['respondant_address'] = response_name[1]
        sol['resp_adv'] = get_val("Resp Advocate name")
        sol['resp_railway'] = get_val("Resp. Railway")

        hearing_detail = [k.find_all_next('tr') for k in html.find_all('th') if 'Hearing Detail' in str(k)][0]
        hearing_data = []
        for row in hearing_detail:
            tds = row.find_all('td', class_='txt')
            if len(tds) >= 3:
                hearing_data.append({'bench_hearing': tds[0].get_text(strip=True),
                    'hearing_date': tds[1].get_text(strip=True),
                    'hearing_purpose': tds[2].get_text(strip=True)})

        sol['hearing_detail'] = hearing_data
        judge_details = [k.find_next('tr').find('a')['href'] for k in html.find_all('th') if 'Judgment Detail' in str(k)]
        if judge_details:
            sol['judgment_detail'] = 'https://rct.indianrail.gov.in/rct/' + judge_details[0]
    else:
        sol = {'message': 'No Record Found', 'result': 'error'}

    return sol

@rct_rail_bp.route('', methods=['GET'])
def get_case():
    case_number = request.args.get('case_number')
    if not case_number:
        return jsonify({"error": "Missing case_number parameter"}), 400

    try:
        data = fetch_case_details(case_number)
        status = "completed" if "result" not in data or data["result"] != "error" else data["message"]
        log_case(case_number, status)
        return jsonify(data)
    except Exception as e:
        err_msg = f"Error: {str(e)} | Trace: {traceback.format_exc(limit=1)}"
        log_case(case_number, err_msg)
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500
