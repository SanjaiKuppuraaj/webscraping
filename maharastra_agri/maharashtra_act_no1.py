import mysql.connector
import requests
from bs4 import BeautifulSoup as bs
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

headers = {"User-Agent": "Mozilla/5.0"}
session = requests.Session()
session.headers.update(headers)

acts = {
    5: 'Essential Commodities (Special Provisions) Act',
    897: 'Essential Commodities (Special Provisions) Act',
    133: 'The Fertilizer (Control) Order Act',
    2143: 'Maharashtra Cotton Seeds Regulation Act',
    82: 'Insecticides Act',
    89: 'Seeds Act',
    1858: 'Seeds Rules'
}

case_status = 'Pending'

def get_db():
    return mysql.connector.connect(host="localhost",user="root", password="sanjai",database='ecourts_db')

def post_retry(url, data):
    for attempt in range(4):
        try:
            res = session.post(url, data=data, timeout=45)
            res.raise_for_status()
            return res
        except Exception as e:
            if attempt == 3:
                raise e
            time.sleep(2 + random.random() * 2)

def scrape_complex(row):
    state_name = row['state_name']
    state_code = row['state_code']
    district_name = row['district_name']
    district_code = row['district_code']
    complex_name = row['complex_name']
    complex_code = row['complex_code']
    print(f"Thread started → {district_name} | {complex_name}")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    local_inserted = set()

    for act_code, act_name in acts.items():
        payload = {
            "search_act": "",
            "actcode": act_code,
            "under_sec": "",
            "case_status": case_status,
            "act_captcha_code": "",
            "state_code": state_code,
            "dist_code": district_code,
            "court_complex_code": complex_code,
            "est_code": None,
            "ajax_req": True,
            "app_token": ""
        }

        url = "https://services.ecourts.gov.in/ecourtindia_v6/?p=casestatus/submitAct"

        try:
            res = post_retry(url, payload)
            js = res.json()
            if "act_data" not in js:
                continue

            soup = bs(js["act_data"], "html.parser")
            table = soup.find("table")
            if not table:
                continue

            batch = []

            for tr in table.find_all("tr"):
                tds = tr.find_all("td")
                if not tds or tds[0].has_attr("colspan"):
                    continue

                parties = tds[2].get_text(strip=True).split("Vs")
                raw = str(tds[3]).split("viewHistory(")[-1].split(')">')[0].split(",")
                full_case = raw[0].strip()
                cnr = raw[1].replace("'", "").strip() if len(raw) > 1 else ""

                key = (complex_code, act_code, full_case, cnr)
                if key in local_inserted:
                    continue

                now = datetime.now()
                data_row = {
                    'state_name': state_name,
                    'state_code': state_code,
                    'district_name': district_name,
                    'district_code': district_code,
                    'complex_name': complex_name,
                    'complex_code': complex_code,
                    'act_type': act_name,
                    'act_code': act_code,
                    'sno': tds[0].get_text(strip=True),
                    'case_no': tds[1].get_text(strip=True),
                    'petitioner': parties[0],
                    'respondent': parties[1] if len(parties) > 1 else '',
                    'full_case_no': full_case,
                    'cnr_no': cnr,
                    'case_status': case_status,
                    'created_at': now,
                    'updated_at': now
                }
                batch.append(data_row)
                local_inserted.add(key)

            if batch:
                for attempt in range(3):
                    try:
                        cursor.executemany("""
                            INSERT INTO maha_act
                            (state_name, state_code, district_name, district_code, 
                            complex_name, complex_code, act_type, act_code, sno, case_no, 
                            petitioner, respondent, full_case_no, cnr_no, case_status, created_at, updated_at)
                            VALUES (%(state_name)s, %(state_code)s, %(district_name)s, %(district_code)s,
                                    %(complex_name)s, %(complex_code)s, %(act_type)s, %(act_code)s,
                                    %(sno)s, %(case_no)s, %(petitioner)s, %(respondent)s,
                                    %(full_case_no)s, %(cnr_no)s, %(case_status)s, %(created_at)s, %(updated_at)s)
                            ON DUPLICATE KEY UPDATE updated_at=VALUES(updated_at)
                        """, batch)
                        conn.commit()
                        break
                    except mysql.connector.errors.DatabaseError as e:
                        if "1213" in str(e):
                            print(f"[Deadlock retry] {district_name} - {complex_name} - {act_code}")
                            time.sleep(random.uniform(1, 3))
                        else:
                            raise

            time.sleep(1 + random.random() * 1.5)

        except Exception as e:
            print(f"[ERR] {district_name} - {complex_name} - {act_code}: {e}")
            time.sleep(3)
            continue

    cursor.close()
    conn.close()
    print(f"Thread DONE → {district_name} | {complex_name}")
    return f"{district_name} - {complex_name} completed."

if __name__ == "__main__":
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maha_act (
            id INT AUTO_INCREMENT PRIMARY KEY,
            state_name VARCHAR(255),
            state_code INT,
            district_name VARCHAR(255),
            district_code INT,
            complex_name VARCHAR(255),
            complex_code INT,
            act_type VARCHAR(255),
            act_code INT,
            sno INT,
            case_no VARCHAR(100),
            petitioner TEXT,
            respondent TEXT,
            full_case_no VARCHAR(255),
            cnr_no VARCHAR(255),
            case_status VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_case (act_code, full_case_no, cnr_no)
        );
    """)
    conn.commit()

    cursor.execute("""
        SELECT DISTINCT 
            district_code, complex_code, district_name, complex_name, state_name, state_code
        FROM court_data
        WHERE state_code = 1
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    print(f"Total tasks: {len(rows)}\n")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(scrape_complex, r) for r in rows]
        for future in as_completed(futures):
            print(future.result())

    print("\nAll threaded scraping done.")























# import mysql.connector
# import requests
# from bs4 import BeautifulSoup as bs
# import time
# import random
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from datetime import datetime
#
# headers = {"User-Agent": "Mozilla/5.0"}
# acts = {
#     5: 'Essential Commodities (Special Provisions) Act',
#     897: 'Essential Commodities (Special Provisions) Act',
#     133: 'The Fertilizer (Control) Order Act',
#     2143: 'Maharashtra Cotton Seeds Regulation Act',
#     82: 'Insecticides Act',
#     89: 'Seeds Act',
#     1858: 'Seeds Rules'
# }
#
# # case_status = 'Disposed'
# case_status = 'Pending'
#
# def get_db():
#     return mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password="sanjai",
#         database='ecourts_db')
#
# session = requests.Session()
# session.headers.update(headers)
#
# def post_retry(url, data):
#     for attempt in range(4):
#         try:
#             res = session.post(url, data=data, timeout=45)
#             res.raise_for_status()
#             return res
#         except Exception as e:
#             if attempt == 4 - 1:
#                 raise e
#             time.sleep(2 + random.random() * 2)
#
#
# def scrape_complex(row):
#     state_name = row['state_name']
#     state_code = row['state_code']
#     district_name = row['district_name']
#     district_code = row['district_code']
#     complex_name = row['complex_name']
#     complex_code = row['complex_code']
#     print(f"Thread started → {district_name} | {complex_name}")
#
#     conn = get_db()
#     cursor = conn.cursor(dictionary=True)
#     local_inserted = set()
#
#     for act_code, act_name in acts.items():
#         payload = {
#             "search_act": "",
#             "actcode": act_code,
#             "under_sec": "",
#             "case_status": case_status,
#             "act_captcha_code": "",
#             "state_code": state_code,
#             "dist_code": district_code,
#             "court_complex_code": complex_code,
#             "est_code": None,
#             "ajax_req": True,
#             "app_token": ""
#         }
#
#         url = "https://services.ecourts.gov.in/ecourtindia_v6/?p=casestatus/submitAct"
#
#         try:
#             res = post_retry(url, payload)
#             js = res.json()
#
#             if "act_data" not in js:
#                 continue
#
#             soup = bs(js["act_data"], "html.parser")
#             table = soup.find("table")
#             if not table:
#                 continue
#
#             for tr in table.find_all("tr"):
#                 tds = tr.find_all("td")
#                 if not tds or tds[0].has_attr("colspan"):
#                     continue
#
#                 parties = tds[2].get_text(strip=True).split("Vs")
#                 raw = str(tds[3]).split("viewHistory(")[-1].split(')">')[0].split(",")
#                 full_case = raw[0].strip()
#                 cnr = raw[1].replace("'", "").strip() if len(raw) > 1 else ""
#
#                 key = (complex_code, act_code, full_case, cnr)
#                 if key in local_inserted:
#                     continue
#
#                 now = datetime.now()
#                 data_row = {
#                     'state_name': state_name,
#                     'state_code': state_code,
#                     'district_name': district_name,
#                     'district_code': district_code,
#                     'complex_name': complex_name,
#                     'complex_code': complex_code,
#                     'act_type': act_name,
#                     'act_code': act_code,
#                     'sno': tds[0].get_text(strip=True),
#                     'case_no': tds[1].get_text(strip=True),
#                     'petitioner': parties[0],
#                     'respondent': parties[1] if len(parties) > 1 else '',
#                     'full_case_no': full_case,
#                     'cnr_no': cnr,
#                     'case_status': case_status,
#                     'created_at': now,
#                     'updated_at': now
#                 }
#
#                 try:
#                     cursor.execute(
#                         """
#                         INSERT INTO cases
#                         (state_name, state_code, district_name, district_code,
#                         complex_name, complex_code, act_type, act_code, sno, case_no,
#                         petitioner, respondent, full_case_no, cnr_no, case_status, created_at, updated_at)
#                         VALUES (%(state_name)s, %(state_code)s, %(district_name)s, %(district_code)s,
#                                 %(complex_name)s, %(complex_code)s, %(act_type)s, %(act_code)s,
#                                 %(sno)s, %(case_no)s, %(petitioner)s, %(respondent)s,
#                                 %(full_case_no)s, %(cnr_no)s, %(case_status)s, %(created_at)s, %(updated_at)s)
#                         """,
#                         data_row
#                     )
#
#                     conn.commit()
#                     local_inserted.add(key)
#                 except mysql.connector.errors.IntegrityError:
#                     pass
#
#             time.sleep(1 + random.random() * 1.5)
#
#         except Exception as e:
#             print(f"[ERR] {district_name} - {complex_name} - {act_code}: {e}")
#             time.sleep(3)
#             continue
#     cursor.close()
#     conn.close()
#     print(f"Thread DONE → {district_name} | {complex_name}")
#     return f"{district_name} - {complex_name} completed."
#
# if __name__ == "__main__":
#     conn = get_db()
#     cursor = conn.cursor(dictionary=True)
#     cursor.execute("""
#         CREATE TABLE IF NOT EXISTS cases (
#             id INT AUTO_INCREMENT PRIMARY KEY,
#             state_name VARCHAR(255),
#             state_code INT,
#             district_name VARCHAR(255),
#             district_code INT,
#             complex_name VARCHAR(255),
#             complex_code INT,
#             act_type VARCHAR(255),
#             act_code INT,
#             sno INT,
#             case_no VARCHAR(100),
#             petitioner TEXT,
#             respondent TEXT,
#             full_case_no VARCHAR(255),
#             cnr_no VARCHAR(255),
#             case_status VARCHAR(50),
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
#             UNIQUE KEY unique_case (act_code, full_case_no, cnr_no)
#         );
#     """)
#     conn.commit()
#     cursor.execute("""
#         SELECT DISTINCT
#             district_code, complex_code, district_name, complex_name, state_name, state_code
#         FROM court_data
#         WHERE state_code = 1
#     """)
#
#     rows = cursor.fetchall()
#     cursor.close()
#     conn.close()
#     print(f"Total tasks: {len(rows)}\n")
#     with ThreadPoolExecutor(max_workers=5) as executor:
#         futures = [executor.submit(scrape_complex, r) for r in rows]
#         for future in as_completed(futures):
#             print(future.result())
#     print("\nAll threaded scraping done.")
#
#
#
#
#
#
#
#
#
#
#
# # import mysql.connector
# # import requests
# # from bs4 import BeautifulSoup as bs
# # import time
# # import random
# # from concurrent.futures import ThreadPoolExecutor, as_completed
# #
# # headers = {"User-Agent": "Mozilla/5.0"}
# #
# # acts = {
# #     5:  'Essential Commodities (Special Provisions) Act',
# #     897: 'Essential Commodities (Special Provisions) Act',
# #     133: 'The Fertilizer (Control) Order Act',
# #     2143: 'Maharashtra Cotton Seeds Regulation Act',
# #     82:  'Insecticides Act',
# #     89:  'Seeds Act',
# #     1858: 'Seeds Rules'
# # }
# #
# # case_status = 'Disposed'
# # # case_status = 'Pending'
# #
# # # WORKERS = 5
# # # MAX_RETRIES = 4
# #
# # def get_db():
# #     return mysql.connector.connect(
# #         host="localhost",
# #         user="root",
# #         password="sanjai",
# #         database='ecourts_db'
# #     )
# #
# # session = requests.Session()
# # session.headers.update(headers)
# #
# # def post_retry(url, data):
# #     for attempt in range(4):
# #         try:
# #             res = session.post(url, data=data, timeout=45)
# #             res.raise_for_status()
# #             return res
# #         except Exception as e:
# #             if attempt == 4 - 1:
# #                 raise e
# #             time.sleep(2 + random.random() * 2)
# #
# # def scrape_complex(row):
# #     state_name = row['state_name']
# #     state_code = row['state_code']
# #     district_name = row['district_name']
# #     district_code = row['district_code']
# #     complex_name = row['complex_name']
# #     complex_code = row['complex_code']
# #     print(f"Thread started → {district_name} | {complex_name}")
# #     conn = get_db()
# #     cursor = conn.cursor(dictionary=True)
# #     local_inserted = set()
# #     for act_code, act_name in acts.items():
# #         payload = {
# #             "search_act": "",
# #             "actcode": act_code,
# #             "under_sec": "",
# #             "case_status": case_status,
# #             "act_captcha_code": "",
# #             "state_code": state_code,
# #             "dist_code": district_code,
# #             "court_complex_code": complex_code,
# #             "est_code": None,
# #             "ajax_req": True,
# #             "app_token": ""
# #         }
# #
# #         url = "https://services.ecourts.gov.in/ecourtindia_v6/?p=casestatus/submitAct"
# #
# #         try:
# #             res = post_retry(url, payload)
# #             js = res.json()
# #
# #             if "act_data" not in js:
# #                 continue
# #
# #             soup = bs(js["act_data"], "html.parser")
# #             table = soup.find("table")
# #             if not table:
# #                 continue
# #
# #             for tr in table.find_all("tr"):
# #                 tds = tr.find_all("td")
# #                 if not tds or tds[0].has_attr("colspan"):
# #                     continue
# #
# #                 parties = tds[2].get_text(strip=True).split("Vs")
# #
# #                 raw = str(tds[3]).split("viewHistory(")[-1].split(')">')[0].split(",")
# #                 full_case = raw[0].strip()
# #                 cnr = raw[1].replace("'", "").strip() if len(raw) > 1 else ""
# #
# #                 key = (complex_code, act_code, full_case, cnr)
# #                 if key in local_inserted:
# #                     continue
# #
# #                 data_row = {
# #                     'state_name': state_name,
# #                     'state_code': state_code,
# #                     'district_name': district_name,
# #                     'district_code': district_code,
# #                     'complex_name': complex_name,
# #                     'complex_code': complex_code,
# #                     'act_type': act_name,
# #                     'act_code': act_code,
# #                     'sno': tds[0].get_text(strip=True),
# #                     'case_no': tds[1].get_text(strip=True),
# #                     'petitioner': parties[0],
# #                     'respondent': parties[1] if len(parties) > 1 else '',
# #                     'full_case_no': full_case,
# #                     'cnr_no': cnr,
# #                     'case_status': case_status
# #                 }
# #
# #                 try:
# #                     cursor.execute(
# #                         """
# #                         INSERT INTO cases
# #                         (state_name, state_code, district_name, district_code,
# #                         complex_name, complex_code, act_type, act_code, sno, case_no,
# #                         petitioner, respondent, full_case_no, cnr_no, case_status)
# #                         VALUES (%(state_name)s, %(state_code)s, %(district_name)s, %(district_code)s,
# #                                 %(complex_name)s, %(complex_code)s, %(act_type)s, %(act_code)s,
# #                                 %(sno)s, %(case_no)s, %(petitioner)s, %(respondent)s,
# #                                 %(full_case_no)s, %(cnr_no)s, %(case_status)s)
# #                         """,
# #                         data_row
# #                     )
# #                     conn.commit()
# #                     local_inserted.add(key)
# #
# #                 except mysql.connector.errors.IntegrityError:
# #                     pass
# #
# #             time.sleep(1 + random.random() * 1.5)
# #
# #         except Exception as e:
# #             print(f"[ERR] {district_name} - {complex_name} - {act_code}: {e}")
# #             time.sleep(3)
# #             continue
# #
# #     cursor.close()
# #     conn.close()
# #
# #     print(f"Thread DONE → {district_name} | {complex_name}")
# #     return f"{district_name} - {complex_name} completed."
# #
# # if __name__ == "__main__":
# #     conn = get_db()
# #     cursor = conn.cursor(dictionary=True)
# #
# #     cursor.execute("""
# #         CREATE TABLE IF NOT EXISTS cases (
# #             id INT AUTO_INCREMENT PRIMARY KEY,
# #             state_name VARCHAR(255),
# #             state_code INT,
# #             district_name VARCHAR(255),
# #             district_code INT,
# #             complex_name VARCHAR(255),
# #             complex_code INT,
# #             act_type VARCHAR(255),
# #             act_code INT,
# #             sno INT,
# #             case_no VARCHAR(100),
# #             petitioner TEXT,
# #             respondent TEXT,
# #             full_case_no VARCHAR(255),
# #             cnr_no VARCHAR(255),
# #             case_status VARCHAR(50),
# #             UNIQUE KEY unique_case (act_code, full_case_no, cnr_no)
# #         );
# #     """)
# #     conn.commit()
# #
# #     cursor.execute("""
# #         SELECT DISTINCT
# #             district_code, complex_code, district_name, complex_name, state_name, state_code
# #         FROM court_data
# #         WHERE state_code = 1
# #     """)
# #
# #     rows = cursor.fetchall()
# #     cursor.close()
# #     conn.close()
# #
# #     print(f"Total tasks: {len(rows)}\n")
# #     with ThreadPoolExecutor(max_workers=5) as executor:
# #         futures = [executor.submit(scrape_complex, r) for r in rows]
# #         for future in as_completed(futures):
# #             print(future.result())
# #     print("\nAll threaded scraping done.")
