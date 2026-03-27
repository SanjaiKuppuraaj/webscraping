import mysql.connector

#before running this code, date need to ro change

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="sanjai",
    database="ecourts_db"
)
cursor = conn.cursor(dictionary=True)

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

cursor.execute("""
INSERT IGNORE INTO maha_disposed (
    state_name, state_code, district_name, district_code,
    complex_name, complex_code, act_type, act_code,
    sno, case_no, petitioner, respondent,
    full_case_no, cnr_no, case_status
)
SELECT
    state_name, state_code, district_name, district_code,
    complex_name, complex_code, act_type, act_code,
    sno, case_no, petitioner, respondent,
    full_case_no, cnr_no, case_status
FROM maha_act
WHERE case_status = 'Pending'
  AND created_at LIKE '2026-03-04%';
""")
conn.commit()

print("today pending cases copied")

keywords = [
    'agri.', 'agriculture', 'inspector', 'state of', 'government of',
    'gov.', 'govt.', 'the state', 'maharashtra state', 'maha state',
    'of maharashtra', 'stateofmaharashtra', 'state maharashtra',
    'state  of maharashtra', 'the  state', 'stateof maharashtra',
    'statefertilizer', 'state.', 'state,', 'state through', 'state thr.',
    'state thou', 'state represented', 'stat of maharashtra', 'stat of mah'
]

cursor.execute("""
SELECT id, petitioner, respondent
FROM maha_disposed
WHERE case_status='Pending'
  AND AppearingFor IS NULL
""")

rows = cursor.fetchall()

for row in rows:
    pid = row["id"]
    pet = (row["petitioner"] or "").lower()
    res = (row["respondent"] or "").lower()

    pet_hit = any(k in pet for k in keywords)
    res_hit = any(k in res for k in keywords)

    if pet_hit:
        appearing = "Petitioner"
        opponent = "Respondent"
    elif res_hit:
        appearing = "Respondent"
        opponent = "Petitioner"
    else:
        continue

    cursor.execute("""
        UPDATE maha_disposed
        SET AppearingFor=%s,
            OpponentAs=%s
        WHERE id=%s
    """, (appearing, opponent, pid))

conn.commit()
print("appearing / opponent classified")

new_act_map = {
    'Essential Commodities (Special Provisions) Act': 'Essential Commodities Act 1955',
    'The Fertilizer (Control) Order Act': 'Fertilizer Control Order 1985',
    'Seeds Act': 'Seed Act 1966',
    'Maharashtra Cotton Seeds Regulation Act': 'Maharashtra Cotton Seed Act 2009',
    'Insecticides Act': 'Insecticides Act 1968',
    'Seeds Rules': 'Seed Rules 1968'
}

for old, new in new_act_map.items():
    cursor.execute("""
        UPDATE maha_disposed
        SET new_act_type=%s
        WHERE act_type=%s
    """, (new, old))

conn.commit()
print("act names normalized")

cursor.close()
conn.close()

print("PIPELINE DONE")









# import mysql.connector
#
# conn = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password="sanjai",
#     database='ecourts_db'
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
#     'agri.', 'agriculture', 'inspector', 'state of', 'government of',
#     'gov.', 'govt.', 'the state', 'maharashtra state', 'maha state',
#     'of maharashtra', 'stateofmaharashtra', 'state maharashtra',
#     'state  of maharashtra', 'the  state', 'stateof maharashtra',
#     'statefertilizer', 'state.', 'state,', 'state through', 'state thr.',
#     'state thou', 'state represented', 'stat of maharashtra', 'stat of mah'
# ]
#
# cursor = conn.cursor(dictionary=True)
# cursor.execute("SELECT id, petitioner, respondent FROM cases_disposed")
# rows = cursor.fetchall()
#
# for row in rows:
#     case_id = row['id']
#     petitioner = (row['petitioner'] or "").lower()
#     respondent = (row['respondent'] or "").lower()
#
#     pet_hit = any(kw in petitioner for kw in keywords)
#     res_hit = any(kw in respondent for kw in keywords)
#
#     if pet_hit:
#         appearing = "Petitioner"
#         opponent = "Respondent"
#
#     elif res_hit:
#         appearing = "Respondent"
#         opponent = "Petitioner"
#
#     else:
#         appearing = None
#         opponent = None
#
#     cursor.execute("""
#         UPDATE cases_disposed
#         SET AppearingFor=%s,
#             OpponentAs=%s
#         WHERE id=%s
#     """, (appearing, opponent, case_id))
#
# conn.commit()
#
# new_act_map = {
#     'Essential Commodities (Special Provisions) Act': 'Essential Commodities Act 1955',
#     'The Fertilizer (Control) Order Act': 'Fertilizer Control Order 1985',
#     'Seeds Act': 'Seed Act 1966',
#     'Maharashtra Cotton Seeds Regulation Act': 'Maharashtra Cotton Seed Act 2009',
#     'Insecticides Act': 'Insecticides Act 1968',
#     'Seeds Rules': 'Seed Rules 1968'
# }
#
# for old, new in new_act_map.items():
#     cursor.execute("""
#         UPDATE cases_disposed
#         SET new_act_type=%s
#         WHERE act_type=%s
#     """, (new, old))
#
# conn.commit()
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
#
#
#
#
#
#
#
# # import mysql.connector
# #
# # conn = mysql.connector.connect(
# #     host="localhost",
# #     user="root",
# #     password="sanjai",
# #     database='ecourts_db'
# # )
# # cursor = conn.cursor()
# #
# # # keywords that must be matched exactly as shown
# # keywords = [
# #     'agri.', 'Agriculture', 'Inspector', 'State of', 'Government of',
# #     'Gov.', 'Govt.', 'The state', 'maharashtra state', 'Maha State',
# #     'of Maharashtra', 'StateofMaharashtra', 'State Maharashtra',
# #     'State  of Maharashtra', 'STATE  OF MAHARASHTRA', 'The  State',
# #     'Stateof Maharashtra', 'StateFertilizer', 'State.', 'State,',
# #     'State through', 'State thr.', 'State thou', 'State Represented',
# #     'Stat of Maharashtra', 'Stat of Mah'
# # ]
# #
# # # build LIKE-safe conditions
# # def build_like_conditions(column):
# #     conds = []
# #     for kw in keywords:
# #         kw_low = kw.lower()
# #         conds.append(f"LOWER({column}) LIKE '% {kw_low}%'")
# #         conds.append(f"LOWER({column}) LIKE '{kw_low}%'")          # at start
# #         conds.append(f"LOWER({column}) LIKE '%{kw_low}'")          # at end
# #         conds.append(f"LOWER({column}) LIKE '% {kw_low}.'%")       # with dot
# #         conds.append(f"LOWER({column}) LIKE '% {kw_low},%'")       # with comma
# #     return "(" + " OR ".join(conds) + ")"
# #
# # petitioner_cond = build_like_conditions("petitioner")
# # respondent_cond = build_like_conditions("respondent")
# #
# # # 1️⃣ petitioner matched → AppearingFor = Petitioner
# # cursor.execute(f"""
# #     UPDATE cases_disposed
# #     SET AppearingFor='Petitioner',
# #         OpponentAs='Respondent'
# #     WHERE {petitioner_cond};
# # """)
# # conn.commit()
# #
# # # 2️⃣ respondent matched → AppearingFor = Respondent
# # cursor.execute(f"""
# #     UPDATE cases_disposed
# #     SET AppearingFor='Respondent',
# #         OpponentAs='Petitioner'
# #     WHERE {respondent_cond};
# # """)
# # conn.commit()
# #
# # # fetch and print matched rows
# # cursor.execute(f"""
# #     SELECT * FROM cases_disposed
# #     WHERE {petitioner_cond} OR {respondent_cond};
# # """)
# #
# # rows = cursor.fetchall()
# # for row in rows:
# #     print(row)
# #
# # cursor.close()
# # conn.close()
# #
# #
# #
# #
# #
# #
# #
# #
# #
# #
# #
# #
# #
# #
# # # import mysql.connector
# # # import re
# # #
# # # # Connect to MySQL
# # # conn = mysql.connector.connect(
# # #     host="localhost",
# # #     user="root",
# # #     password="sanjai",
# # #     database="ecourts_db"
# # # )
# # # cursor = conn.cursor()
# # #
# # # # ------------------------------------------------------------
# # # # CREATE TABLE IF NOT EXISTS
# # # # ------------------------------------------------------------
# # # cursor.execute("""
# # #     CREATE TABLE IF NOT EXISTS cases_disposed (
# # #         id INT AUTO_INCREMENT PRIMARY KEY,
# # #         state_name VARCHAR(255),
# # #         state_code INT,
# # #         district_name VARCHAR(255),
# # #         district_code INT,
# # #         complex_name VARCHAR(255),
# # #         complex_code INT,
# # #         act_type VARCHAR(255),
# # #         act_code INT,
# # #         sno INT,
# # #         case_no VARCHAR(100),
# # #         petitioner TEXT,
# # #         respondent TEXT,
# # #         full_case_no VARCHAR(255),
# # #         cnr_no VARCHAR(255),
# # #         case_status VARCHAR(50),
# # #         AppearingFor VARCHAR(100),
# # #         OpponentAs VARCHAR(100),
# # #         new_act_type VARCHAR(255),
# # #         UNIQUE KEY unique_case (act_code, full_case_no, cnr_no)
# # #     );
# # # """)
# # # conn.commit()
# # #
# # # # ------------------------------------------------------------
# # # # ENSURE REQUIRED COLUMNS EXIST
# # # # ------------------------------------------------------------
# # # for col in ["AppearingFor", "OpponentAs", "new_act_type"]:
# # #     cursor.execute(f"SHOW COLUMNS FROM cases_disposed LIKE '{col}';")
# # #     if cursor.fetchone() is None:
# # #         cursor.execute(f"ALTER TABLE cases_disposed ADD COLUMN {col} VARCHAR(255);")
# # #         conn.commit()
# # #
# # # true_state_patterns = [
# # #     r'^state'
# # #     # r'^state of maharashtra',
# # #     # r'^the state of maharashtra',
# # #     # r'^state of',
# # #     # r'^the state',
# # #     # r'^government of maharashtra',
# # #     # r'^govt of maharashtra',
# # #     # r'^maharashtra government'
# # # ]
# # #
# # # # CORPORATION / DEPARTMENT EXCLUSIONS
# # # exclusions = [
# # #     'seeds corporation',
# # #     'seed corporation',
# # #     'electricity board',
# # #     'transport corporation',
# # #     'marketing federation',
# # #     'state seeds',
# # #     'state seed',
# # #     'mahabeej',
# # #     'seeds ltd',
# # #     'fertilizer company',
# # #     'marketing union'
# # # ]
# # #
# # # exclude_pet = " AND ".join([f"LOWER(petitioner) NOT LIKE '%{e}%'" for e in exclusions])
# # # exclude_res = " AND ".join([f"LOWER(respondent) NOT LIKE '%{e}%'" for e in exclusions])
# # #
# # # # ------------------------------------------------------------
# # # # APPLY STATE START-WITH LOGIC
# # # # ------------------------------------------------------------
# # # for pattern in true_state_patterns:
# # #
# # #     # Petitioner is Government
# # #     cursor.execute(f"""
# # #         UPDATE cases_disposed
# # #         SET AppearingFor = 'Petitioner',
# # #             OpponentAs = 'Respondent'
# # #         WHERE LOWER(petitioner) REGEXP '{pattern}'
# # #         AND {exclude_pet};
# # #     """)
# # #
# # #     # Respondent is Government
# # #     cursor.execute(f"""
# # #         UPDATE cases_disposed
# # #         SET AppearingFor = 'Respondent',
# # #             OpponentAs = 'Petitioner'
# # #         WHERE LOWER(respondent) REGEXP '{pattern}'
# # #         AND {exclude_res};
# # #     """)
# # #
# # # conn.commit()
# # #
# # # # ------------------------------------------------------------
# # # # KEYWORD LIST (MATCH ONLY WHOLE WORD)
# # # # ------------------------------------------------------------
# # # keywords = [
# # #     'agri.', 'Agriculture', 'Inspector', 'State of', 'Government of', 'Gov.', 'Govt.',
# # #     'The state', 'maharashtra state', 'Maha State', 'of Maharashtra', 'StateofMaharashtra',
# # #     'State Maharashtra', 'State  of Maharashtra', 'STATE  OF MAHARASHTRA', 'The  State',
# # #     'Stateof Maharashtra', 'StateFertilizer', 'State.', 'State,', 'State through',
# # #     'State thr.', 'State thou', 'State Represented', 'Stat of Maharashtra', 'Stat of Mah'
# # # ]
# # #
# # # # Escape for REGEXP
# # # safe_keywords = [re.escape(k.lower()) for k in keywords]
# # #
# # # # ------------------------------------------------------------
# # # # MID-SENTENCE WHOLE-WORD MATCHING USING REGEXP WORD BOUNDARIES
# # # # ------------------------------------------------------------
# # # for kw in safe_keywords:
# # #
# # #     pattern = f"[[:<:]]{kw}[[:>:]]"
# # #
# # #     # Keyword appears in PETITIONER
# # #     cursor.execute(f"""
# # #         UPDATE cases_disposed
# # #         SET AppearingFor = 'Petitioner',
# # #             OpponentAs = 'Respondent'
# # #         WHERE LOWER(petitioner) REGEXP '{pattern}';
# # #     """)
# # #
# # #     # Keyword appears in RESPONDENT
# # #     cursor.execute(f"""
# # #         UPDATE cases_disposed
# # #         SET AppearingFor = 'Respondent',
# # #             OpponentAs = 'Petitioner'
# # #         WHERE LOWER(respondent) REGEXP '{pattern}';
# # #     """)
# # #
# # # conn.commit()
# # #
# # # # ------------------------------------------------------------
# # # # MAP ACT TYPES
# # # # ------------------------------------------------------------
# # # new_act_type = {
# # #     'Essential Commodities (Special Provisions) Act': 'Essential Commodities Act 1955',
# # #     'The Fertilizer (Control) Order Act': 'Fertilizer Control Order 1985',
# # #     'Seeds Act': 'Seed Act 1966',
# # #     'Maharashtra Cotton Seeds Regulation Act': 'Maharashtra Cotton Seed Act 2009',
# # #     'Insecticides Act': 'Insecticides Act 1968',
# # #     'Seeds Rules': 'Seed Rules 1968'
# # # }
# # #
# # # for old_act, new_act in new_act_type.items():
# # #     cursor.execute("""
# # #         UPDATE cases_disposed
# # #         SET new_act_type = %s
# # #         WHERE act_type = %s;
# # #     """, (new_act, old_act))
# # #
# # # conn.commit()
# # #
# # # # ------------------------------------------------------------
# # # # DEBUG OUTPUT (OPTIONAL)
# # # # ------------------------------------------------------------
# # # cursor.execute("""
# # #     SELECT id, petitioner, respondent, AppearingFor, OpponentAs
# # #     FROM cases_disposed
# # #     WHERE AppearingFor IS NOT NULL;
# # # """)
# # #
# # # for row in cursor.fetchall():
# # #     print(row)
# # #
# # # cursor.close()
# # # conn.close()
