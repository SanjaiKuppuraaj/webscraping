import sys
sys.path.insert(0, '/var/www/mml_python_code')

from bs4 import BeautifulSoup as bs
import requests
import time
from common_code.mysql_common import get_cursor

with get_cursor(dictionary=False) as cursor:
    cursor.execute("""
     CREATE TABLE IF NOT EXISTS court_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        state_code INT,
        state_name VARCHAR(255),
        district_code VARCHAR(50),
        district_name VARCHAR(255),
        complex_code VARCHAR(50),
        complex_name VARCHAR(255),
        est_id VARCHAR(50),
        judge_id VARCHAR(50),
        judge_name VARCHAR(255),
        judge_designation VARCHAR(255),
        judge_fullname VARCHAR(1024),
        status TINYINT(1) NOT NULL DEFAULT 0,
        UNIQUE KEY unique_judge (state_code, district_code, complex_code, est_id, judge_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

def truncate_utf8(s, max_bytes):
    encoded = s.encode('utf-8')
    if len(encoded) <= max_bytes:
        return s
    truncated = encoded[:max_bytes]
    while True:
        try:
            return truncated.decode('utf-8')
        except UnicodeDecodeError:
            truncated = truncated[:-1]

def truncate_str(s, max_chars):
    return s[:max_chars] if s else s

urls = 'https://services.ecourts.gov.in/ecourtindia_v6/?p=cause_list/index&app_token='
headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": 'https://services.ecourts.gov.in/',
    "X-Requested-With": "XMLHttpRequest",
}

response = requests.get(urls, headers=headers, timeout=20)
response_bs = bs(response.text, 'html.parser')
state_select = response_bs.find('select', {'id': 'sess_state_code'})
state_names = [k.text.strip() for k in state_select.find_all('option')[1:]]
state_values = [k['value'] for k in state_select.find_all('option')[1:]]
state_datas = list(zip(state_names, state_values))

total_judges = 0
total_updated = 0

for state_name, state_code in state_datas:
    state_code = int(state_code)
    print(f"\nProcessing state: {state_name} ({state_code})")

    dist_url = 'https://services.ecourts.gov.in/ecourtindia_v6/?p=casestatus/fillDistrict'
    payload = {'state_code': state_code, 'ajax_req': 'true', 'app_token': ''}
    try:
        main_res = requests.post(dist_url, data=payload, headers=headers, timeout=30)
        main_res.raise_for_status()
        main_res = bs(main_res.json().get('dist_list', ''), 'html.parser')
    except Exception as e:
        print(f"Failed to get districts for {state_name}: {e}")
        continue

    district_tags = main_res.find_all('option')[1:]
    for di_tag in district_tags:
        di_val = di_tag['value']
        di_name = di_tag.text.strip()
        print(f"  District: {di_name} ({di_val})")

        complex_url = 'https://services.ecourts.gov.in/ecourtindia_v6/?p=casestatus/fillcomplex'
        com_payload = {'state_code': state_code, 'dist_code': di_val, 'ajax_req': 'true', 'app_token': ''}
        try:
            com_res = requests.post(complex_url, data=com_payload, headers=headers)
            com_res.raise_for_status()
            com_res = bs(com_res.json().get('complex_list', ''), 'html.parser')
        except Exception as e:
            print(f"Failed to get complexes for {di_name}: {e}")
            continue

        complex_tags = com_res.find_all('option')[1:]

        for comp in complex_tags:
            comp_parts = comp['value'].split('@')
            comp_value = comp_parts[0]
            comp_est = comp_parts[1] if len(comp_parts) > 1 else None
            comp_name = comp.text.strip()
            print(f"    Complex: {comp_name} ({comp_value})")

            cause_list_url = 'https://services.ecourts.gov.in/ecourtindia_v6/?p=cause_list/fillCauseList'
            cause_payload = {
                'state_code': state_code,
                'dist_code': di_val,
                'court_complex_code': comp_value,
                'est_code': comp_est,
                'search_act': 'undefined',
                'ajax_req': 'true',
                'app_token': ''
            }

            try:
                res_cause_list = requests.post(cause_list_url, data=cause_payload, headers=headers)
                res_cause_list.raise_for_status()
                cause_list_html = res_cause_list.json().get('cause_list', '')
                cause_bs = bs(cause_list_html, 'html.parser')
                cause_options = [opt for opt in cause_bs.find_all('option')[1:] if opt and not opt.has_attr('disabled')]
            except Exception as e:
                print(f"Failed to get cause list for {comp_name}: {e}")
                continue

            for c in cause_options:
                val_parts = c['value'].split('^') if c else [None, None]
                est_id = val_parts[0] if len(val_parts) > 0 else None
                judge_id = val_parts[1] if len(val_parts) > 1 else None
                text_parts = c.text.split('-') if c else []
                judge_name = text_parts[1].strip() if len(text_parts) > 1 else 'Unknown'
                judge_designation = '-'.join(text_parts[2:]).strip() if len(text_parts) > 2 else 'Unknown'
                judge_fullname = c.text.strip()

                judge_name = truncate_str(judge_name, 255)
                judge_designation = truncate_str(judge_designation, 255)
                judge_fullname = truncate_utf8(judge_fullname, 1024)

                with get_cursor(dictionary=False) as cursor:
                    cursor.execute("""
                        SELECT id FROM court_data
                        WHERE state_code=%s AND district_code=%s AND complex_code=%s AND est_id=%s AND judge_id=%s
                    """, (state_code, di_val, comp_value, est_id, judge_id))
                    result = cursor.fetchone()

                    if result:
                        cursor.execute("""
                            UPDATE court_data
                            SET judge_name=%s,
                                judge_designation=%s,
                                judge_fullname=%s
                            WHERE id=%s
                        """, (judge_name, judge_designation, judge_fullname, result[0]))
                        total_updated += 1
                    else:
                        cursor.execute("""
                            INSERT INTO court_data
                            (state_code, state_name, district_code, district_name, complex_code, complex_name, est_id, judge_id, judge_name, judge_designation, judge_fullname, status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
                        """, (state_code, state_name, di_val, di_name, comp_value, comp_name, est_id, judge_id, judge_name, judge_designation, judge_fullname))
                        total_judges += 1

            time.sleep(0.3)

print(f"\nAll done. Total new judges added: {total_judges}, Total existing updated: {total_updated}")


# python3 services_ecourt.py