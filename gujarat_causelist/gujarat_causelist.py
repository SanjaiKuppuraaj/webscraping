import sys
sys.path.insert(0, '/var/www/mml_python_code')
from flask import Blueprint, jsonify, request
import os
import re
import multiprocessing
import requests
import pdfplumber
from bs4 import BeautifulSoup as bs
import glob
import json
import logging
from datetime import datetime
from common_code import common_module as cm

gujarat_bp = Blueprint("gujarat", __name__)

BASE_DIR = "/var/www/mml_python_code/gujarat_causelist"
PDF_FOLDER = os.path.join(BASE_DIR, "cause_list")
HTML_FOLDER = os.path.join(BASE_DIR, "html_outputs")
json_folder = cm.BASE_DIR_OUTPUTS + "/gujarat_causelist"
JSON_FOLDER = os.path.join(json_folder)
LOG_DIR = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime("%Y-%m-%d"))
LOG_FILE = os.path.join(LOG_DIR, "gujarat_log.txt")

os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(HTML_FOLDER, exist_ok=True)
os.makedirs(JSON_FOLDER, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.getLogger("pdfminer").setLevel(logging.ERROR)

CASE_NO_REGEX = re.compile(r"\b[A-Z]+(?:/[A-Z0-9]+)+/\d+\b")
DATE_REGEX = re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|([A-Z][a-z]+ \d{1,2}, \d{4})")
COURT_NO_REGEX = re.compile(r"COURT\s*(?:NO)?\s*[:\-]?\s*(\d+)", re.I)

def write_log(date_pdf, update_flag, status, total_cases=0):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = (
        f"[{ts}] date={date_pdf} | update={'true' if update_flag else 'false'} | "
        f"status={status} | total_cases={total_cases}\n"
    )
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def clean(text_lines):
    return " ".join(" ".join(text_lines).split())

def parse_case_no(cn):
    parts = cn.split("/")
    if len(parts) < 3:
        return {"case_mode": "", "case_type": "", "case_number": "", "case_year": ""}
    if parts[0] in {"R", "F"}:
        return {
            "case_mode": parts[0],
            "case_type": parts[1],
            "case_number": parts[2],
            "case_year": parts[3] if len(parts) > 3 else "",
        }
    else:
        return {
            "case_mode": "",
            "case_type": parts[0],
            "case_number": parts[1],
            "case_year": parts[2] if len(parts) > 2 else "",
        }

def download_pdf(listing_date):
    for f in glob.glob(f"{PDF_FOLDER}/*.pdf"):
        os.remove(f)
    for f in glob.glob(f"{HTML_FOLDER}/*.html"):
        os.remove(f)

    url = "https://gujarathc-casestatus.nic.in/gujarathc/printBoardNew"
    payload = {
        "coram": "",
        "coramOrder": "",
        "sidecode": "",
        "listflag": "5",
        "courtcode": "0",
        "courtroom": "undefined-undefined-undefined",
        "listingdate": listing_date,
        "advocatecodeval": "",
        "advocatenameval": "",
        "ccinval": "",
        "download_token": "",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0"}

    pdf_path = os.path.join(PDF_FOLDER, "cause_list.pdf")
    res = requests.post(url, data=payload, headers=headers, stream=True)
    if res.status_code == 200:
        with open(pdf_path, "wb") as f:
            for chunk in res.iter_content(8192):
                if chunk:
                    f.write(chunk)
        return pdf_path
    else:
        raise Exception(f"Failed to download PDF, status {res.status_code}")

def extract_pdf_to_html(pdf_path):
    output_files = []
    tagging_keywords = [
        "FOR ADMISSION",
        "FRESH MATTERS",
        "NOTICE & ADJOURNED MATTERS",
        "FOR HEARING",
        "CRITICALLY OLD MATTERS",
        "MR MANAN A SHAH On",
        "MATTERS WHERE",
        "FOR ADMISSION Old Matters - 5 to 10 years",
        "NOTICE & ADJOURNED MATTERS Old Matters - 5 to 10 years",
    ]
    board_mark_keywords = [
        "ARISING FROM",
        "CR-I/",
        "F/CR.MA",
        "R/CR.A/",
        "TITLE-",
        "STATUS-",
        "POLICE STATION",
    ]

    def is_new_entry(row):
        return row[0] and re.match(r"^\d+\s*$", row[0].strip())

    def is_tagging_row(row):
        return any(any(kw in (cell or "").upper() for kw in tagging_keywords) for cell in row)

    def is_board_mark_row(row):
        text = " ".join(cell or "" for cell in row).upper()
        return any(keyword in text for keyword in board_mark_keywords)

    with pdfplumber.open(pdf_path) as pdf:
        num_pages = len(pdf.pages)

    for page_num in range(num_pages):
        output_html_path = os.path.join(HTML_FOLDER, f"cause_list_page{page_num+1}.html")
        output_files.append(output_html_path)

        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_num]
            tables = page.extract_tables()

        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(
                """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>PDF Tables</title>
<style>
body{font-family:Arial,sans-serif;margin:20px;}
table{width:100%;border-collapse:collapse;margin-bottom:30px;border:2px solid #000;}
th,td{border:1px solid #000;padding:10px;text-align:left;vertical-align:top;}
th{background-color:#f2f2f2;}
tr.or{background-color:#e6f7ff;font-weight:bold;}
tr.tagging{background-color:#fff8e1;font-style:italic;}
h3{margin-top:40px;}
</style></head><body>"""
            )

            for table_index, table in enumerate(tables, start=1):
                f.write(f"<h3>Page {page_num+1} - Table {table_index}</h3>\n<table>\n")
                grouped_rows = []
                current_row = [""] * len(table[0])

                for row in table:
                    if is_tagging_row(row) and not is_new_entry(row):
                        if any(current_row):
                            grouped_rows.append(current_row)
                            current_row = [""] * len(table[0])
                        text = "<br>".join(cell.strip() for cell in row if cell and cell.strip())
                        grouped_rows.append(["__TAGGING__"] + [text] + [""] * (len(table[0]) - 2))
                    elif is_new_entry(row):
                        if any(current_row):
                            grouped_rows.append(current_row)
                        current_row = [cell or "" for cell in row]
                    elif is_board_mark_row(row):
                        if any(current_row):
                            grouped_rows.append(current_row)
                            current_row = [""] * len(table[0])
                        text = "<br>".join(cell.strip() for cell in row if cell and cell.strip())
                        grouped_rows.append(["__BOARD_MARKS__"] + [text] + [""] * (len(table[0]) - 2))
                    else:
                        for i in range(len(current_row)):
                            if i < len(row) and row[i]:
                                current_row[i] = "<br>".join(filter(None, [current_row[i], row[i]]))

                if any(current_row):
                    grouped_rows.append(current_row)

                i = 0
                while i < len(grouped_rows):
                    row = grouped_rows[i]
                    if row[0] == "__TAGGING__":
                        f.write(f"<tr class='tagging'><td colspan='{len(row)}'>{row[1]}</td></tr>\n")
                        i += 1
                        continue
                    if row[0] == "__BOARD_MARKS__":
                        i += 1
                        continue
                    is_or_row = re.match(r"^\d+(\s*<br>.*)?$", row[0].strip())
                    board_notes = []
                    j = i + 1
                    while j < len(grouped_rows) and grouped_rows[j][0] == "__BOARD_MARKS__":
                        board_notes.append(grouped_rows[j][1])
                        j += 1
                    row_class = ' class="or"' if is_or_row else ""
                    f.write(f"<tr{row_class}>\n")
                    for idx, cell in enumerate(row):
                        if idx == len(row) - 1 and board_notes:
                            board_text = "<br><br><span style='font-size:90%;font-style:italic;color:#555;'>"
                            board_text += "<br>".join(board_notes)
                            board_text += "</span>"
                            f.write(f"<td>{cell}{board_text}</td>\n")
                        else:
                            f.write(f"<td>{cell}</td>\n")
                    f.write("</tr>\n")
                    i = j

                f.write("</table>\n")

            f.write("</body></html>")

    return output_files

def parse_html_to_json(html_files, listing_date):
    all_grouped = []
    for html_path in html_files:
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        soup = bs(html, "html.parser")
        text_content = soup.get_text(separator="\n").split("\n")
        date_match = next((m.group(0) for line in text_content for m in [DATE_REGEX.search(line)] if m), listing_date)

        active_court_no = "NA"
        active_judges = ["NA"]
        grouped_by_matter_type = {}
        current_matter_type = "Unknown"

        rows = soup.find_all("tr")
        for row in rows:
            row_text = row.get_text(separator="\n").strip()
            court_match = COURT_NO_REGEX.search(row_text)
            if court_match:
                active_court_no = court_match.group(1)

            judge_lines = [
                re.sub(r"\s+", " ", l.strip())
                for l in row_text.splitlines()
                if "HONOURABLE" in l.upper() or "HON'BLE" in l.upper()
            ]
            if judge_lines:
                active_judges = judge_lines[:4]

            row_class = row.get("class", [])
            if "tagging" in row_class:
                tagging_text = re.sub(r"\s+", " ", row.get_text(separator="\n").strip())
                tagging_text = re.sub(r"^MATTER TYPE\s*[:\-]?\s*", "", tagging_text, flags=re.I)
                current_matter_type = tagging_text.strip()
                if current_matter_type not in grouped_by_matter_type:
                    grouped_by_matter_type[current_matter_type] = {
                        "clist": [],
                        "court_no": active_court_no,
                        "judge_names": active_judges if active_judges else ["NA"],
                    }
                continue
            if "or" not in row_class:
                continue

            tds = row.find_all("td")
            if len(tds) < 5:
                continue
            sno_text = tds[0].get_text(strip=True)
            match = re.match(r"^(\d+(\.\d+)?)", sno_text)
            if not match:
                continue
            sno_value = match.group(1)
            case_text = tds[1].get_text(separator="\n").strip()
            case_lines = [line.strip() for line in case_text.split("\n") if line.strip()]
            case_nos = [line for line in case_lines if CASE_NO_REGEX.search(line)]
            case_set = set(case_nos)
            courts = [line for line in case_lines if line not in case_set]
            if not case_nos:
                continue

            lines = [line.strip() for line in tds[2].get_text(separator="\n").split("\n") if line.strip()]
            petitioner_lines, respondent_lines, current, found_vs = [], [], [], False
            for line in lines:
                if re.fullmatch(r"V/?S", line, re.IGNORECASE):
                    petitioner_lines = current
                    current = []
                    found_vs = True
                else:
                    current.append(line)
            if found_vs:
                respondent_lines = current
            else:
                continue

            petitioner, respondent = clean(petitioner_lines), clean(respondent_lines)
            if not petitioner or not respondent:
                continue

            main_case = parse_case_no(case_nos[0])
            sol = {
                "brd_slno": sno_value,
                "case_no": case_nos[0],
                "case_mode": main_case["case_mode"],
                "case_type": main_case["case_type"],
                "case_number": main_case["case_number"],
                "case_year": main_case["case_year"],
                "court_name": courts[0] if courts else "",
                "petitioner": [petitioner],
                "respondent": [respondent],
                "pet_advocate": tds[3].get_text(strip=True),
                "resp_advocate": tds[4].get_text(strip=True),
                "connected_cases": [],
            }

            for cidx in range(1, len(case_nos)):
                parsed = parse_case_no(case_nos[cidx])
                sub_case = {
                    "brd_slno": f"{sno_value}.{cidx}",
                    "case_no": case_nos[cidx],
                    "case_mode": parsed["case_mode"],
                    "case_type": parsed["case_type"],
                    "case_number": parsed["case_number"],
                    "case_year": parsed["case_year"],
                    "court_name": courts[cidx] if cidx < len(courts) else sol["court_name"],
                    "petitioner": [petitioner],
                    "respondent": [respondent],
                    "pet_advocate": tds[3].get_text(strip=True),
                    "resp_advocate": tds[4].get_text(strip=True),
                }
                sol["connected_cases"].append(sub_case)

            if current_matter_type not in grouped_by_matter_type:
                grouped_by_matter_type[current_matter_type] = {
                    "clist": [],
                    "court_no": active_court_no,
                    "judge_names": active_judges if active_judges else ["NA"],
                }
            grouped_by_matter_type[current_matter_type]["clist"].append(sol)

        for matter_type, info in grouped_by_matter_type.items():
            court_no = info.get("court_no", "NA") or "NA"
            judge_lines_list = info.get("judge_names", [])[:4] if info.get("judge_names") else ["NA"]
            all_grouped.append(
                {
                    "matter_type": matter_type,
                    "court_no": court_no,
                    "date": date_match or "NA",
                    "judge_names": judge_lines_list,
                    "clist": info["clist"],
                }
            )

    return all_grouped

def process_causelist(date_pdf):
    try:
        pdf_path = download_pdf(date_pdf)
        html_files = extract_pdf_to_html(pdf_path)
        result_json = parse_html_to_json(html_files, date_pdf)

        json_path = os.path.join(JSON_FOLDER, date_pdf.replace("/", "-") + ".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result_json, f, indent=4, ensure_ascii=False)

        total_cases = 0
        for m in result_json:
            for case in m.get("clist", []):
                total_cases += 1
                total_cases += len(case.get("connected_cases", []))
        write_log(date_pdf, True, "completed", total_cases)
        print(f"[Background] Completed processing for {date_pdf} with {total_cases} cases")

        return result_json, total_cases

    except Exception as e:
        write_log(date_pdf, True, f"error: {e}", 0)
        print(f"[Background] Error for {date_pdf}: {e}")
        return None, 0

@gujarat_bp.route("", methods=["GET"])
def gujarat_causelist():
    date_input = request.args.get("date", None)
    update_flag = request.args.get("update", "false").lower() == "true"
    # update_flag = request.args.get("update", "false")
    if not date_input:
        return jsonify({"message": "date param required"}), 400
    date_pdf = date_input.replace("-", "/")
    json_file = os.path.join(JSON_FOLDER, date_input + ".json")
    if update_flag:
        proc = multiprocessing.Process(target=process_causelist, args=(date_pdf,))
        proc.start()
        write_log(date_pdf, True, "started", 0)
        return jsonify({"message": "Processing started in background, check again later"}), 202
    else:
        if os.path.exists(json_file):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            total_cases = 0
            for m in data:
                for case in m.get("clist", []):
                    total_cases += 1
                    total_cases += len(case.get("connected_cases", []))

            write_log(date_pdf, False, "success", total_cases)
            return jsonify({"total_cases": total_cases, "result": data})

        else:
            write_log(date_pdf, False, "not found", 0)
            return jsonify({"message": "no record found"}), 404


