from flask import Flask, request, jsonify,Blueprint
from bs4 import BeautifulSoup as bs
from PIL import Image
import pytesseract
import requests
import cv2
import numpy as np
import urllib3
import json
import os
from datetime import datetime
from common_code import common_module as cm
from common_code import proxy_implement

app = Flask(__name__)
ngt_case_bp = Blueprint("ngt_case_bp", __name__)
proxy_mode = proxy_implement.get_requests_proxy()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

output_folder = cm.BASE_DIR_OUTPUTS + '/ngt_casestatus'
DATA_FOLDER = output_folder
os.makedirs(DATA_FOLDER, exist_ok=True)

def convert_date(date_str: str):
    try:
        dt = datetime.strptime(date_str, "%d-%m-%Y")
        return dt.strftime("%Y-%m-%d")
    except:
        return ""

def clean_list(lst):
    return [x.strip().lstrip("<td>").rstrip("</td>").strip()
            for x in lst if x.strip() and not (x.strip().startswith("<") and x.strip().endswith(">"))]

class CaseStatusScraper:
    def __init__(self):
        self.session = requests.Session()
        if proxy_mode:
            self.session.proxies.update(proxy_mode)
        self.base_url = "https://www.greentribunal.gov.in"
        self.max_retries = 5

    def get_captcha(self, soup):
        captcha_url = self.base_url + soup.find("img", {"id": "captcha_image"})["src"]
        response = self.session.get(captcha_url, verify=False)
        response.raise_for_status()
        image = np.asarray(bytearray(response.content), dtype="uint8")
        image = cv2.imdecode(image, cv2.IMREAD_GRAYSCALE)
        _, image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        return Image.fromarray(image)

    def solve_captcha(self, image):
        config = r"--psm 7 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz1234567890"
        text = pytesseract.image_to_string(image, lang="eng", config=config)
        return text.strip().replace(" ", "").replace("\n", "")[:6]

    def fetch_case_status(self, case_number, case_year, captcha_text, zone_type, case_type):
        url = (f"{self.base_url}/casestatus/caseNumberData?"
               f"zone_type={zone_type}&case_type={case_type}"
               f"&case_number={case_number}&case_year={case_year}&captcha_input={captcha_text}")
        headers = {
            "user-agent": "Mozilla/5.0",
            "referer": f"{self.base_url}/casestatus/casenumber",
        }
        response = self.session.get(url, verify=False, headers=headers)
        return bs(response.text, "html.parser")

    def scrape(self, zone_type, case_type, case_number, case_year):
        response = self.session.get(f"{self.base_url}/casestatus/casenumber", verify=False)
        soup = bs(response.text, "html.parser")
        retries = 0

        while retries < self.max_retries:
            captcha_image = self.get_captcha(soup)
            captcha_text = self.solve_captcha(captcha_image)
            main_soup = self.fetch_case_status(case_number, case_year, captcha_text, zone_type, case_type)

            table = main_soup.find("table", {"class": "table-bordered customtable"})
            if not table:
                retries += 1
                soup = bs(self.session.get(f"{self.base_url}/casestatus/casenumber", verify=False).text, "html.parser")
                continue

            table_body = table.find("tbody")
            bench_links = [k.find("a") for k in table_body.find_all("td") if k][1:]

            if not bench_links or not bench_links[0]:
                retries += 1
                soup = bs(self.session.get(f"{self.base_url}/casestatus/casenumber", verify=False).text, "html.parser")
                continue

            a_tag = bench_links[0]
            bench = a_tag.text.strip()
            main_link = a_tag.get("href", "")

            # Skip archived links
            if main_link and "archived.greentribunal.gov.in" in main_link:
                retries += 1
                soup = bs(self.session.get(f"{self.base_url}/casestatus/casenumber", verify=False).text, "html.parser")
                continue

            # Fetch main case page
            try:
                response = self.session.get(main_link, verify=False, timeout=10)
                response.raise_for_status()
            except requests.RequestException:
                retries += 1
                soup = bs(self.session.get(f"{self.base_url}/casestatus/casenumber", verify=False).text, "html.parser")
                continue

            response_div = bs(response.text, "html.parser").find("div", {"class": "col-12 col-sm-9 col-md-9 ordersm1"})
            sol = {"bench": bench}

            def get_text_by_label(label):
                try:
                    return [k.find_next("td").text.strip() for k in response_div.find_all("td") if label in str(k)][0]
                except:
                    return ""

            sol["cin"] = get_text_by_label("Filing Number").split("/")[0] if get_text_by_label("Filing Number") else ""
            sol["case_title"] = get_text_by_label("Party Name")

            try:
                pet_val = get_text_by_label("Party Name").split("VS")
                sol["petitioner"] = [pet_val[0].strip()]
                sol["respondent"] = [pet_val[1].strip()]
            except:
                sol["petitioner"], sol["respondent"] = "", ""

            sol["case_filed_date"] = convert_date(get_text_by_label("Filing Date"))
            sol["petitioner_adv"] = get_text_by_label("Petitioner Advocate(s)")
            sol["respondent_adv"] = get_text_by_label("Respondent Advocate(s)")
            sol["act"] = get_text_by_label("Act")

            try:
                case_no = get_text_by_label("Case Number").split(". ")
                sol["case_type"] = case_no[0] if case_no else ""
                sol["case_no"] = case_no[1].split("/")[0]
                sol["case_year"] = case_no[1].split("/")[1]
            except:
                sol["case_type"], sol["case_no"], sol["case_year"] = "", "", ""

            sol["case_last_action_date"] = convert_date(get_text_by_label("Last Listed"))
            sol["next_hearing_date"] = convert_date(get_text_by_label("Next Hearing Date"))
            sol["case_status"] = get_text_by_label("Case Status")

            # Judgement History
            orders = []
            try:
                list_response = [
                    k.find_next("table").find("tbody")
                    for k in response_div.find_all("a")
                    if "Listing History (Orders)" in str(k)
                ][0]
                for row in list_response.find_all("tr"):
                    sno_td = row.find("td")
                    if not sno_td or not sno_td.text.strip().isdigit():
                        continue
                    list_data = {
                        "sno": sno_td.text.strip(),
                        "date": convert_date(sno_td.find_next("td").text) if sno_td.find_next("td") else "",
                        "date_of_upload": convert_date(sno_td.find_next("td").find_next("td").text) if sno_td.find_next("td") and sno_td.find_next("td").find_next("td") else "",
                        "coram": clean_list(str(sno_td.find_next("td").find_next("td").find_next("td")).split("<br/>")) if sno_td.find_next("td") and sno_td.find_next("td").find_next("td").find_next("td") else [],
                        "judgement": 'Order'
                    }
                    try:
                        pdf_link = row.find_all("a")[-1]["onclick"]
                        list_data["link"] = "https://www.greentribunal.gov.in/gen_pdf_test.php?filepath=" + str(pdf_link).split("('")[-1].split("')")[0]
                    except:
                        list_data["link"] = ""
                    orders.append(list_data)
            except:
                pass
            sol["judgement"] = orders

            # Parties
            try:
                parties_table = [
                    k.find_next("table").find("tbody")
                    for k in response_div.find_all("a")
                    if "All Parties" in str(k)
                ][0]
                petit_data = parties_table.find("td")
                sol["all_petitioner"] = clean_list(str(petit_data).split("<br/>"))
                sol["all_respondent"] = clean_list(str(petit_data.find_next("td")).split("<br/>"))
            except:
                sol["all_petitioner"], sol["all_respondent"] = [], []

            return sol

        return {"result": "error", "message": "Maximum retries exceeded. Unable to fetch case status."}

@ngt_case_bp.route("/ngt_status", methods=["GET"])
# @app.route('/ngt_status', methods=['GET'])
def case_status():
    try:
        zone_type = request.args.get("zone_type", type=int, default=1)
        case_type = request.args.get("case_type", type=int, default=1)
        case_number = request.args.get("case_number", type=int)
        case_year = request.args.get("case_year", type=int)

        if not case_number or not case_year:
            return jsonify({"error": "case_number and case_year are required"}), 400

        scraper = CaseStatusScraper()
        result = scraper.scrape(zone_type, case_type, case_number, case_year)
        filename = f"{zone_type}_{case_type}_{case_number}_{case_year}.json"
        filepath = os.path.join(DATA_FOLDER, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)

        return jsonify({"result": [result]})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
