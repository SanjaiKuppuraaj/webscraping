import sys
sys.path.insert(0, '/var/www/mml_python_code')
from flask import Blueprint, request, jsonify
from datetime import datetime
import threading
import time
from collections import defaultdict
from pathlib import Path
import json
import requests
from bs4 import BeautifulSoup as bs

from common_code import proxy_implement
from common_code import mysql_common

get_connection = mysql_common.get_conn()
get_cursor = mysql_common.get_cursor

service_bp = Blueprint("service_court", __name__)
request_method = proxy_implement.get_new_requests_proxy()

MAX_THREADS = 10

def convert_date(date_str):
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").strftime("%Y-%m-%d")
    except:
        return None


def create_tables():
    with get_cursor(dictionary=False) as cursor:
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
                    state_code, district_code, complex_code, est_code, judge_id, full_caseno, causelist_date, case_category
                )
            )
        """)

def fetch_court_data_from_db(state_code, dist_code=None, complex_code=None, est_code=None, judge_id=None):
    query = "SELECT * FROM court_data WHERE state_code=%s"
    params = [state_code]

    if dist_code:
        query += " AND district_code=%s"
        params.append(dist_code)
    if complex_code:
        query += " AND complex_code=%s"
        params.append(complex_code)
    if est_code:
        query += " AND est_id=%s"
        params.append(est_code)
    if judge_id:
        query += " AND judge_id=%s"
        params.append(judge_id)

    with get_cursor(dictionary=False) as cursor:
        cursor.execute(query, tuple(params))
        return cursor.fetchall()

def save_to_db(data):
    insert_query = """
        INSERT IGNORE INTO district_court_causelist (
            state_code,state_name,district_code,district_name,
            complex_code,complex_name,est_code,
            judge_id,judge_name,judge_designation,
            causelist_date,case_category,matter_type,sno,
            full_caseno,cnr_no,case_type,case_no,case_year,
            next_hearing_date,petitioner,respondent,
            petitioner_advocate,respondent_advocate,note
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    with get_cursor(dictionary=False) as cursor:
        cursor.execute(insert_query, (
            data.get("state_code"), data.get("state_name"), data.get("district_code"), data.get("district_name"),
            data.get("complex_code"), data.get("complex_name"), data.get("est_code"),
            data.get("judge_id"), data.get("judge_name"), data.get("judge_designation"),
            data.get("causelist_date"), data.get("case_category"), data.get("matter_type"), data.get("sno"),
            data.get("full_caseno"), data.get("cnr_no"), data.get("case_type"), data.get("case_no"), data.get("case_year"),
            data.get("next_hearing_date"), data.get("petitioner"), data.get("respondent"),
            data.get("petitioner_advocate"), data.get("respondent_advocate"), data.get("note")
        ))


def mark_queue_completed(state_code, dist_code, est_code, complex_code, judge_id):
    return

def fetch_data(row, date_today):
    state_code, state_name, dist_code, dist_name, complex_code, complex_name, est_code, judge_id, judge_name, judge_designation, judge_fullname = row[1:12]
    print(f"[INFO] Fetching => {dist_name} | {state_name} | {complex_code} | {est_code} | {judge_fullname}")

    try:
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

            url = "https://services.ecourts.gov.in/ecourtindia_v6/?p=cause_list/submitCauseList"
            headers = {
                'user-agent': 'Mozilla/5.0',
                'x-requested-with': 'XMLHttpRequest',
                'referer': 'https://services.ecourts.gov.in/'
            }

            response = requests.post(
                url,
                data=payload,
                proxies=request_method,
                headers=headers,
                timeout=20
            )

            html = bs(response.json().get('case_data', ''), 'html.parser')
            tbody = html.find("tbody")
            if not tbody:
                continue

            matter_type = ""
            for tr in tbody.find_all("tr"):
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
                link = case_td.find("a")

                if link and "onclick" in link.attrs:
                    try:
                        parts = link["onclick"].split("('")[1].split(",")
                        sol["full_caseno"] = parts[0].replace("'", "")
                        sol["cnr_no"] = parts[1].replace("'", "")
                    except:
                        sol["full_caseno"] = ""
                        sol["cnr_no"] = ""

                details_text = case_td.get_text(" ", strip=True).replace("View", "")
                case_details = details_text.split("Next")[0].split("/")

                if len(case_details) >= 3:
                    sol["case_type"] = case_details[0].strip()
                    sol["case_no"] = case_details[1].strip()
                    sol["case_year"] = case_details[2].strip()
                else:
                    sol["case_type"] = sol["case_no"] = sol["case_year"] = None

                party_td = case_td.find_next("td")
                if party_td:
                    parties = party_td.get_text(" ", strip=True).split("versus")
                    sol["petitioner"] = parties[0].strip()
                    sol["respondent"] = parties[1].strip() if len(parties) > 1 else ""

                    adv_td = party_td.find_next("td")
                    if adv_td:
                        advs = adv_td.get_text(" ", strip=True).split("versus")
                        sol["petitioner_advocate"] = advs[0].strip() if advs else ""
                        sol["respondent_advocate"] = advs[1].strip() if len(advs) > 1 else ""

                sol["note"] = ""

                save_to_db(sol)

        mark_queue_completed(state_code, dist_code, est_code, complex_code, judge_id)

    except Exception as e:
        print(f"[ERROR] {judge_fullname}: {e}")


@service_bp.route("/service_ecourt", methods=["GET"])
def fetch_court_data_route():
    state_code = request.args.get("state_code", type=int)
    dist_code = request.args.get("district_code", type=int)
    complex_code = request.args.get("complex_code", type=int)
    est_code = request.args.get("est_code", type=int)
    judge_id = request.args.get("judge_id", type=int)
    date_today = request.args.get("date", datetime.today().strftime("%d-%m-%Y"))
    update_flag = request.args.get("update", "true").lower()

    if not state_code:
        return jsonify({"status": "error", "message": "state_code is required"}), 400

    out_dir = Path("/var/www/mml_python_code/output/service_ecourt_causelist")
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{date_today}.json"
    save_path = out_dir / filename

    if update_flag == "false":
        if save_path.exists():
            return jsonify(json.loads(save_path.read_text()))
        return jsonify({"status": "error", "message": "Stored file not found"}), 404

    create_tables()
    results = fetch_court_data_from_db(state_code, dist_code, complex_code, est_code, judge_id)

    if results:
        threads = []
        for row in results:
            while threading.active_count() > MAX_THREADS:
                time.sleep(0.2)
            t = threading.Thread(target=fetch_data, args=(row, date_today))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

    query = "SELECT * FROM district_court_causelist WHERE state_code=%s AND causelist_date=%s"
    params = [state_code, convert_date(date_today)]
    with get_cursor(dictionary=True) as cursor:
        cursor.execute(query, tuple(params))
        all_rows = cursor.fetchall()

    if not all_rows:
        if save_path.exists():
            return jsonify(json.loads(save_path.read_text()))
        return jsonify({
            "status": "success",
            "message": "No record found.",
            "count": 0,
            "data": {"states": []}
        })

    districts_dict = defaultdict(list)
    for row in all_rows:
        districts_dict[(row["district_code"], row["district_name"])].append(row)

    new_districts = []
    for (d_code, d_name), rows in districts_dict.items():
        complexes_dict = defaultdict(list)
        for r in rows:
            key = (
                r["complex_code"],
                r["complex_name"],
                r["est_code"],
                r["judge_id"],
                r["judge_name"],
                r["judge_designation"]
            )
            complexes_dict[key].append(r)

        complex_list = []
        for (complex_code, complex_name, est_code, judge_id, judge_name, judge_designation), cases in complexes_dict.items():
            row_data = []
            for c in cases:
                row_data.append({
                    "sno": c.get("sno"),
                    "matter_type": c.get("matter_type"),
                    "full_caseno": c.get("full_caseno"),
                    "cnr_no": c.get("cnr_no"),
                    "case_type": c.get("case_type"),
                    "case_no": c.get("case_no"),
                    "case_year": c.get("case_year"),
                    "petitioner": c.get("petitioner"),
                    "respondent": c.get("respondent"),
                    "petitioner_advocate": c.get("petitioner_advocate"),
                    "respondent_advocate": c.get("respondent_advocate")
                })

            complex_list.append({
                "judge_name": f"{judge_id}:{judge_name}",
                "court_hall_address": judge_designation,
                "causelist_date": convert_date(date_today),
                "court_hall_no": f"CR NO {judge_id}",
                "note": "" if row_data else "No records found",
                "complex_name": complex_name,
                "complex_code": complex_code,
                "est_code": est_code,
                "row_data": row_data
            })

        new_districts.append({
            "district_name": d_name,
            "district_code": str(d_code),
            "complexes": complex_list
        })

    if save_path.exists():
        existing_json = json.loads(save_path.read_text())
        existing_data = existing_json.get("data", {})
        existing_states = {s["state_code"]: s for s in existing_data.get("states", [])}

        existing_states[str(state_code)] = { "state": all_rows[0]["state_name"],"state_code": str(state_code), "districts": new_districts}

        final_data = {"status": "success","message": "Data fetch completed.","count": len(all_rows),"data": {"states": list(existing_states.values())}}
        save_path.write_text(json.dumps(final_data, indent=4))
        return jsonify(final_data)

    else:
        output_json = {
            "status": "success",
            "message": "Data fetch completed.",
            "count": len(all_rows),
            "data": {"states": [{ "state": all_rows[0]["state_name"],
                        "state_code": str(state_code),
                        "districts": new_districts}]}}
        save_path.write_text(json.dumps(output_json, indent=4))
        return jsonify(output_json)

# http://localhost/service_ecourt?state_code=10&district_code=12&complex_code=1100119&est_code=2&judge_id=&date=13-10-2025&update=true