import mysql.connector

# Connect to MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="sanjai",
    database="ecourts_db"
)
cursor = conn.cursor()

# Create table if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS maha_disposed (
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
        AppearingFor VARCHAR(100),
        OpponentAs VARCHAR(100),
        new_act_type VARCHAR(255),
        UNIQUE KEY unique_case (act_code, full_case_no, cnr_no)
    );
""")
conn.commit()
for col in ["AppearingFor", "OpponentAs", "new_act_type"]:
    cursor.execute(f"SHOW COLUMNS FROM maha_disposed LIKE '{col}';")
    if cursor.fetchone() is None:
        cursor.execute(f"ALTER TABLE maha_disposed ADD COLUMN {col} VARCHAR(255);")
        conn.commit()

state_patterns = [
    r'^state'
]
keywords = [
    'agri.', 'Agriculture', 'Inspector', 'State of', 'Government of', 'Gov.', 'Govt.',
    'The state', 'maharashtra state', 'Maha State', 'of Maharashtra', 'StateofMaharashtra',
    'State Maharashtra', 'State  of Maharashtra', 'STATE  OF MAHARASHTRA', 'The  State',
    'Stateof Maharashtra', 'StateFertilizer', 'State.', 'State,', 'State through', 'State thr.',
    'State thou', 'State Represented', 'Stat of Maharashtra', 'Stat of Mah'
]

for pattern in state_patterns:

    cursor.execute(f"""
        UPDATE maha_disposed
        SET AppearingFor = 'Petitioner',
            OpponentAs = 'Respondent'
        WHERE LOWER(petitioner) REGEXP '{pattern}';
    """)

    # Match in respondent (State as Respondent)
    cursor.execute(f"""
        UPDATE maha_disposed
        SET AppearingFor = 'Respondent',
            OpponentAs = 'Petitioner'
        WHERE LOWER(respondent) REGEXP '{pattern}';
    """)

conn.commit()

new_act_type = {
    'Essential Commodities (Special Provisions) Act': 'Essential Commodities Act 1955',
    'The Fertilizer (Control) Order Act': 'Fertilizer Control Order 1985',
    'Seeds Act': 'Seed Act 1966',
    'Maharashtra Cotton Seeds Regulation Act': 'Maharashtra Cotton Seed Act 2009',
    'Insecticides Act': 'Insecticides Act 1968',
    'Seeds Rules': 'Seed Rules 1968'
}

for old_act, new_act in new_act_type.items():
    cursor.execute("""
        UPDATE maha_disposed
        SET new_act_type = %s
        WHERE act_type = %s;
    """, (new_act, old_act))

conn.commit()

cursor.execute("""
    SELECT * FROM maha_disposed
    WHERE AppearingFor IS NOT NULL
       OR OpponentAs IS NOT NULL;
""")

for row in cursor.fetchall():
    print(row)

cursor.close()
conn.close()















# import mysql.connector
#
# conn = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password="sanjai",
#     database="ecourts_db"
# )
# cursor = conn.cursor()
#
# cursor.execute("""
#     CREATE TABLE IF NOT EXISTS cases_disposed (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         state_name VARCHAR(255),
#         state_code INT,
#         district_name VARCHAR(255),
#         district_code INT,
#         complex_name VARCHAR(255),
#         complex_code INT,
#         act_type VARCHAR(255),
#         act_code INT,
#         sno INT,
#         case_no VARCHAR(100),
#         petitioner TEXT,
#         respondent TEXT,
#         full_case_no VARCHAR(255),
#         cnr_no VARCHAR(255),
#         case_status VARCHAR(50),
#         AppearingFor VARCHAR(100),
#         OpponentAs VARCHAR(100),
#         new_act_type VARCHAR(255),
#         UNIQUE KEY unique_case (act_code, full_case_no, cnr_no)
#     );
# """)
# conn.commit()
#
# for col in ["AppearingFor", "OpponentAs", "new_act_type"]:
#     cursor.execute(f"SHOW COLUMNS FROM cases_disposed LIKE '{col}';")
#     if cursor.fetchone() is None:
#         cursor.execute(f"ALTER TABLE cases_disposed ADD COLUMN {col} VARCHAR(255);")
#         conn.commit()
#
# keywords = [
#     'agri.', 'Agriculture', 'Inspector', 'State of', 'Government of', 'Gov.', 'Govt.',
#     'The state', 'maharashtra state', 'Maha State', 'of Maharashtra', 'StateofMaharashtra',
#     'State Maharashtra', 'State  of Maharashtra', 'STATE  OF MAHARASHTRA', 'The  State',
#     'Stateof Maharashtra', 'StateFertilizer', 'State.', 'State,', 'State through', 'State thr.',
#     'State thou', 'State Represented', 'Stat of Maharashtra', 'Stat of Mah'
# ]
#
# for kw in keywords:
#     kw_lower = kw.lower()
#
#     cursor.execute(f"""
#         UPDATE cases_disposed
#             SET AppearingFor = 'Petitioner', OpponentAs = 'Respondent'
#         WHERE LOWER(petitioner) LIKE '%{kw_lower}%';
#     """)
#
#     cursor.execute(f"""
#         UPDATE cases_disposed
#         SET AppearingFor = 'Respondent', OpponentAs = 'Petitioner'
#         WHERE LOWER(respondent) LIKE '%{kw_lower}%';
#     """)
# conn.commit()
#
# new_act_type = {
#     'Essential Commodities (Special Provisions) Act': 'Essential Commodities Act 1955',
#     'The Fertilizer (Control) Order Act': 'Fertilizer Control Order 1985',
#     'Seeds Act': 'Seed Act 1966',
#     'Maharashtra Cotton Seeds Regulation Act': 'Maharashtra Cotton Seed Act 2009',
#     'Insecticides Act': 'Insecticides Act 1968',
#     'Seeds Rules': 'Seed Rules 1968'
# }
#
# for old_act, new_act in new_act_type.items():
#     cursor.execute("""
#         UPDATE cases_disposed
#         SET new_act_type = %s
#         WHERE act_type = %s;
#     """, (new_act, old_act))
# conn.commit()
#
# query_conditions = " OR ".join(
#     [f"LOWER(petitioner) LIKE '%{kw.lower()}%' OR LOWER(respondent) LIKE '%{kw.lower()}%'" for kw in keywords]
# )
# cursor.execute(f"SELECT * FROM cases_disposed WHERE {query_conditions}")
#
# rows = cursor.fetchall()
# for row in rows:
#     print(row)
#
# cursor.close()
# conn.close()











# ------------------------------------------------------------------------------
# import mysql.connector
# import requests
# from bs4 import BeautifulSoup as bs
# import pandas as pd
# import time
#
# conn = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password="sanjai",
#     database='ecourts_db'
# )
#
# cursor = conn.cursor(dictionary=True)
# query = "SELECT * FROM court_data WHERE state_code = 1;"
# cursor.execute(query)
# results = cursor.fetchall()
#
# all_data = []
# headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
#
# act_code = 133
#
# for row in results:
#     urls = 'https://services.ecourts.gov.in/ecourtindia_v6/?p=casestatus/submitAct'
#     payload = {
#         "search_act": "",
#         "actcode": act_code,
#         "under_sec": "",
#         "case_status": "Pending",
#         "act_captcha_code": "",
#         "state_code": 1,
#         "dist_code": row['district_code'],
#         "court_complex_code": row['complex_code'],
#         "est_code": None,
#         "ajax_req": True,
#         "app_token": ""
#     }
#
#     try:
#         print(f"Fetching: {row['district_name']} ({row['complex_name']})...")
#         response = requests.post(urls, data=payload, headers=headers, timeout=15)
#         response.raise_for_status()
#         response_json = response.json()
#         if 'act_data' not in response_json:
#             print("No act_data found, skipping...")
#             continue
#
#         soup = bs(response_json['act_data'], 'html.parser')
#         table = soup.find('table')
#
#         if not table:
#             print("No table found in response.")
#             continue
#
#         for tr in table.find_all('tr'):
#             tds = tr.find_all('td')
#             if not tds or tds[0].has_attr('colspan'):
#                 continue
#
#             sol = {
#                 'state_name': row['state_name'],
#                 'district_name': row['district_name'],
#                 'complex_name': row['complex_name'],
#                 'act_type': 'The Fertilizer (Control) Order Act',
#                 'act_code':act_code,
#                 'sno': tds[0].get_text(strip=True),
#                 'case_no': tds[1].get_text(strip=True)
#             }
#
#             case_type = str(tds[2].get_text(strip=True)).split('Vs')
#             sol['petitioner'] = case_type[0]
#             sol['respondent'] = case_type[1] if len(case_type) > 1 else ''
#
#             filed_on = str(tds[3]).split('viewHistory(')[-1].split(')">')[0].split(',')
#             sol['full_case_no'] = filed_on[0]
#             sol['cnr_no'] = filed_on[1].replace("'", '').strip() if len(filed_on) > 1 else ''
#
#             all_data.append(sol)
#
#         time.sleep(2)
#
#     except requests.exceptions.RequestException as e:
#         print(f" Error fetching data for {row['district_name']}: {e}")
#         time.sleep(5)
#         continue
#
#
# df = pd.DataFrame(all_data)
# df.to_csv('ecourt_FULL.csv', index=False, encoding='utf-8-sig')
#
# print("\nSaved all data to ecourt_FULL.csv")
#
# cursor.close()
# conn.close()
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
#
# # import mysql.connector
# # import requests
# # from bs4 import BeautifulSoup as bs
# # import pandas as pd
# #
# # # MySQL connection
# # conn = mysql.connector.connect(
# #     host="localhost",
# #     user="root",
# #     password="sanjai",
# #     database='ecourts_db'
# # )
# #
# # cursor = conn.cursor(dictionary=True)
# # query = "SELECT * FROM court_data WHERE state_code = 1 and district_code=1;"
# # query = "SELECT * FROM court_data WHERE state_code = 1 ;"
# # cursor.execute(query)
# # results = cursor.fetchall()
# #
# # all_data = []  # to collect all rows for Excel
# #
# # for row in results:
# #     urls = 'https://services.ecourts.gov.in/ecourtindia_v6/?p=casestatus/submitAct'
# #     payload = {
# #         "search_act": "",
# #         "actcode": "133",  # the fertizi
# #         "under_sec": "",
# #         "case_status": "Pending",
# #         "act_captcha_code": "",
# #         "state_code": 1,
# #         "dist_code": row['district_code'],
# #         "court_complex_code": row['complex_code'],
# #         "est_code": None,
# #         "ajax_req": True,
# #         "app_token": ""
# #     }
# #
# #     response = requests.post(urls, data=payload)
# #     response_json = response.json()
# #
# #     if 'act_data' not in response_json:
# #         continue
# #
# #     soup = bs(response_json['act_data'], 'html.parser')
# #     table_rows = soup.find('table')
# #     if table_rows:
# #         table_rows = table_rows.find_all('tr')
# #         for data in table_rows:
# #             tds = data.find_all('td')
# #             if not tds or tds[0].has_attr('colspan'):
# #                 continue
# #
# #             sol = dict()
# #             sol['state_name'] = row['state_name']
# #             sol['district_name'] = row['district_name']
# #             sol['complex_name'] = row['complex_name']
# #             sol['act_type'] = 'The Fertilizer (Control) Order Act'
# #             sol['sno'] = tds[0].get_text(strip=True)
# #             sol['case_no'] = tds[1].get_text(strip=True)
# #
# #             case_type = str(tds[2].get_text(strip=True)).split('Vs')
# #             sol['petitioner'] = case_type[0]
# #             sol['respondent'] = case_type[1] if len(case_type) > 1 else ''
# #
# #             filed_on = str(tds[3]).split('viewHistory(')[-1].split(')">')[0].split(',')
# #             sol['full_case_no'] = filed_on[0]
# #             sol['cnr_no'] = filed_on[1].replace("'", '').strip() if len(filed_on) > 1 else ''
# #
# #             all_data.append(sol)
# #
# # df = pd.DataFrame(all_data)
# # df.to_excel('ecourt_FULL.xlsx', index=False)
# # print("Saved all data to ecourt_cases.xlsx")
# #
# # cursor.close()
# # conn.close()
#
#
#
#
# # import mysql.connector
# # import requests
# # from bs4 import BeautifulSoup as bs
# #
# # conn = mysql.connector.connect(
# #     host="localhost",
# #     user="root",
# #     password="sanjai",
# #     database='ecourts_db'
# # )
# #
# # cursor = conn.cursor(dictionary=True)
# # query = "SELECT * FROM court_data WHERE state_code = 1 and district_code=1;"
# # cursor.execute(query)
# # results = cursor.fetchall()
# # for row in results:
# #     urls = 'https://services.ecourts.gov.in/ecourtindia_v6/?p=casestatus/submitAct'
# #     payload = {
# #     "search_act": "",
# #     "actcode": "133",# the fertizi
# #     "under_sec": "",
# #     "case_status" : "Pending",
# #     "act_captcha_code": "",
# #     "state_code": 1,
# #     "dist_code": row['district_code'],
# #     "court_complex_code": row['complex_code'],
# #     "est_code": None,
# #     "ajax_req": True,
# #     "app_token": ""}
# #
# #     response = requests.post(urls,data=payload)
# #     response = bs(response.json()['act_data'],'html.parser')
# #     response = response.find('table').find_all('tr')
# #     for data in response:
# #         sol = dict()
# #         tds = data.find_all('td')
# #         if not tds or tds[0].has_attr('colspan'):
# #             continue
# #
# #         sol['state_name'] = row['state_name']
# #         sol['district_name'] = row['district_name']
# #         sol['act'] = ''
# #         sol['sno'] = tds[0].get_text(strip=True)
# #         sol['case_no'] = tds[1].get_text(strip=True)
# #         case_type = str(tds[2].get_text(strip=True)).split('Vs')
# #         sol['petitioner'] = case_type[0]
# #         sol['respondent'] = case_type[1]
# #         filed_on = str(tds[3]).split('viewHistory(')[-1].split(')">')[0].split(',')
# #         sol['full_case_no'] = filed_on[0]
# #         sol['cnr_no'] = filed_on[1].replace("'",'').strip()
# #         print(sol)
# #
# #     exit()
# #
# # cursor.close()
# # conn.close()
