import sys
sys.path.insert(0, '/var/www/mml_python_code')
import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime
import time
import threading
from http.client import RemoteDisconnected
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from common_code.mysql_common import get_cursor
from common_code import proxy_implement

USE_PROXY = True
if USE_PROXY:
    print('proxy is true')
    request_method = proxy_implement.get_new_requests_proxy()
else:
    print('proxy is false')
    request_method = None

batch_size = 20
max_attempts = 3
date_today = None

def create_queue_table_if_not_exists():
    with get_cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queue_table (
                id INT AUTO_INCREMENT PRIMARY KEY,
                state_code VARCHAR(10) NOT NULL,
                district_code VARCHAR(10) NOT NULL,
                est_code VARCHAR(20) NOT NULL,
                court_complex_id VARCHAR(20) NOT NULL,
                judge_id VARCHAR(20) NOT NULL,
                causelist_date DATE NOT NULL,
                status INT DEFAULT 0,
                attempts INT DEFAULT 0,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_entry (state_code, district_code, est_code, court_complex_id, judge_id, causelist_date)
            )
        """)

def create_causelist_table_if_not_exists():
    with get_cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS district_court_causelist (
                id INT AUTO_INCREMENT PRIMARY KEY,
                state_code INT,
                state_name VARCHAR(50),
                district_code INT,
                district_name VARCHAR(50),
                complex_code VARCHAR(50),
                complex_name VARCHAR(255),
                est_code VARCHAR(50),
                judge_id VARCHAR(50),
                judge_name VARCHAR(255),
                judge_designation VARCHAR(255),
                causelist_date DATE,
                case_category VARCHAR(50),
                matter_type VARCHAR(255),
                sno VARCHAR(20),
                full_caseno VARCHAR(255),
                cnr_no VARCHAR(255),
                case_type VARCHAR(255),
                case_no VARCHAR(50),
                case_year VARCHAR(10),
                next_hearing_date DATE,
                petitioner TEXT,
                respondent TEXT,
                petitioner_advocate TEXT,
                respondent_advocate TEXT,
                note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_case (state_code, district_code, complex_code, est_code, judge_id, full_caseno, causelist_date, case_category)
            )
        """)

def insert_into_queue_if_not_exists(state_code, district_code, est_code, complex_code, judge_id, causelist_date):
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT id FROM queue_table
            WHERE state_code=%s AND district_code=%s AND est_code=%s
              AND court_complex_id=%s AND judge_id=%s AND causelist_date=%s
        """, (state_code, district_code, est_code, complex_code, judge_id, causelist_date))
        row = cursor.fetchone()
        if not row:
            cursor.execute("""
                INSERT INTO queue_table (
                    state_code, district_code, est_code, court_complex_id,
                    judge_id, causelist_date, status, attempts
                ) VALUES (%s, %s, %s, %s, %s, %s, 0, 0)
            """, (state_code, district_code, est_code, complex_code, judge_id, causelist_date))
            print(f"Queue entry created for judge_id={judge_id} | date={causelist_date}")

def mark_queue_processing(state_code, district_code, est_code, complex_id, judge_id, causelist_date):
    with get_cursor() as cursor:
        cursor.execute("""UPDATE queue_table SET status=1, updated_at=CURRENT_TIMESTAMP 
                          WHERE state_code=%s AND district_code=%s AND est_code=%s 
                          AND court_complex_id=%s AND judge_id=%s AND causelist_date=%s""",
                       (state_code, district_code, est_code, complex_id, judge_id, causelist_date))

def mark_queue_completed(state_code, district_code, est_code, complex_id, judge_id, causelist_date):
    with get_cursor() as cursor:
        cursor.execute("""UPDATE queue_table SET status=2, updated_at=CURRENT_TIMESTAMP 
                          WHERE state_code=%s AND district_code=%s AND est_code=%s 
                          AND court_complex_id=%s AND judge_id=%s AND causelist_date=%s""",
                       (state_code, district_code, est_code, complex_id, judge_id, causelist_date))

def mark_queue_error(state_code, district_code, est_code, complex_id, judge_id, causelist_date, msg):
    with get_cursor() as cursor:
        cursor.execute("""UPDATE queue_table 
                          SET attempts = attempts + 1, error=%s, updated_at=CURRENT_TIMESTAMP 
                          WHERE state_code=%s AND district_code=%s AND est_code=%s 
                          AND court_complex_id=%s AND judge_id=%s AND causelist_date=%s""",
                       (msg, state_code, district_code, est_code, complex_id, judge_id, causelist_date))

        cursor.execute("""SELECT attempts FROM queue_table 
                          WHERE state_code=%s AND district_code=%s AND est_code=%s 
                          AND court_complex_id=%s AND judge_id=%s AND causelist_date=%s""",
                       (state_code, district_code, est_code, complex_id, judge_id, causelist_date))
        row = cursor.fetchone()
        if row and row['attempts'] >= max_attempts:
            cursor.execute("""UPDATE queue_table SET status=3 WHERE state_code=%s AND district_code=%s 
                              AND est_code=%s AND court_complex_id=%s AND judge_id=%s AND causelist_date=%s""",
                           (state_code, district_code, est_code, complex_id, judge_id, causelist_date))
        else:
            cursor.execute("""UPDATE queue_table SET status=0 WHERE state_code=%s AND district_code=%s 
                              AND est_code=%s AND court_complex_id=%s AND judge_id=%s AND causelist_date=%s""",
                           (state_code, district_code, est_code, complex_id, judge_id, causelist_date))

def should_process(state_code, district_code, est_code, complex_id, judge_id, causelist_date):
    with get_cursor() as cursor:
        cursor.execute("""SELECT status, attempts FROM queue_table 
                          WHERE state_code=%s AND district_code=%s AND est_code=%s 
                          AND court_complex_id=%s AND judge_id=%s AND causelist_date=%s""",
                       (state_code, district_code, est_code, complex_id, judge_id, causelist_date))
        row = cursor.fetchone()
        if not row:
            return True
        return not (row['status'] in (1, 2) or row['attempts'] >= max_attempts)

def convert_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").strftime("%Y-%m-%d")
    except:
        return None

def save_to_db(data):
    with get_cursor() as cursor:
        cursor.execute("""SELECT id FROM district_court_causelist 
                          WHERE full_caseno=%s AND causelist_date=%s AND judge_id=%s""",
                       (data.get("full_caseno"), data["causelist_date"], data["judge_id"]))
        if cursor.fetchone():
            return
        cursor.execute("""
            INSERT INTO district_court_causelist (
                state_code, state_name, district_code, district_name, complex_code, complex_name, est_code,
                judge_id, judge_name, judge_designation, causelist_date, case_category, matter_type, sno,
                full_caseno, cnr_no, case_type, case_no, case_year, next_hearing_date,
                petitioner, respondent, petitioner_advocate, respondent_advocate, note
            ) VALUES (
                %(state_code)s, %(state_name)s, %(district_code)s, %(district_name)s,
                %(complex_code)s, %(complex_name)s, %(est_code)s, %(judge_id)s, %(judge_name)s, %(judge_designation)s,
                %(causelist_date)s, %(case_category)s, %(matter_type)s, %(sno)s,
                %(full_caseno)s, %(cnr_no)s, %(case_type)s, %(case_no)s, %(case_year)s,
                %(next_hearing_date)s, %(petitioner)s, %(respondent)s,
                %(petitioner_advocate)s, %(respondent_advocate)s, %(note)s
            )
        """, data)

def get_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def fetch_data(row):
    state_code = row['state_code']
    state_name = row['state_name']
    dist_code = row['district_code']
    dist_name = row['district_name']
    complex_code = row['complex_code']
    complex_name = row['complex_name']
    est_code = row['est_id']
    judge_id = row['judge_id']
    judge_name = row['judge_name']
    judge_designation = row['judge_designation']
    judge_fullname = row['judge_fullname']

    print(f"Fetching for Judge: {dist_name} | {state_name} | {complex_code} | {est_code} | {judge_fullname} | {date_today}")

    try:
        session = get_session()
        for cicri_val in ["civ", "cri"]:
            case_category = "Civil" if cicri_val == "civ" else "Criminal"
            payload = {
                "CL_court_no": f"{est_code}^{judge_id}",
                "causelist_date": date_today,
                "cause_list_captcha_code": "",
                "court_name_txt": judge_fullname,
                "state_code": state_code,
                "dist_code": dist_code,
                "court_complex_code": complex_code,
                "est_code": est_code,
                "cicri": cicri_val,
                "selprevdays": 0,
                "ajax_req": "true",
                "app_token": ""
            }

            url = 'https://services.ecourts.gov.in/ecourtindia_v6/?p=cause_list/submitCauseList'
            print(f"POST => {url} | judge_id={judge_id} | category={case_category}")

            try:
                response = session.post(url, data=payload, proxies=request_method, timeout=15)
                response.raise_for_status()
            except RemoteDisconnected:
                raise Exception("RemoteDisconnected: Server closed connection unexpectedly")
            except requests.exceptions.RequestException as e:
                raise Exception(f"Network Error: {e}")

            html = bs(response.json().get('case_data', ''), 'html.parser')
            tbody = html.find("tbody")
            if not tbody:
                continue

            rows_tr = tbody.find_all("tr")
            matter_type = None

            for tr in rows_tr:
                tds = tr.find_all("td")
                if len(tds) == 1 or "colspan" in tds[0].attrs:
                    matter_type = tds[0].get_text(strip=True)
                    continue

                sol = {
                    "state_code": state_code, "state_name": state_name,
                    "district_code": dist_code, "district_name": dist_name,
                    "complex_code": complex_code, "complex_name": complex_name,
                    "est_code": est_code, "judge_id": judge_id, "judge_name": judge_name,
                    "judge_designation": judge_designation, "causelist_date": convert_date(date_today),
                    "case_category": case_category, "matter_type": matter_type
                }

                sol["sno"] = tds[0].get_text(strip=True)
                case_td = tds[1]
                # link = case_td.find("a")
                # if link and "onclick" in link.attrs:
                #     try:
                #         parts = link["onclick"].split("('")[1].split(",")
                #         sol["full_caseno"] = parts[0].replace("'", "")
                #         sol["cnr_no"] = parts[1].replace("'", "")
                #     except:
                #         sol["full_caseno"] = sol["cnr_no"] = ""

                sol["full_caseno"] = ""
                sol["cnr_no"] = ""
                link = case_td.find("a")
                if link and "onclick" in link.attrs:
                    try:
                        parts = link["onclick"].split("('")[1].split(",")
                        sol["full_caseno"] = parts[0].replace("'", "")
                        sol["cnr_no"] = parts[1].replace("'", "")
                    except:
                        pass

                next_datas = case_td.get_text(" ", strip=True).replace("View", "").split("Next")
                case_details = next_datas[0].split("/")
                if len(case_details) >= 3:
                    sol["case_type"] = case_details[0].strip()
                    sol["case_no"] = case_details[1].strip()
                    sol["case_year"] = case_details[2].strip()
                else:
                    sol["case_type"] = sol["case_no"] = sol["case_year"] = None

                if len(next_datas) > 1 and ":-" in next_datas[1]:
                    hearing_date = next_datas[1].split(":-")[1].strip()
                    sol["next_hearing_date"] = convert_date(hearing_date)
                else:
                    sol["next_hearing_date"] = None

                party_td = case_td.find_next("td")
                if party_td:
                    parties = party_td.get_text(" ", strip=True).split("versus")
                    sol["petitioner"] = parties[0].strip()
                    sol["respondent"] = parties[1].strip() if len(parties) > 1 else ""
                    adv_td = party_td.find_next("td")
                    if adv_td:
                        advs = adv_td.get_text(" ", strip=True).split("versus")
                        sol["petitioner_advocate"] = advs[0].strip() if len(advs) >= 1 else ""
                        sol["respondent_advocate"] = advs[1].strip() if len(advs) >= 2 else ""
                sol["note"] = ""
                save_to_db(sol)

            time.sleep(3)

        mark_queue_completed(state_code, dist_code, est_code, complex_code, judge_id, convert_date(date_today))

    except Exception as e:
        print(f"Error for judge {judge_id}: {e}")
        mark_queue_error(state_code, dist_code, est_code, complex_code, judge_id, convert_date(date_today), str(e))

def fetch_for_judge(row):
    fetch_data(row)

def process_batch(judge_batch):
    threads = []
    for row in judge_batch:
        state_code = row['state_code']
        dist_code = row['district_code']
        complex_code = row['complex_code']
        est_code = row['est_id']
        judge_id = row['judge_id']

        print('Processing:', state_code, dist_code, est_code, complex_code, judge_id)

        causelist_date = convert_date(date_today)
        insert_into_queue_if_not_exists(state_code, dist_code, est_code, complex_code, judge_id, causelist_date)

        if should_process(state_code, dist_code, est_code, complex_code, judge_id, causelist_date):
            mark_queue_processing(state_code, dist_code, est_code, complex_code, judge_id, causelist_date)
            t = threading.Thread(target=fetch_for_judge, args=(row,))
            t.start()
            threads.append(t)
            time.sleep(2)
    for t in threads:
        t.join()

def fetch_court_data(state_code=None, dist_code=None, complex_code=None, est_code=None, judge_id=None):
    with get_cursor() as cursor:
        # query = "SELECT * FROM court_data WHERE 1=1"
        query = "SELECT * FROM court_data WHERE status=1"
        params = []
        if state_code: query += " AND state_code=%s"; params.append(state_code)
        if dist_code: query += " AND district_code=%s"; params.append(dist_code)
        if complex_code: query += " AND complex_code=%s"; params.append(complex_code)
        if est_code: query += " AND est_id=%s"; params.append(est_code)
        if judge_id: query += " AND judge_id=%s"; params.append(judge_id)
        cursor.execute(query, tuple(params))
        return cursor.fetchall()

def clear_queue_entries(state_code, dist_code=None, complex_code=None):
    with get_cursor() as cursor:
        query = "DELETE FROM queue_table WHERE state_code=%s AND causelist_date=%s"
        params = [state_code, convert_date(date_today)]
        if dist_code:
            query += " AND district_code=%s"; params.append(dist_code)
        if complex_code:
            query += " AND court_complex_id=%s"; params.append(complex_code)
        cursor.execute(query, tuple(params))
    print(f"Cleared old queue entries for state={state_code}, district={dist_code}, complex={complex_code}, date={date_today}")

def main(state_code=None, dist_code=None, complex_code=None, est_code=None, judge_id=None):
    create_causelist_table_if_not_exists()
    create_queue_table_if_not_exists()
    results = fetch_court_data(state_code, dist_code, complex_code, est_code, judge_id)
    clear_queue_entries(state_code, dist_code, complex_code)

    for row in results:
        insert_into_queue_if_not_exists(
            row['state_code'], row['district_code'], row['est_id'],
            row['complex_code'], row['judge_id'], convert_date(date_today)
        )

    for i in range(0, len(results), batch_size):
        batch = results[i:i + batch_size]
        process_batch(batch)

    print("All data inserted and queue status updated.")

if __name__ == "__main__":
    state_code = dist_code = complex_code = est_code = judge_id = None
    date_today = datetime.today().strftime("%d-%m-%Y")
    args = sys.argv[1:]
    if args and '-' in args[0]:
        date_today = args.pop(0)
    for arg in args:
        if '=' in arg:
            key, val = arg.split('=', 1)
            if key == 'st_id': state_code = int(val)
            elif key == 'dis_id': dist_code = int(val)
            elif key == 'com_id': complex_code = val
            elif key == 'est': est_code = val
            elif key == 'j_id': judge_id = int(val)
    print(f"st_id={state_code} dis_id={dist_code} com_id={complex_code} est={est_code} j_id={judge_id} date={date_today}")
    main(state_code, dist_code, complex_code, est_code, judge_id)


# python3 causelist_ecourt.py 20-11-2025 st_id=3 dis_id=20 com_id=1030134 est=10 j_id=81
