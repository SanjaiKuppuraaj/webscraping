from flask import Blueprint, request, jsonify
import subprocess
import os
import json
from bs4 import BeautifulSoup as bs
from datetime import datetime
from common_code import common_module as cm

mp_casestatus_bp = Blueprint("mp_casestatus", __name__)

DATA_DIR_output = os.path.join(cm.BASE_DIR_OUTPUTS, 'hcmp_casestatus')
os.makedirs(DATA_DIR_output, exist_ok=True)

data_log = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
os.makedirs(data_log, exist_ok=True)

def bench_name(code):
    return {"01": "jabalpur", "02": "indore", "03": "gwalior"}.get(code, code)

def log_status(bench, pet_res, partyname, case_year, status, result):
    log_entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {bench}/{pet_res}/{partyname}/{case_year}/{status} | Status: {result}\n"
    log_path = os.path.join(data_log, "mp_casestatus_log.txt")
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(log_entry)

def parse_html_to_json(html_content):
    soup = bs(html_content, 'html.parser')
    rows = soup.find('tbody').find_all('tr')
    all_cases = []

    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 5:
            continue
        sol = {}
        sol['sno'] = cols[0].get_text(strip=True)
        case_parts = list(cols[1].stripped_strings)
        if len(case_parts) >= 3:
            try:
                case_type, case_num_year = case_parts[0].strip().split(' ', 1)
                case_num, case_year = case_num_year.strip().split('/')
            except ValueError:
                case_type = case_parts[0].strip()
                case_num = case_year = ''
            sol['case_type'] = case_type
            sol['case_no'] = case_num
            sol['case_year'] = case_year
            sol['cases'] = f"{case_type}-{case_num}-{case_year}"
        else:
            sol['case_type'] = sol['case_no'] = sol['case_year'] = sol['cases'] = ''

        sol['district'] = case_parts[1] if len(case_parts) > 1 else ''
        sol['filing_date'] = case_parts[-2] if len(case_parts) > 2 else ''
        sol['status'] = case_parts[-1] if len(case_parts) > 2 else ''

        party_info_raw = cols[2].get_text(separator='|', strip=True)
        party_map = {'petitioner': [], 'petitioner_advocate': [], 'respondant': [], 'respondant_advocate': []}

        for segment in party_info_raw.split('|'):
            segment = segment.strip()
            if 'Petitioner:' in segment:
                party_map['petitioner'] = [x.strip() for x in segment.partition(':')[2].split(',') if x.strip()]
            elif 'Petitioner Advocates:' in segment:
                party_map['petitioner_advocate'] = [x.strip() for x in segment.partition(':')[2].split(',') if x.strip()]
            elif 'Respondants:' in segment or 'Respondent:' in segment:
                party_map['respondant'] = [x.strip() for x in segment.partition(':')[2].split(',') if x.strip()]
            elif 'Res. Advocates:' in segment:
                party_map['respondant_advocate'] = [x.strip() for x in segment.partition(':')[2].split(',') if x.strip()]
        sol.update(party_map)
        sol['category'] = cols[3].get_text(strip=True)
        sol['next_hearing_date'] = cols[4].get_text(strip=True)
        all_cases.append(sol)

    return all_cases

@mp_casestatus_bp.route("", methods=["GET", "POST"])
def mp_casestatus_auto():
    data = request.form if request.method == "POST" else request.args

    bench = data.get("bench", "").strip()
    partyname = data.get("partyname", "").strip()
    case_year = data.get("case_year", "").strip()
    pet_res = data.get("pet_res", "").strip()
    status = data.get("status", "").strip()

    if not bench or not partyname or not case_year or not pet_res or not status:
        return jsonify({"error": "bench, partyname, case_year, pet_res, and status are all required."}), 400

    try:
        SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "hcmp_casestatus.py")
        result = subprocess.run(
            ["python3", SCRIPT_PATH, bench, partyname, case_year, pet_res, status],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        if result.returncode != 0:
            error_message = result.stderr.strip()
            log_status(bench, pet_res, partyname, case_year, status, f"Failed: {error_message}")
            return jsonify({"error": f"Scraper failed: {error_message}"}), 500

        html_output = result.stdout.strip()
        all_cases = parse_html_to_json(html_output)

        filename = f"{bench_name(bench)}_{pet_res}_{partyname}_{case_year}_{status}.json"
        filepath = os.path.join(DATA_DIR_output, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({'result': all_cases}, f, indent=2, ensure_ascii=False)

        filtered = []
        for case in all_cases:
            case_str = json.dumps(case, ensure_ascii=False).lower()
            if partyname.lower() not in case_str:
                continue
            if case.get("case_year") != case_year:
                continue
            filtered.append(case)

        log_status(bench, pet_res, partyname, case_year, status, f"{len(filtered)} cases found")
        return jsonify({"result": filtered})

    except Exception as e:
        log_status(bench, pet_res, partyname, case_year, status, f"Exception: {str(e)}")
        return jsonify({"error": str(e)}), 500














# import sys
# sys.path.insert(0, '/var/www/mml_python_code')
#
# from flask import Blueprint, request, jsonify
# import subprocess
# import os
# import json
# from bs4 import BeautifulSoup as bs
# from datetime import datetime
# from common_code import common_module as cm
#
# mp_casestatus_bp = Blueprint("mp_casestatus", __name__)
#
# DATA_DIR_output = os.path.join(cm.BASE_DIR_OUTPUTS, 'hcmp_casestatus')
# os.makedirs(DATA_DIR_output, exist_ok=True)
#
# data_log = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
# os.makedirs(data_log, exist_ok=True)
#
# def bench_name(code):
#     return {"01": "jabalpur", "02": "indore", "03": "gwalior"}.get(code, code)
#
# def log_status(bench, pet_res, partyname, case_year, status, result):
#     log_entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {bench}/{pet_res}/{partyname}/{case_year}/{status} | Status: {result}\n"
#     log_path = os.path.join(data_log, "mp_casestatus_log.txt")
#     with open(log_path, "a", encoding="utf-8") as log_file:
#         log_file.write(log_entry)
#
# def parse_html_to_json(html_content):
#     soup = bs(html_content, 'html.parser')
#     rows = soup.find('tbody').find_all('tr')
#     all_cases = []
#
#     for row in rows:
#         cols = row.find_all('td')
#         if len(cols) < 5:
#             continue
#         sol = {}
#         sol['sno'] = cols[0].get_text(strip=True)
#         case_parts = list(cols[1].stripped_strings)
#         if len(case_parts) >= 3:
#             try:
#                 case_type, case_num_year = case_parts[0].strip().split(' ', 1)
#                 case_num, case_year = case_num_year.strip().split('/')
#             except ValueError:
#                 case_type = case_parts[0].strip()
#                 case_num = case_year = ''
#             sol['case_type'] = case_type
#             sol['case_no'] = case_num
#             sol['case_year'] = case_year
#             sol['cases'] = f"{case_type}-{case_num}-{case_year}"
#         else:
#             sol['case_type'] = sol['case_no'] = sol['case_year'] = sol['cases'] = ''
#
#         sol['district'] = case_parts[1] if len(case_parts) > 1 else ''
#         sol['filing_date'] = case_parts[-2] if len(case_parts) > 2 else ''
#         sol['status'] = case_parts[-1] if len(case_parts) > 2 else ''
#
#         party_info_raw = cols[2].get_text(separator='|', strip=True)
#         party_map = {'petitioner': [], 'petitioner_advocate': [], 'respondant': [], 'respondant_advocate': []}
#
#         for segment in party_info_raw.split('|'):
#             segment = segment.strip()
#             if 'Petitioner:' in segment:
#                 party_map['petitioner'] = [x.strip() for x in segment.partition(':')[2].split(',') if x.strip()]
#             elif 'Petitioner Advocates:' in segment:
#                 party_map['petitioner_advocate'] = [x.strip() for x in segment.partition(':')[2].split(',') if x.strip()]
#             elif 'Respondants:' in segment or 'Respondent:' in segment:
#                 party_map['respondant'] = [x.strip() for x in segment.partition(':')[2].split(',') if x.strip()]
#             elif 'Res. Advocates:' in segment:
#                 party_map['respondant_advocate'] = [x.strip() for x in segment.partition(':')[2].split(',') if x.strip()]
#         sol.update(party_map)
#         sol['category'] = cols[3].get_text(strip=True)
#         sol['next_hearing_date'] = cols[4].get_text(strip=True)
#         all_cases.append(sol)
#
#     return all_cases
#
# @mp_casestatus_bp.route("", methods=["GET", "POST"])
# def mp_casestatus_auto():
#     data = request.form if request.method == "POST" else request.args
#
#     bench = data.get("bench", "").strip()
#     partyname = data.get("partyname", "").strip()
#     case_year = data.get("case_year", "").strip()
#     pet_res = data.get("pet_res", "").strip()
#     status = data.get("status", "").strip()
#
#     if not bench or not partyname or not case_year or not pet_res or not status:
#         return jsonify({"error": "bench, partyname, case_year, pet_res, and status are all required."}), 400
#
#     try:
#         SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "hcmp_casestatus.py")
#         result = subprocess.run(
#             ["python3", SCRIPT_PATH, bench, partyname, case_year, pet_res, status],
#             capture_output=True,
#             text=True,
#             encoding="utf-8"
#         )
#         if result.returncode != 0:
#             error_message = result.stderr.strip()
#             log_status(bench, pet_res, partyname, case_year, status, f"Failed: {error_message}")
#             return jsonify({"error": f"Scraper failed: {error_message}"}), 500
#
#         html_output = result.stdout.strip()
#         all_cases = parse_html_to_json(html_output)
#
#         filename = f"{bench_name(bench)}_{pet_res}_{partyname}_{case_year}_{status}.json"
#         filepath = os.path.join(DATA_DIR_output, filename)
#         with open(filepath, "w", encoding="utf-8") as f:
#             json.dump({'result': all_cases}, f, indent=2, ensure_ascii=False)
#
#         filtered = []
#         for case in all_cases:
#             case_str = json.dumps(case, ensure_ascii=False).lower()
#             if partyname.lower() not in case_str:
#                 continue
#             if case.get("case_year") != case_year:
#                 continue
#             filtered.append(case)
#
#         log_status(bench, pet_res, partyname, case_year, status, f"{len(filtered)} cases found")
#         return jsonify({"result": filtered})
#
#     except Exception as e:
#         log_status(bench, pet_res, partyname, case_year, status, f"Exception: {str(e)}")
#         return jsonify({"error": str(e)}), 500
