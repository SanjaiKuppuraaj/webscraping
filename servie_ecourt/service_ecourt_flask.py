import sys
sys.path.insert(0, '/var/www/mml_python_code')

from flask import Blueprint, request, jsonify
import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime, timedelta
import time
import threading
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from common_code.mysql_common import get_cursor
from common_code import proxy_implement

ecourt_bp = Blueprint('ecourt_flask', __name__)

date_today = None
request_method = proxy_implement.get_requests_proxy()
batch_size = 20

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
                UNIQUE KEY unique_case (
                    state_code, district_code, complex_code, est_code,
                    judge_id, full_caseno, causelist_date, case_category
                )
            )
        """)

# --- Utility Functions ---
def convert_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").strftime("%Y-%m-%d")
    except:
        return None

def save_to_db(data):
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT id
            FROM district_court_causelist
            WHERE full_caseno=%s AND causelist_date=%s AND judge_id=%s
        """, (data.get("full_caseno"), data["causelist_date"], data["judge_id"]))

        if cursor.fetchone():
            return

        cursor.execute("""
            INSERT INTO district_court_causelist (
                state_code, state_name, district_code, district_name,
                complex_code, complex_name, est_code,
                judge_id, judge_name, judge_designation,
                causelist_date, case_category, matter_type, sno,
                full_caseno, cnr_no, case_type, case_no, case_year,
                next_hearing_date, petitioner, respondent,
                petitioner_advocate, respondent_advocate, note
            ) VALUES (
                %(state_code)s, %(state_name)s, %(district_code)s, %(district_name)s,
                %(complex_code)s, %(complex_name)s, %(est_code)s,
                %(judge_id)s, %(judge_name)s, %(judge_designation)s,
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

# --- Data Fetching Function ---
def fetch_data(row):
    global date_today
    state_code, state_name = row['state_code'], row['state_name']
    dist_code, dist_name = row['district_code'], row['district_name']
    complex_code, complex_name = row['complex_code'], row['complex_name']
    est_code, judge_id = row['est_id'], row['judge_id']
    judge_name, judge_designation = row['judge_name'], row['judge_designation']

    try:
        session = get_session()
        for cicri_val in ["civ", "cri"]:
            case_category = "Civil" if cicri_val == "civ" else "Criminal"
            payload = {
                "CL_court_no": f"{est_code}^{judge_id}",
                "causelist_date": date_today,
                "state_code": state_code,
                "dist_code": dist_code,
                "court_complex_code": complex_code,
                "est_code": est_code,
                "cicri": cicri_val,
                "ajax_req": "true",
            }
            url = 'https://services.ecourts.gov.in/ecourtindia_v6/?p=cause_list/submitCauseList'
            response = session.post(url, data=payload, proxies=request_method, timeout=20)
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
                    "case_category": case_category, "matter_type": matter_type,
                    "court_hall_no": "", "court_hall_address": "", "note": ""
                }

                sol["sno"] = tds[0].get_text(strip=True)

                case_td = tds[1]
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

                save_to_db(sol)
            time.sleep(2)
    except Exception as e:
        print(f"Error fetching data for judge {judge_id}: {str(e)}")

def main(state_code=None, dist_code=None, complex_code=None, est_code=None, judge_id=None):
    global date_today
    create_causelist_table_if_not_exists()
    create_queue_table_if_not_exists()
    with get_cursor() as cursor:
        query = "SELECT * FROM court_data WHERE 1=1"
        params = []
        if state_code: query += " AND state_code=%s"; params.append(state_code)
        if dist_code: query += " AND district_code=%s"; params.append(dist_code)
        if complex_code: query += " AND complex_code=%s"; params.append(complex_code)
        if est_code: query += " AND est_id=%s"; params.append(est_code)
        if judge_id: query += " AND judge_id=%s"; params.append(judge_id)
        cursor.execute(query, tuple(params))
        results = cursor.fetchall()

    for i in range(0, len(results), batch_size):
        batch = results[i:i + batch_size]
        threads = []
        for row in batch:
            t = threading.Thread(target=fetch_data, args=(row,))
            t.start()
            threads.append(t)
            time.sleep(1)
        for t in threads:
            t.join()
    return True

@ecourt_bp.route("/service_ecourt", methods=["GET"])
def service_ecourt():
    global date_today
    date_today = request.args.get("date") or (datetime.today() + timedelta(days=1)).strftime("%d-%m-%Y")
    state_code = request.args.get("state_code")
    dist_code = request.args.get("district_code")
    complex_code = request.args.get("complex_code")
    est_code = request.args.get("est_code")
    judge_id = request.args.get("judge_id")
    update = request.args.get("update", "false").lower() == "true"

    try:
        if update:
            main(state_code, dist_code, complex_code, est_code, judge_id)

        with get_cursor() as cursor:
            query = "SELECT * FROM district_court_causelist WHERE causelist_date=%s"
            params = [convert_date(date_today)]
            if state_code: query += " AND state_code=%s"; params.append(state_code)
            if dist_code: query += " AND district_code=%s"; params.append(dist_code)
            if complex_code: query += " AND complex_code=%s"; params.append(complex_code)
            if est_code: query += " AND est_code=%s"; params.append(est_code)
            if judge_id: query += " AND judge_id=%s"; params.append(judge_id)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

        complex_dict = {}
        for row in rows:
            complex_key = (row["complex_code"], row["est_code"], row["judge_id"])
            if complex_key not in complex_dict:
                complex_dict[complex_key] = {
                    "district_name": row["district_name"],
                    "district_code": str(row["district_code"]),
                    "complex_name": row["complex_name"],
                    "complex_code": row["complex_code"],
                    "est_code": row["est_code"],
                    "judge_name": f"{row['judge_id']}:{row['judge_name']}",
                    "court_hall_address": row["judge_designation"],
                    "causelist_date": row["causelist_date"].strftime("%Y-%m-%d"),
                    "court_hall_no": f"CR NO {row['judge_id']}",
                    "note": row.get("note", ""),
                    "row_data": []
                }

            complex_dict[complex_key]["row_data"].append({
                "sno": row.get("sno"),
                "matter_type": row.get("matter_type"),
                "full_caseno": row.get("full_caseno"),
                "cnr_no": row.get("cnr_no"),
                "case_type": row.get("case_type"),
                "case_no": row.get("case_no"),
                "case_year": row.get("case_year"),
                "petitioner": row.get("petitioner"),
                "respondent": row.get("respondent"),
                "petitioner_advocate": row.get("petitioner_advocate"),
                "respondent_advocate": row.get("respondent_advocate"),
                'type': row.get('case_category')
            })

        for c in complex_dict.values():
            c["row_data"].sort(key=lambda x: int(x.get("sno") or 0))

        state_name = rows[0]["state_name"] if rows else ""
        state_code_str = str(rows[0]["state_code"]) if rows else ""

        final_json = {
            "status": "success",
            "count": len(rows),
            "message": "Data fetch completed",
            "data": {
                "state": state_name,
                "state_code": state_code_str,
                "complexes": list(complex_dict.values())
            }
        }

        return jsonify(final_json)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
# http://localhost/service_ecourt?state_code=3&district_code=20&complex_code=1030138&est_code=&judge_id=29&date=28-11-2025&update=false