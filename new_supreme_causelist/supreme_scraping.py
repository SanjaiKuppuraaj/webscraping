import sys
sys.path.insert(0, '/var/www/mml_python_code')
import re
import json
import sys
import os
from bs4 import BeautifulSoup as bs
from common_code import common_module as cm

folder_name = os.path.join(cm.BASE_DIR_OUTPUTS, "new_supreme_causelist", "output")

DATE_STR = "UNKNOWN_DATE"
pdf_link = ""
label_name = ""
output_filename = ""

if len(sys.argv) > 2:
    output_filename = sys.argv[2]
    match = re.search(r'(\d{2}-\d{2}-\d{4})', output_filename)
    if match:
        DATE_STR = match.group(1)
    else:
        print("Warning: No valid date found in filename. Using UNKNOWN_DATE.")

if len(sys.argv) > 3:
    pdf_link = sys.argv[3]

# === Dynamic label mapping logic ===
def get_readable_label(label_name):
    parts = label_name.strip().upper().split("_")

    if parts == ["JUDGE", "MISCELLANEOUS", "ADVANCE"]:
        return "MISCELLANEOUS ADVANCE"
    elif parts == ["JUDGE", "MISCELLANEOUS", "MAIN"]:
        return "MISCELLANEOUS HEARING"
    elif parts in (["JUDGE", "MISCELLANEOUS", "SUPPLEMENTARY"], ["JUDGE", "MISCELLANEOUS", "SUPPL"]):
        return "SUPPLEMENTARY LIST MISCELLANEOUS HEARING"
    elif parts == ["JUDGE", "REGULAR", "MAIN"]:
        return "REGULAR HEARING"
    elif parts in (["JUDGE", "REGULAR", "SUPPLEMENTARY"], ["JUDGE", "REGULAR", "SUPPL"]):
        return "SUPPLEMENTARY LIST REGULAR HEARING"
    elif len(parts) == 2:
        if parts[0] == "CHAMBER" and parts[1] == "MAIN":
            return "CHAMBER MATTERS"
        elif parts[0] == "CHAMBER" and parts[1] == "SUPPL":
            return "MISCELLANEOUS HEARING"
        elif parts[1] == "MAIN":
            return f"{parts[0]} MATTERS"
        elif parts[1] == "SUPPL":
            return "MISCELLANEOUS HEARING"
    elif "SUPPL" in parts or "SUPPLEMENTARY" in parts:
        return "SUPPLEMENTARY LIST MISCELLANEOUS HEARING"

    return label_name.replace("_", " ")

if len(sys.argv) > 4:
    raw_label = sys.argv[4]
    label_name = get_readable_label(raw_label)

if not output_filename:
    raise ValueError("output_filename is not set. Please check command-line arguments.")

html_path = os.path.join(folder_name, 'output.html')
with open(html_path, 'r', encoding='utf-8-sig') as f:
    html = f.read()

soup = bs(html, 'html.parser')
rows = soup.find_all("tr")

def clean(t):
    if not isinstance(t, str):
        return t
    return re.sub(r'\\n|\\r|\\t|\n|\r|\t', ' ', t).replace('  ', ' ').strip()

def deep_clean_dict(d):
    for k, v in d.items():
        if isinstance(v, str):
            d[k] = clean(v)
        elif isinstance(v, list):
            d[k] = [deep_clean_dict(item) if isinstance(item, dict) else clean(item) for item in v]
        elif isinstance(v, dict):
            d[k] = deep_clean_dict(v)
    return d

judge_pattern = r"(HON'BLE(?: THE CHIEF JUSTICE| (?:MR|MS|MRS)\. JUSTICE [A-Z. ]+)|(?:MR|MS|MRS|SH|DR|SMT)\. [A-Z. ]+, REGISTRAR)"
court_pattern = r"(COURT(?: HALL)?(?: NO\.?)*\s*:?[ ]*\d+)"

matter_types_raw = [
    '[DEFAULT / OTHER MATTERS]', '[SERVICE/COMPLIANCE]-BEFORE REGISTRAR(J)',
    '[TRANSFER PETITIONS]', '[BAIL MATTERS]', 'CHAMBER MATTERS',
    '[FRESH (FOR ADMISSION) - CIVIL CASES]', '[FRESH (FOR ADMISSION) - CRIMINAL CASES]',
    '[FRESHLY / ADJOURNED MATTERS]', 'PUBLIC INTEREST LITIGATIONS',
    '[AFTER NOTICE (FOR ADMISSION) - CIVIL CASES]', '[AFTER NOTICE (FOR ADMISSION) - CRIMINAL CASES]',
    '[DISPOSAL/FINAL DISPOSAL AT ADMISSION STAGE - CIVIL CASES]', '[ORDERS (INCOMPLETE MATTERS / IAs / CRLMPs)]',
    '[TOP OF THE LIST (FOR ADMISSION)]', 'AD INTERIM STAY MATTERS',
    "MISCELLANEOUS ADVANCE", "MISCELLANEOUS MAIN", "MISCELLANEOUS SUPPLEMENTARY",
    "REGULAR MAIN", "REGULAR SUPPLEMENTARY", "CHAMBER MAIN", "CHAMBER SUPPLEMENTARY",
    "SINGLE JUDGE MAIN", "SINGLE JUDGE SUPPLEMENTARY", "REVIEW & CURATIVE MAIN",
    "REVIEW & CURATIVE SUPPLEMENTARY", "REGISTRAR MAIN", "REGISTRAR SUPPLEMENTARY",
    "SUPPLEMENTARY LIST", "MISCELLANEOUS HEARING", "BAIL MATTERS",
    'Service Laws - Retiral benefits, pension', 'Criminal Law'
]
matter_types = [clean(mt).upper().replace('(', '').replace(')', '') for mt in matter_types_raw]

blocks = []
court_notes = []
current_note = ""
next_row_is_note = False
last_main_sno = ""

current_judge = ""
current_court = ""
current_matter_type = ""

temp_block = None
all_cases = {}
main_case_map = {}
connected_map = {}

for idx, row in enumerate(rows):
    text = clean(row.get_text(separator=' ', strip=True).replace('\ufeff', ''))
    upper_text = text.upper().replace('(', '').replace(')', '')

    if next_row_is_note:
        current_note = clean(row.get_text())
        if len(current_note) > 10:
            court_notes.append(current_note)
        next_row_is_note = False
        continue

    judge_match = re.search(judge_pattern, upper_text)
    if judge_match:
        current_judge = judge_match.group(0).strip()

    matter_type_found = None
    for mtype in matter_types:
        if mtype in upper_text:
            matter_type_found = mtype
            break
    if matter_type_found:
        current_matter_type = matter_type_found

    court_match = re.search(court_pattern, upper_text, re.IGNORECASE)
    if court_match:
        current_court = court_match.group(1).strip()

    if 'NOTE:-' in upper_text:
        next_row_is_note = True
        continue

    if court_match or matter_type_found or judge_match:
        if temp_block and temp_block['clist']:
            temp_block['court_hall_note'] = court_notes[:]
            blocks.append(temp_block)
            court_notes = []

        temp_block = {
            "Court_Number": [current_court or ""],
            "matter_type": [current_matter_type or label_name],
            "judge_name": [current_judge or ""],
            "clist": []
        }
        continue

    if not temp_block:
        temp_block = {
            "Court_Number": [""],
            "matter_type": [""],
            "judge_name": [""],
            "clist": []
        }

    cells = row.find_all("td")
    if len(cells) != 4:
        continue

    sno_raw = clean(cells[0].get_text()).replace('\n', '').replace(' ', '')
    if re.match(r'^\d+\.\d+$', sno_raw):
        sno = sno_raw
        last_main_sno = sno.split('.')[0]
    elif sno_raw.startswith('.'):
        sno = f"{last_main_sno}{sno_raw}"
    elif re.match(r'^\d+$', sno_raw):
        sno = sno_raw
        last_main_sno = sno
    else:
        continue

    case_no_text = clean(cells[1].get_text(separator=' '))
    case_string = case_no_text.replace('Connected', '').strip()
    match = re.search(r'([A-Z][A-Z0-9./() ]+)\s*(?:NO\.?|No\.?)\s*(\d+)[/-](\d{4})', case_string, re.IGNORECASE)
    if not match:
        continue

    case_type = clean(match.group(1))
    case_no = match.group(2)
    case_year = match.group(3)

    raw_html = str(cells[2])
    text = bs(raw_html, 'html.parser').get_text()
    pet = clean(text.split('Versus')[0])
    parts = raw_html.split('Versus')
    if len(parts) > 1:
        after_versus = parts[1]
        soup = bs(after_versus, 'html.parser')
        lines = [clean(line) for line in soup.get_text(separator='\n').split('\n') if line.strip()]
        respondent = lines[0] if lines else ''
        board_remark = ' '.join(lines[1:])
    else:
        respondent = ''
        board_remark = ''

    adv_soup = bs(str(cells[3]), 'html.parser')
    parts = [bs(p, "html.parser").get_text(strip=True) for p in adv_soup.decode_contents().split("<br/>") if p.strip()]
    pet_adv = parts[0] if parts else ''
    resp_adv = ", ".join(parts[1:]) if len(parts) > 1 else ''
    # advocates = [clean(line) for line in adv_soup.get_text(separator=' ').split('\n') if line.strip()]
    # pet_adv = advocates[0] if advocates else ''
    # resp_adv = advocates[-1] if len(advocates) > 1 else ''

    case_data = {
        "Board_Remark": board_remark,
        "brd_slno": sno,
        "case_type": case_type,
        "case_no": case_no,
        "case_year": case_year,
        "cases": f"{case_type} {case_no}/{case_year}",
        "petitioner_name": [pet],
        "respondent_name": [respondent],
        "petitioner_adv": [pet_adv],
        "respondent_adv": [resp_adv]
    }

    case_data = deep_clean_dict(case_data)
    all_cases[sno] = case_data

    if '.' in sno:
        base = sno.split('.')[0]
        connected_map.setdefault(base, []).append(sno)
    else:
        main_case_map[sno] = case_data
        temp_block['clist'].append(case_data)

if temp_block and temp_block['clist']:
    temp_block['court_hall_note'] = court_notes[:]
    blocks.append(temp_block)

for base, connected_snos in connected_map.items():
    parent = main_case_map.get(base)
    if not parent:
        print(f"[Warning] Missing parent case for connected entries: {base}")
        continue
    for c_sno in connected_snos:
        conn_case = all_cases.get(c_sno)
        if conn_case:
            parent.setdefault("connected_cases", []).append(conn_case)

output_data = {
    "pdf_link": pdf_link,
    "label": label_name,
    "result": blocks
}

os.makedirs(os.path.dirname(output_filename), exist_ok=True)
with open(output_filename, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, indent=4, ensure_ascii=False)


# import re
# import json
# import sys
# import os
# from bs4 import BeautifulSoup as bs
# from common_code import common_module as cm
#
# folder_name = os.path.join(cm.BASE_DIR_OUTPUTS, "new_supreme_causelist", "output")
#
# DATE_STR = "UNKNOWN_DATE"
# pdf_link = ""
# label_name = ""
# output_filename = ""
#
# if len(sys.argv) > 2:
#     output_filename = sys.argv[2]
#     match = re.search(r'(\d{2}-\d{2}-\d{4})', output_filename)
#     if match:
#         DATE_STR = match.group(1)
#     else:
#         print("Warning: No valid date found in filename. Using UNKNOWN_DATE.")
#
# if len(sys.argv) > 3:
#     pdf_link = sys.argv[3]
#
# if len(sys.argv) > 4:
#     label_name = sys.argv[4]
#
# if not output_filename:
#     raise ValueError("output_filename is not set. Please check command-line arguments.")
#
# html_path = os.path.join(folder_name, 'output.html')
# with open(html_path, 'r', encoding='utf-8-sig') as f:
#     html = f.read()
#
# soup = bs(html, 'html.parser')
# rows = soup.find_all("tr")
#
# def clean(t):
#     if not isinstance(t, str):
#         return t
#     return re.sub(r'\\n|\\r|\\t|\n|\r|\t', ' ', t).replace('  ', ' ').strip()
#
# def deep_clean_dict(d):
#     for k, v in d.items():
#         if isinstance(v, str):
#             d[k] = clean(v)
#         elif isinstance(v, list):
#             d[k] = [deep_clean_dict(item) if isinstance(item, dict) else clean(item) for item in v]
#         elif isinstance(v, dict):
#             d[k] = deep_clean_dict(v)
#     return d
#
# judge_pattern = r"(HON'BLE(?: THE CHIEF JUSTICE| (?:MR|MS|MRS)\. JUSTICE [A-Z. ]+)|(?:MR|MS|MRS|SH|DR|SMT)\. [A-Z. ]+, REGISTRAR)"
# court_pattern = r"(COURT(?: HALL)?(?: NO\.?)*\s*:?[ ]*\d+)"
#
# matter_types_raw = [
#     '[DEFAULT / OTHER MATTERS]', '[SERVICE/COMPLIANCE]-BEFORE REGISTRAR(J)',
#     '[TRANSFER PETITIONS]', '[BAIL MATTERS]', 'CHAMBER MATTERS',
#     '[FRESH (FOR ADMISSION) - CIVIL CASES]', '[FRESH (FOR ADMISSION) - CRIMINAL CASES]',
#     '[FRESHLY / ADJOURNED MATTERS]', 'PUBLIC INTEREST LITIGATIONS',
#     '[AFTER NOTICE (FOR ADMISSION) - CIVIL CASES]', '[AFTER NOTICE (FOR ADMISSION) - CRIMINAL CASES]',
#     '[DISPOSAL/FINAL DISPOSAL AT ADMISSION STAGE - CIVIL CASES]', '[ORDERS (INCOMPLETE MATTERS / IAs / CRLMPs)]',
#     '[TOP OF THE LIST (FOR ADMISSION)]', 'AD INTERIM STAY MATTERS',
#     "MISCELLANEOUS ADVANCE", "MISCELLANEOUS MAIN", "MISCELLANEOUS SUPPLEMENTARY",
#     "REGULAR MAIN", "REGULAR SUPPLEMENTARY", "CHAMBER MAIN", "CHAMBER SUPPLEMENTARY",
#     "SINGLE JUDGE MAIN", "SINGLE JUDGE SUPPLEMENTARY", "REVIEW & CURATIVE MAIN",
#     "REVIEW & CURATIVE SUPPLEMENTARY", "REGISTRAR MAIN", "REGISTRAR SUPPLEMENTARY",
#     "SUPPLEMENTARY LIST", "MISCELLANEOUS HEARING", "BAIL MATTERS",
#     'Service Laws - Retiral benefits, pension', 'Criminal Law'
# ]
# matter_types = [clean(mt).upper().replace('(', '').replace(')', '') for mt in matter_types_raw]
#
# blocks = []
# court_notes = []
# current_note = ""
# next_row_is_note = False
# last_main_sno = ""
#
# current_judge = ""
# current_court = ""
# current_matter_type = ""
#
# temp_block = None
# all_cases = {}
# main_case_map = {}
# connected_map = {}
#
# for idx, row in enumerate(rows):
#     text = clean(row.get_text(separator=' ', strip=True).replace('\ufeff', ''))
#     upper_text = text.upper().replace('(', '').replace(')', '')
#
#     if next_row_is_note:
#         current_note = clean(row.get_text())
#         if len(current_note) > 10:
#             court_notes.append(current_note)
#         next_row_is_note = False
#         continue
#
#     judge_match = re.search(judge_pattern, upper_text)
#     if judge_match:
#         current_judge = judge_match.group(0).strip()
#
#     matter_type_found = None
#     for mtype in matter_types:
#         if mtype in upper_text:
#             matter_type_found = mtype
#             break
#     if matter_type_found:
#         current_matter_type = matter_type_found
#
#     court_match = re.search(court_pattern, upper_text, re.IGNORECASE)
#     if court_match:
#         current_court = court_match.group(1).strip()
#
#     if 'NOTE:-' in upper_text:
#         next_row_is_note = True
#         continue
#
#     if court_match or matter_type_found or judge_match:
#         if temp_block and temp_block['clist']:
#             temp_block['court_hall_note'] = court_notes[:]
#             blocks.append(temp_block)
#             court_notes = []
#
#         temp_block = {
#             "Court_Number": [current_court or ""],
#             # "Date": DATE_STR,
#             "matter_type": current_matter_type or "MISCELLANEOUS ADVANCE",
#             "judge_name": [current_judge or ""],
#             "clist": []
#         }
#         continue
#
#     if not temp_block:
#         temp_block = {
#             "Court_Number": [""],
#             # "Date": DATE_STR,
#             "matter_type": "MISCELLANEOUS ADVANCE",
#             "judge_name": [""],
#             "clist": []
#         }
#
#     cells = row.find_all("td")
#     if len(cells) != 4:
#         continue
#
#     sno_raw = clean(cells[0].get_text()).replace('\n', '').replace(' ', '')
#     if re.match(r'^\d+\.\d+$', sno_raw):
#         sno = sno_raw
#         last_main_sno = sno.split('.')[0]
#     elif sno_raw.startswith('.'):
#         sno = f"{last_main_sno}{sno_raw}"
#     elif re.match(r'^\d+$', sno_raw):
#         sno = sno_raw
#         last_main_sno = sno
#     else:
#         continue
#
#     case_no_text = clean(cells[1].get_text(separator=' '))
#     case_string = case_no_text.replace('Connected', '').strip()
#
#     # match = re.search(r'([A-Z./() ]+)\s*(?:NO\.?|No\.?)?\s*(\d+)[/|-](\d{4})', case_string, re.IGNORECASE)
#     match = re.search(r'([A-Z][A-Z0-9./() ]+)\s*(?:NO\.?|No\.?)\s*(\d+)[/-](\d{4})', case_string, re.IGNORECASE)
#
#     if not match:
#         continue
#
#     case_type = clean(match.group(1))
#     case_no = match.group(2)
#     case_year = match.group(3)
#
#     raw_html = str(cells[2])
#     text = bs(raw_html, 'html.parser').get_text()
#     pet = clean(text.split('Versus')[0])
#     parts = raw_html.split('Versus')
#     if len(parts) > 1:
#         after_versus = parts[1]
#         soup = bs(after_versus, 'html.parser')
#         lines = [clean(line) for line in soup.get_text(separator='\n').split('\n') if line.strip()]
#         respondent = lines[0] if lines else ''
#         board_remark = ' '.join(lines[1:])
#     else:
#         respondent = ''
#         board_remark = ''
#
#     adv_soup = bs(str(cells[3]), 'html.parser')
#     advocates = [clean(line) for line in adv_soup.get_text(separator=' ').split('\n') if line.strip()]
#     pet_adv = advocates[0] if advocates else ''
#     resp_adv = advocates[-1] if len(advocates) > 1 else ''
#
#     case_data = {
#         "Board_Remark": board_remark,
#         "brd_slno": sno,
#         "case_type": case_type,
#         "case_no": case_no,
#         "case_year": case_year,
#         "cases": f"{case_type} {case_no}/{case_year}",
#         "petitioner_name": [pet],
#         "respondent_name": [respondent],
#         "petitioner_adv": [pet_adv],
#         "respondent_adv": [resp_adv]
#     }
#
#     case_data = deep_clean_dict(case_data)
#     all_cases[sno] = case_data
#
#     if '.' in sno:
#         base = sno.split('.')[0]
#         connected_map.setdefault(base, []).append(sno)
#     else:
#         main_case_map[sno] = case_data
#         temp_block['clist'].append(case_data)
#
# if temp_block and temp_block['clist']:
#     temp_block['court_hall_note'] = court_notes[:]
#     blocks.append(temp_block)
#
# for base, connected_snos in connected_map.items():
#     parent = main_case_map.get(base)
#     if not parent:
#         print(f"[Warning] Missing parent case for connected entries: {base}")
#         continue
#
#     for c_sno in connected_snos:
#         conn_case = all_cases.get(c_sno)
#         if conn_case:
#             parent.setdefault("connected_cases", []).append(conn_case)
#
# output_data = {
#     "pdf_link": pdf_link,
#     "label": label_name,
#     # "date": DATE_STR,
#     "result": blocks
# }
#
# os.makedirs(os.path.dirname(output_filename), exist_ok=True)
# with open(output_filename, 'w', encoding='utf-8') as f:
#     json.dump(output_data, f, indent=4, ensure_ascii=False)
