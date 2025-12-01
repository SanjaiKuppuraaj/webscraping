import os
import re
import time
import json
import random
import traceback
from datetime import datetime
from io import BytesIO
from bs4 import BeautifulSoup as bs
from requests.auth import HTTPProxyAuth
import requests
from common_code import common_module as cm
from common_code import proxy_implement as proxy
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

mfb_map = {"1": "M", "4": "L", "5": "S"}
sdbench_map = {"1": "Single Bench", "2": "Division Bench", "3": "Full Bench"}
city_map = {"01": "JBP", "02": "IND", "03": "GWL"}

city_full_map = {"JBP": "jabalpur", "IND": "indore", "GWL": "gwalior"}
mfb_full_map = {"M": "motion", "L": "lok_adalat", "S": "mediation"}

def write_log(city, bench, mfb, date, status, ip):
    log_folder = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(log_folder, exist_ok=True)
    log_file = os.path.join(log_folder, "mp_causelist.txt")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {city}/{bench}/{mfb}/{date} | Status: {status} | IP: {ip}\n"
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(log_line)

def get_ip(session):
    try:
        res = session.get("https://api.ipify.org", timeout=10)
        return res.text.strip()
    except:
        return "Unavailable"

def get_valid_session(max_retries=5):
    for _ in range(max_retries):
        try:
            session = requests.Session()
            proxies = proxy.get_requests_proxy()
            session.proxies.update(proxies)
            session.get("https://api.ipify.org", timeout=10)
            return session
        except:
            continue
    return requests.Session()

# def robust_request(session, url, headers, retries=5, backoff=5):
#     for attempt in range(retries):
#         try:
#             res = session.post(url, headers=headers, timeout=360)
#             print(res, 'robust_request')
#             if res.status_code == 200:
#                 return res
#             time.sleep(backoff * (attempt + 1))
#         except:
#             time.sleep(backoff * (attempt + 1))
#     raise Exception(f"Failed after {retries} retries")

def robust_request(session, url, headers, retries=5, backoff=5):
    for attempt in range(retries):
        try:
            res = session.get(url, headers=headers, timeout=360, verify=False)
            print(f"[robust_request] Attempt {attempt+1} - Status {res.status_code}")
            if res.status_code == 200:
                return res
        except Exception as e:
            print(f"[robust_request] Attempt {attempt+1} failed: {e}")
        time.sleep(backoff * (attempt + 1))
    raise Exception(f"Failed after {retries} retries")

def is_new_case(tr):
    tds = tr.find_all("td")
    if not tds:
        return False
    serial = tds[0].text.strip()
    try:
        float(serial)
        return True
    except ValueError:
        return False

def extract_case_data(case_rows):
    tds0 = case_rows[0].find_all("td")
    serial = tds0[0].text.strip()
    case_number = tds0[1].decode_contents().strip().replace("\n", "")
    petitioner_html = tds0[2].decode_contents().strip()
    respondent_html = ""
    if len(case_rows) > 1 and len(case_rows[1].find_all("td")) >= 3:
        respondent_html = case_rows[1].find_all("td")[2].decode_contents().strip()
    party_html = f"<div>Petitioner:<br/>{petitioner_html}<b r/><br/>Respondent:<br/>{respondent_html}</div>"
    adv_pet = tds0[3].decode_contents().strip()
    adv_res = ""
    if len(case_rows) > 1 and len(case_rows[1].find_all("td")) >= 4:
        adv_res = case_rows[1].find_all("td")[3].decode_contents().strip()
    advocate_html = f"Petitioner: {adv_pet}<br/>Respondent: {adv_res}"
    remarks = tds0[4].decode_contents().strip()
    subject_lines = ""
    ia_lines = ""
    for tr in case_rows[2:]:
        tds = tr.find_all("td")
        for td in tds:
            html = td.decode_contents().strip()
            if "IA No" in html:
                ia_lines += "<br/>" + html
            elif "colspan" in td.attrs or len(tds) == 1:
                subject_lines += "<br/>" + html
    final_remarks = f"{remarks}{subject_lines}{ia_lines}".strip()
    return [serial, case_number, party_html, advocate_html, final_remarks]

def parse_cleaned_html(soup):
    final_result = []
    for h2 in soup.find_all('h2'):
        judge_names = h2.text.strip()
        court_number = [judge_names.split('[')[-1].replace(']-', '').replace(']', '').strip()]
        date_match = re.search(r'\d{2}-\d{2}-\d{4}', judge_names)
        causelist_date = date_match.group() if date_match else ''
        judge_info = judge_names.split(causelist_date, 1)[-1].strip() if causelist_date else judge_names
        if '[' in judge_info:
            judge_info = judge_info.split('[', 1)[0].strip()
        coram = [judge_info.replace('\xa0', ' ')]
        clist = []
        for tr in h2.find_all_next('tr'):
            if tr.find_previous('h2') != h2:
                break
            tds = tr.find_all("td")
            if not tds or len(tds) < 5:
                continue
            try:
                sol = {
                    'brd_slno': tds[0].text.strip(),
                    'case_type': '', 'case_no': '', 'case_year': '', 'cases': '',
                    'petitioner_name': '', 'respondent_name': '',
                    'petitioner_adv': [], 'respondent_adv': [],
                    'remark': '', 'Board_Remark': ''
                }
                case_details = tds[1]
                case_no = [k.strip() for k in bs(str(case_details).split('<br/>')[0], 'html.parser').text.split('-') if k]
                if len(case_no) < 2:
                    continue
                sol['case_type'] = case_no[0].strip()
                case_number = case_no[1].split(' ')[0].split('/')
                if len(case_number) < 2:
                    continue
                sol['case_no'] = case_number[0]
                sol['case_year'] = case_number[1]
                sol['cases'] = f"{sol['case_type']}-{sol['case_no']}-{sol['case_year']}"
                peti = tds[2].text.split('Respondent:')
                sol['respondent_name'] = peti[1].strip() if len(peti) > 1 else ''
                sol['petitioner_name'] = peti[0].split('Petitioner:')[1].strip() if 'Petitioner:' in peti[0] else ''
                advo_petse = str(tds[3]).split('Respondent:')
                pet_advo = bs(advo_petse[0], 'html.parser')
                sol['petitioner_adv'] = [line.strip() for div in pet_advo.find_all("div") for line in div.decode_contents().split('<br/>') if line.strip()]
                res_advo = bs(advo_petse[1], 'html.parser') if len(advo_petse) > 1 else bs('', 'html.parser')
                sol['respondent_adv'] = list(dict.fromkeys([line.strip() for div in res_advo.find_all(["div", "span"]) for line in div.get_text(separator='<br/>').split('<br/>') if line.strip()]))
                board = tds[4]
                sol['remark'] = bs(str(board).split('<br/>')[0], 'html.parser').text.strip()
                board_remarks = [bs(k, 'html.parser').get_text(strip=True).replace('\n', '') for k in str(board).split('<br/>') if bs(k, 'html.parser').get_text(strip=True)]
                sol['Board_Remark'] = board_remarks[-1] if board_remarks else ''
                clist.append(sol)
            except:
                continue
        if clist:
            final_result.append({"Court_Number": court_number, "Date": causelist_date, "coram": coram, "clist": clist})
    return final_result

def get_csrf_token(session):
    try:
        response = session.get("https://mphc.gov.in/causelist", timeout=120)
        soup = bs(response.text, "html.parser")
        return soup.find('input', {'id': 'csrf_token'})['value']
    except Exception as e:
        raise Exception(f"Failed to fetch CSRF token: {e}")

def fetch_mp_causelist(date, city, refresh=True):
    city_val = next((k for k, v in city_map.items() if v == city or k == city), None)
    city_code = city_map.get(city_val)
    if not city_val:
        return {"error": True, "message": "Invalid City"}
    city_full = city_full_map.get(city_code, city_code).lower()
    output_folder = os.path.join(cm.BASE_DIR_OUTPUTS, "Mp_causelist", date)
    os.makedirs(output_folder, exist_ok=True)
    final_summary = []
    failed_jobs = []

    if not refresh:
        for file in os.listdir(output_folder):
            if file.endswith(".json") and city_full in file:
                with open(os.path.join(output_folder, file), "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        if data.get("success"):
                            final_summary.extend(data.get("results", []))
                    except json.JSONDecodeError:
                        pass
        return {"success": True, "results": final_summary}

    for mfb_val, mfb_code in mfb_map.items():
        for sd_val, sd_name in sdbench_map.items():
            try:
                print(f"[START] Fetching for {city_full} | {sd_name} | {mfb_code} | {date}")
                session = get_valid_session()
                csrf_token = get_csrf_token(session)
                current_ip = get_ip(session)
                payload_url = f"https://mphc.gov.in/php/hc/causelist/get_cl.php?jcd=0&dtd={date}&place={city_code}&sbdb={sd_val}&dw=1&mfb={mfb_code}&lt=0&code=&a=&csrf_token={csrf_token}"
                headers = {
                    'User-Agent': 'Mozilla/5.0',
                    'Accept': 'text/html',
                    'Referer': 'https://mphc.gov.in/causelist',
                    'Origin': 'https://mphc.gov.in',
                    'Connection': 'keep-alive'
                }
                res = robust_request(session, payload_url, headers)
                print(res, 'requests')
                html = bs(res.text, 'html.parser')
                # print(html)
                html_cleaned = "<html><body>"
                sections = []
                current_section = {"date": "", "rows": []}
                for tag in html.find_all(["font", "table", "tr"], recursive=True):
                    if tag.name == "font" and "Causelist dated" in tag.text:
                        if current_section["date"] and current_section["rows"]:
                            sections.append(current_section)
                        current_section = {"date": tag.text.strip(), "rows": []}
                    elif tag.name == "tr":
                        current_section["rows"].append(tag)
                if current_section["date"] and current_section["rows"]:
                    sections.append(current_section)

                for section in sections:
                    html_cleaned += f"<h2>{section['date']}</h2>\n<table>"
                    cases = []
                    current_case = []
                    for tr in section["rows"]:
                        if is_new_case(tr):
                            if current_case:
                                cases.append(current_case)
                                current_case = []
                        if tr.find_all("td"):
                            current_case.append(tr)
                    if current_case:
                        cases.append(current_case)
                    for case_rows in cases:
                        try:
                            data = extract_case_data(case_rows)
                            html_cleaned += "<tr>" + "".join(f"<td>{cell}</td>" for cell in data) + "</tr>"
                        except:
                            continue
                    html_cleaned += "</table>"
                html_cleaned += "</body></html>"

                soup = bs(html_cleaned, "html.parser")
                parsed_data = parse_cleaned_html(soup)

                mfb_full = mfb_full_map.get(mfb_code, mfb_code).lower()
                bench_full = sd_name.lower().replace(" ", "_")

                for section in parsed_data:
                    section["ctype"] = str(mfb_full).capitalize()
                    section["bench"] = str(bench_full).replace('_bench', '').strip().capitalize()
                    section["court_name"] = str(city_full).capitalize()

                filename = f"{city_full}_{mfb_full}_{bench_full}_{date}.json"
                filepath = os.path.join(output_folder, filename)
                existing_data = []
                if os.path.exists(filepath):
                    with open(filepath, "r", encoding="utf-8") as f:
                        try:
                            existing_json = json.load(f)
                            existing_data = existing_json.get("results", [])
                        except json.JSONDecodeError:
                            existing_data = []

                def build_key(item):
                    return f"{item.get('cases', '').strip()}_{item.get('Court_Number', [''])[0]}"

                existing_dict = {build_key(d): d for d in existing_data}
                new_dict = {build_key(d): d for d in parsed_data}
                existing_dict.update(new_dict)
                merged_data = list(existing_dict.values())
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump({"success": True, "message": "Record Found.", "results": merged_data}, f,
                              ensure_ascii=False, indent=2)

                final_summary.extend(merged_data)
                write_log(city_full.capitalize(), sd_name, mfb_code, date, "Completed", current_ip)
                time.sleep(random.randint(15, 22))

            except Exception as e:
                print(f"[ERROR] {city_full} | {sd_name} | {mfb_code} | {date}")
                traceback.print_exc()
                failed_jobs.append((city_full, sd_name, mfb_code, date, str(e)))
                write_log(city_full.capitalize(), sd_name, mfb_code, date, f"Error - {e}", "Unavailable")

    for city_full, sd_name, mfb_code, date, reason in failed_jobs:
        try:
            session = get_valid_session()
            csrf_token = get_csrf_token(session)
            current_ip = get_ip(session)
            payload_url = f"https://mphc.gov.in/php/hc/causelist/get_cl.php?jcd=0&dtd={date}&place={city_code}&sbdb={sd_val}&dw=1&mfb={mfb_code}&lt=0&code=&a=&csrf_token={csrf_token}"
            headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html', 'Referer': 'https://mphc.gov.in/causelist', 'Origin': 'https://mphc.gov.in', 'Connection': 'keep-alive'}
            robust_request(session, payload_url, headers)
            write_log(city_full.capitalize(), sd_name, mfb_code, date, "Retry Success", current_ip)
        except Exception as e2:
            write_log(city_full.capitalize(), sd_name, mfb_code, date, f"Retry Failed - {e2}", "Unavailable")

    return {"success": True, "results": final_summary}





















# import os
# import re
# import time
# import json
# import random
# from datetime import datetime
# from io import BytesIO
# from bs4 import BeautifulSoup as bs
# from requests.auth import HTTPProxyAuth
# import requests
# from common_code import common_module as cm
# from common_code import proxy_implement as proxy
#
# # import sys
# # import os
# # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#
# mfb_map = {"1": "M", "4": "L", "5": "S"}
# sdbench_map = {"1": "Single Bench", "2": "Division Bench", "3": "Full Bench"}
# city_map = {"01": "JBP", "02": "IND", "03": "GWL"}
#
# city_full_map = {"JBP": "jabalpur", "IND": "indore", "GWL": "gwalior"}
# mfb_full_map = {"M": "motion", "L": "lok_adalat", "S": "mediation"}
#
#
# def write_log(city, bench, mfb, date, status, ip):
#     log_folder = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
#     os.makedirs(log_folder, exist_ok=True)
#     log_file = os.path.join(log_folder, "mp_causelist.txt")
#     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     log_line = f"[{timestamp}] {city}/{bench}/{mfb}/{date} | Status: {status} | IP: {ip}\n"
#     with open(log_file, "a", encoding="utf-8") as log:
#         log.write(log_line)
#
#
# def get_ip(session):
#     try:
#         res = session.get("https://api.ipify.org", timeout=10)
#         return res.text.strip()
#     except:
#         return "Unavailable"
#
#
# def get_valid_session(max_retries=5):
#     for _ in range(max_retries):
#         try:
#             session = requests.Session()
#
#             proxies = proxy.get_new_requests_proxy()
#             session.proxies.update(proxies)
#             session.get("https://api.ipify.org", timeout=10)  # test connection
#             return session
#         except:
#             continue
#     return requests.Session()
#
#
# def robust_request(session, url, headers, retries=5, backoff=5):
#     for attempt in range(retries):
#         try:
#             res = session.post(url, headers=headers, timeout=365)
#             if res.status_code == 200:
#                 return res
#             time.sleep(backoff * (attempt + 1))
#         except:
#             time.sleep(backoff * (attempt + 1))
#     raise Exception(f"Failed after {retries} retries")
#
#
# def is_new_case(tr):
#     tds = tr.find_all("td")
#     if not tds:
#         return False
#     serial = tds[0].text.strip()
#     try:
#         float(serial)
#         return True
#     except ValueError:
#         return False
#
#
# def extract_case_data(case_rows):
#     tds0 = case_rows[0].find_all("td")
#     serial = tds0[0].text.strip()
#     case_number = tds0[1].decode_contents().strip().replace("\n", "")
#     petitioner_html = tds0[2].decode_contents().strip()
#     respondent_html = ""
#     if len(case_rows) > 1 and len(case_rows[1].find_all("td")) >= 3:
#         respondent_html = case_rows[1].find_all("td")[2].decode_contents().strip()
#     party_html = f"<div>Petitioner:<br/>{petitioner_html}<br/><br/>Respondent:<br/>{respondent_html}</div>"
#     adv_pet = tds0[3].decode_contents().strip()
#     adv_res = ""
#     if len(case_rows) > 1 and len(case_rows[1].find_all("td")) >= 4:
#         adv_res = case_rows[1].find_all("td")[3].decode_contents().strip()
#     advocate_html = f"Petitioner: {adv_pet}<br/>Respondent: {adv_res}"
#     remarks = tds0[4].decode_contents().strip()
#     subject_lines = ""
#     ia_lines = ""
#     for tr in case_rows[2:]:
#         tds = tr.find_all("td")
#         for td in tds:
#             html = td.decode_contents().strip()
#             if "IA No" in html:
#                 ia_lines += "<br/>" + html
#             elif "colspan" in td.attrs or len(tds) == 1:
#                 subject_lines += "<br/>" + html
#     final_remarks = f"{remarks}{subject_lines}{ia_lines}".strip()
#     return [serial, case_number, party_html, advocate_html, final_remarks]
#
#
# def parse_cleaned_html(soup):
#     final_result = []
#     for h2 in soup.find_all('h2'):
#         judge_names = h2.text.strip()
#         court_number = [judge_names.split('[')[-1].replace(']-', '').replace(']', '').strip()]
#         date_match = re.search(r'\d{2}-\d{2}-\d{4}', judge_names)
#         causelist_date = date_match.group() if date_match else ''
#         judge_info = judge_names.split(causelist_date, 1)[-1].strip() if causelist_date else judge_names
#         if '[' in judge_info:
#             judge_info = judge_info.split('[', 1)[0].strip()
#         coram = [judge_info.replace('\xa0', ' ')]
#         clist = []
#         for tr in h2.find_all_next('tr'):
#             if tr.find_previous('h2') != h2:
#                 break
#             tds = tr.find_all("td")
#             if not tds or len(tds) < 5:
#                 continue
#             try:
#                 sol = {
#                     'brd_slno': tds[0].text.strip(),
#                     'case_type': '', 'case_no': '', 'case_year': '', 'cases': '',
#                     'petitioner_name': '', 'respondent_name': '',
#                     'petitioner_adv': [], 'respondent_adv': [],
#                     'remark': '', 'Board_Remark': ''
#                 }
#                 case_details = tds[1]
#                 case_no = [k.strip() for k in bs(str(case_details).split('<br/>')[0], 'html.parser').text.split('-') if
#                            k]
#                 if len(case_no) < 2:
#                     continue
#                 sol['case_type'] = case_no[0].strip()
#                 case_number = case_no[1].split(' ')[0].split('/')
#                 if len(case_number) < 2:
#                     continue
#                 sol['case_no'] = case_number[0]
#                 sol['case_year'] = case_number[1]
#                 sol['cases'] = f"{sol['case_type']}-{sol['case_no']}-{sol['case_year']}"
#                 peti = tds[2].text.split('Respondent:')
#                 sol['respondent_name'] = peti[1].strip() if len(peti) > 1 else ''
#                 sol['petitioner_name'] = peti[0].split('Petitioner:')[1].strip() if 'Petitioner:' in peti[0] else ''
#                 advo_petse = str(tds[3]).split('Respondent:')
#                 pet_advo = bs(advo_petse[0], 'html.parser')
#                 sol['petitioner_adv'] = [line.strip() for div in pet_advo.find_all("div") for line in
#                                          div.decode_contents().split('<br/>') if line.strip()]
#                 res_advo = bs(advo_petse[1], 'html.parser') if len(advo_petse) > 1 else bs('', 'html.parser')
#                 sol['respondent_adv'] = list(dict.fromkeys(
#                     [line.strip() for div in res_advo.find_all(["div", "span"]) for line in
#                      div.get_text(separator='<br/>').split('<br/>') if line.strip()]))
#                 board = tds[4]
#                 sol['remark'] = bs(str(board).split('<br/>')[0], 'html.parser').text.strip()
#                 board_remarks = [bs(k, 'html.parser').get_text(strip=True).replace('\n', '') for k in
#                                  str(board).split('<br/>') if bs(k, 'html.parser').get_text(strip=True)]
#                 sol['Board_Remark'] = board_remarks[-1] if board_remarks else ''
#                 clist.append(sol)
#             except:
#                 continue
#         if clist:
#             final_result.append({"Court_Number": court_number, "Date": causelist_date, "coram": coram, "clist": clist})
#     return final_result
#
#
# def get_csrf_token(session):
#     try:
#         response = session.get("https://mphc.gov.in/causelist", timeout=120)
#         soup = bs(response.text, "html.parser")
#         return soup.find('input', {'id': 'csrf_token'})['value']
#     except Exception as e:
#         raise Exception(f"Failed to fetch CSRF token: {e}")
#
#
# def fetch_mp_causelist(date, city, refresh=True):
#     city_val = next((k for k, v in city_map.items() if v == city or k == city), None)
#     city_code = city_map.get(city_val)
#     if not city_val:
#         return {"error": True, "message": "Invalid City"}
#     city_full = city_full_map.get(city_code, city_code).lower()
#     output_folder = os.path.join(cm.BASE_DIR_OUTPUTS, "Mp_causelist", date)
#     os.makedirs(output_folder, exist_ok=True)
#     final_summary = []
#     failed_jobs = []
#
#     if not refresh:
#         for file in os.listdir(output_folder):
#             if file.endswith(".json") and city_full in file:
#                 with open(os.path.join(output_folder, file), "r", encoding="utf-8") as f:
#                     try:
#                         data = json.load(f)
#                         if data.get("success"):
#                             final_summary.extend(data.get("results", []))
#                     except json.JSONDecodeError:
#                         pass
#         return {"success": True, "results": final_summary}
#
#     for mfb_val, mfb_code in mfb_map.items():
#         for sd_val, sd_name in sdbench_map.items():
#             try:
#                 session = get_valid_session()
#                 csrf_token = get_csrf_token(session)
#                 current_ip = get_ip(session)
#                 payload_url = f"https://mphc.gov.in/php/hc/causelist/get_cl.php?jcd=0&dtd={date}&place={city_code}&sbdb={sd_val}&dw=1&mfb={mfb_code}&lt=0&code=&a=&csrf_token={csrf_token}"
#                 headers = {
#                     'User-Agent': 'Mozilla/5.0',
#                     'Accept': 'text/html',
#                     'Referer': 'https://mphc.gov.in/causelist',
#                     'Origin': 'https://mphc.gov.in',
#                     'Connection': 'keep-alive'
#                 }
#                 res = robust_request(session, payload_url, headers)
#                 html = bs(res.text, 'html.parser')
#
#                 html_cleaned = "<html><body>"
#                 sections = []
#                 current_section = {"date": "", "rows": []}
#                 for tag in html.find_all(["font", "table", "tr"], recursive=True):
#                     if tag.name == "font" and "Causelist dated" in tag.text:
#                         if current_section["date"] and current_section["rows"]:
#                             sections.append(current_section)
#                         current_section = {"date": tag.text.strip(), "rows": []}
#                     elif tag.name == "tr":
#                         current_section["rows"].append(tag)
#                 if current_section["date"] and current_section["rows"]:
#                     sections.append(current_section)
#
#                 for section in sections:
#                     html_cleaned += f"<h2>{section['date']}</h2>\n<table>"
#                     cases = []
#                     current_case = []
#                     for tr in section["rows"]:
#                         if is_new_case(tr):
#                             if current_case:
#                                 cases.append(current_case)
#                                 current_case = []
#                         if tr.find_all("td"):
#                             current_case.append(tr)
#                     if current_case:
#                         cases.append(current_case)
#                     for case_rows in cases:
#                         try:
#                             data = extract_case_data(case_rows)
#                             html_cleaned += "<tr>" + "".join(f"<td>{cell}</td>" for cell in data) + "</tr>"
#                         except:
#                             continue
#                     html_cleaned += "</table>"
#                 html_cleaned += "</body></html>"
#
#                 soup = bs(html_cleaned, "html.parser")
#                 parsed_data = parse_cleaned_html(soup)
#
#                 mfb_full = mfb_full_map.get(mfb_code, mfb_code).lower()
#                 bench_full = sd_name.lower().replace(" ", "_")
#
#                 for section in parsed_data:
#                     section["ctype"] = str(mfb_full).capitalize()
#                     section["bench"] = str(bench_full).replace('_bench', '').strip().capitalize()
#                     section["court_name"] = str(city_full).capitalize()
#
#                 filename = f"{city_full}_{mfb_full}_{bench_full}_{date}.json"
#                 filepath = os.path.join(output_folder, filename)
#                 existing_data = []
#                 if os.path.exists(filepath):
#                     with open(filepath, "r", encoding="utf-8") as f:
#                         try:
#                             existing_json = json.load(f)
#                             existing_data = existing_json.get("results", [])
#                         except json.JSONDecodeError:
#                             existing_data = []
#
#                 def build_key(item):
#                     return f"{item.get('cases', '').strip()}_{item.get('Court_Number', [''])[0]}"
#
#                 existing_dict = {build_key(d): d for d in existing_data}
#                 new_dict = {build_key(d): d for d in parsed_data}
#                 existing_dict.update(new_dict)
#                 merged_data = list(existing_dict.values())
#                 with open(filepath, "w", encoding="utf-8") as f:
#                     json.dump({"success": True, "message": "Record Found.", "results": merged_data}, f,
#                               ensure_ascii=False, indent=2)
#
#                 final_summary.extend(merged_data)
#                 write_log(city_full.capitalize(), bench_full.replace("_bench", "").capitalize(), mfb_full.capitalize(),
#                           date, "Completed", current_ip)
#                 time.sleep(random.randint(15, 22))
#
#             except Exception as e:
#                 failed_jobs.append((city_full, sd_name, mfb_code, date, str(e)))
#                 write_log(city_full.capitalize(), sd_name, mfb_code, date, f"Error - {e}", "Unavailable")
#
#     for city_full, sd_name, mfb_code, date, reason in failed_jobs:
#         try:
#             session = get_valid_session()
#             csrf_token = get_csrf_token(session)
#             current_ip = get_ip(session)
#             payload_url = f"https://mphc.gov.in/php/hc/causelist/get_cl.php?jcd=0&dtd={date}&place={city_code}&sbdb={sd_val}&dw=1&mfb={mfb_code}&lt=0&code=&a=&csrf_token={csrf_token}"
#             headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html', 'Referer': 'https://mphc.gov.in/causelist',
#                        'Origin': 'https://mphc.gov.in', 'Connection': 'keep-alive'}
#             robust_request(session, payload_url, headers)
#             write_log(city_full.capitalize(), sd_name, mfb_code, date, "Retry Success", current_ip)
#         except Exception as e2:
#             write_log(city_full.capitalize(), sd_name, mfb_code, date, f"Retry Failed - {e2}", "Unavailable")
#
#     return {"success": True, "results": final_summary}