from flask import Blueprint, request, jsonify
import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime
import urllib3
import logging
import json
import os
from common_code import common_module as cm

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

case_status_bp = Blueprint("case_status", __name__)

logging.basicConfig(level=logging.INFO, format="%(message)s")


def log_status(zone_type, case_type, case_number, case_year, status):
    log_dir = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'Ngt_casestatus.txt')
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{now} | {zone_type}/{case_type}/{case_number}/{case_year} | status: {status}"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")
    logging.info(log_entry)


def convert_date(date_str: str):
    try:
        dt = datetime.strptime(date_str, "%d-%m-%Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


def clean_list(lst):
    return [x.strip().lstrip("<td>").rstrip("</td>").strip()
            for x in lst
            if x.strip() and not (x.strip().startswith("<") and x.strip().endswith(">"))]


@case_status_bp.route("", methods=["GET"])
def case_status():
    zone_type = request.args.get("zone_type", "")
    case_type = request.args.get("case_type", "")
    case_number = request.args.get("case_number", "")
    case_year = request.args.get("case_year", "")

    if not case_number or not case_year:
        log_status(zone_type, case_type, case_number, case_year, "Error")
        return jsonify({"result": "error", "message": "case_number and case_year are required"}), 400

    url = f"https://www.greentribunal.gov.in/casestatus/caseNumberData?zone_type={zone_type}&case_type={case_type}&case_number={case_number}&case_year={case_year}"

    try:
        response = requests.get(url, verify=False, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        log_status(zone_type, case_type, case_number, case_year, "Error")
        return jsonify({"result": "not found", "message": f"error fetching main url: {str(e)}"}), 500

    soup = bs(response.text, "html.parser")
    response_data = soup.find("table", {"class": "table-bordered customtable"})
    if not response_data:
        log_status(zone_type, case_type, case_number, case_year, "Error")
        return jsonify({"result": "Record not found", "message": "No data available"}), 404

    response_data = response_data.find("tbody").find_all("tr")
    results = []

    for data in response_data:
        sol = {}
        a_tag = data.find("a")
        if not a_tag or not a_tag.get("href"):
            continue
        bench = a_tag.text.strip()
        main_links = a_tag["href"]
        if "archived.greentribunal.gov.in" in main_links:
            continue

        try:
            detail_res = requests.get(main_links, verify=False, timeout=10)
            detail_res.raise_for_status()
        except requests.exceptions.RequestException:
            continue

        detail_soup = bs(detail_res.text, "html.parser")
        detail_div = detail_soup.find("div", {"class": "col-12 col-sm-9 col-md-9 ordersm1"})
        if not detail_div:
            continue

        sol["bench"] = bench or ""

        def safe_extract(label, split=False):
            try:
                value = [k.find_next("td").text.strip() for k in detail_div.find_all("td") if label in str(k)][0].strip()
                return value.split("/")[0] if split else value
            except:
                return ""

        sol["cin"] = safe_extract("Filing Number", split=True)
        sol["case_filed_date"] = convert_date(safe_extract("Registered On"))
        sol["petitioner_adv"] = safe_extract("Petitioner Advocate(s)")
        sol["respondent_adv"] = safe_extract("Respondent Advocate(s)")
        sol["act"] = safe_extract("Act")

        # Case title and parties
        try:
            party_name = [k.find_next("td").text.strip() for k in detail_div.find_all("td") if "Party Name" in str(k)][0]
            sol['case_title'] = party_name
            pet_val = party_name.split('VS')
            sol['petitioner'] = pet_val[0].strip() if len(pet_val) > 1 else pet_val[0].strip()
            sol['respondent'] = pet_val[1].strip() if len(pet_val) > 1 else ""
        except:
            sol['case_title'] = sol['petitioner'] = sol['respondent'] = ""

        # Case numbers
        try:
            case_no = [k.find_next("td").text.strip() for k in detail_div.find_all("td") if "Case Number" in str(k)][0].strip().split(". ")
            sol["case_type"] = case_no[0] if case_no else ""
            sol["case_no"] = case_no[1].split("/")[0]
            sol["case_year"] = case_no[1].split("/")[1]
        except:
            sol["case_type"], sol["case_no"], sol["case_year"] = "", "", ""

        sol["case_last_action_date"] = convert_date(safe_extract("Last Listed"))
        sol["next_hearing_date"] = convert_date(safe_extract("Next Hearing Date"))
        sol["case_status"] = safe_extract("Case Status")

        # Judgement/Orders
        sol["judgement"] = []
        try:
            list_response = [k.find_next("table").find("tbody") for k in detail_div.find_all("a") if "Listing History (Orders)" in str(k)][0]
            for lists in list_response.find_all("tr"):
                list_data = {}
                sno_tag = lists.find("td")
                sno_text = sno_tag.text.strip() if sno_tag else ""
                if sno_text and sno_text != "No data found!":
                    list_data["sno"] = sno_text
                    date_of_listing = sno_tag.find_next("td") if sno_tag else None
                    list_data["date"] = convert_date(date_of_listing.text) if date_of_listing else ""
                    date_of_upload = date_of_listing.find_next("td") if date_of_listing else None
                    list_data["date_of_upload"] = convert_date(date_of_upload.text) if date_of_upload else ""
                    coram = date_of_upload.find_next("td") if date_of_upload else None
                    # list_data["judgement"] = clean_list(str(coram).split("<br/>")) if coram else []
                    list_data["judgement"] = 'Order'
                    try:
                        pdf_link = lists.find_all("a")[-1]["onclick"]
                        list_data["link"] = "https://www.greentribunal.gov.in/gen_pdf_test.php?filepath=" + str(pdf_link).split("('")[-1].split("')")[0]
                    except:
                        list_data["pdf_link"] = ""
                    sol["judgement"].append(list_data)
        except:
            sol["judgement"] = []

        # All parties
        try:
            pedt_datas = [k.find_next("table").find("tbody") for k in detail_div.find_all("a") if "All Parties" in str(k)][0]
            petit_data = pedt_datas.find('td')
            sol['all_petitioner'] = clean_list(str(petit_data).split('<br/>'))
            sol['all_respondent'] = clean_list(str(petit_data.find_next('td')).split('<br/>'))
        except:
            sol['all_petitioner'], sol['all_respondent'] = [], []

        results.append(sol)

    if not results:
        log_status(zone_type, case_type, case_number, case_year, "Error")
        return jsonify({"result": "Record not found", "message": "No valid records"}), 404

    out_dir = os.path.join(cm.BASE_DIR_OUTPUTS, "Ngt_casestatus")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"{zone_type}_{case_type}_{case_number}_{case_year}.json")

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"result": results}, f, ensure_ascii=False, indent=4)

    log_status(zone_type, case_type, case_number, case_year, "Completed")
    return jsonify({'result': results})