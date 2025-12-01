import json

from flask import Blueprint, request, jsonify
import requests
from bs4 import BeautifulSoup as bs
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from io import BytesIO
import re
import time
from datetime import datetime

rera_bp = Blueprint("rera_bp", __name__)

base_url = "https://haryanarera.gov.in/assistancecontrol/searchcaseopen"
main_url = "https://haryanarera.gov.in/assistancecontrol/search_case_open"

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/117.0.5938.132 Safari/537.36"
}

session = requests.Session()
session.headers.update(headers)


def get_token_and_captcha():
    resp = session.get(base_url)
    soup = bs(resp.text, "html.parser")
    token = soup.find("input", {"name": "qwerty_"})["value"]
    captcha_link = soup.find("img", {"id": "imageid"})["src"]

    captcha_resp = session.get(captcha_link)
    image = Image.open(BytesIO(captcha_resp.content))
    image = image.convert("L")
    image = ImageEnhance.Contrast(image).enhance(8)
    image = image.resize((image.width * 6, image.height * 7))
    image = image.filter(ImageFilter.MedianFilter(size=3))
    image = image.point(lambda x: 0 if x < 180 else 255, "1")
    image = image.filter(ImageFilter.SHARPEN)

    raw_text = pytesseract.image_to_string(image, lang="eng", config="--psm 12")
    clean_text = re.sub(r"[^A-Za-z0-9]", "", raw_text)[:6]

    return token, clean_text


def search_case(case_type, case_no, case_year, max_retries=5):
    for attempt in range(max_retries):
        token, captcha = get_token_and_captcha()
        print(f"[Attempt {attempt + 1}] Captcha solved as: {captcha}")

        payload = {
            "qwerty_": token,
            "t_case_type": case_type,
            "t_case_no": case_no,
            "t_case_year": case_year,
            "captcha": captcha,
            "submit": "Search"
        }

        res = session.post(main_url, data=payload, headers=headers)
        soup = bs(res.text, "html.parser")

        table = soup.find("table", {"id": "table"})
        if table:
            print("Captcha accepted, data found!")
            rows = table.find("tbody").find_all("tr")

            results = []
            for row in rows:
                sol = dict()
                case_no = row.find("td")
                parts = case_no.text.split("-")
                sol['case_type'] = "-".join(parts[:-2])
                sol['case_no'] = parts[-2]
                sol['case_year'] = parts[-1]

                petitioner = case_no.find_next('td')
                sol['petitioner'] = petitioner.text

                respondent = petitioner.find_next('td')
                sol['respondent'] = respondent.text if respondent else ''

                adv_name = respondent.find_next('td')
                sol['petitioner_adv'] = adv_name.text if adv_name else ''

                status = adv_name.find_next('td')
                sol['case_status'] = status.text if status else ''

                next_data = status.find_next('td')
                raw_date_text = next_data.text.strip()

                try:
                    formatted_date = datetime.strptime(
                        raw_date_text, "%d-%b-%Y"
                    ).strftime("%Y-%m-%d")
                    sol['next_hearing_date'] = formatted_date
                except Exception:
                    sol['next_hearing_date'] = raw_date_text if raw_date_text else None

                results.append(sol)

            return results

        print("Captcha failed, retrying...\n")
        time.sleep(2)

    return None


@rera_bp.route("", methods=["GET"])
def search_case_api():
    case_type = request.args.get("case_type")
    case_no = request.args.get("case_no")
    case_year = request.args.get("case_year")

    if not all([case_type, case_no, case_year]):
        return jsonify({"error": "Missing required params"}), 400

    data = search_case(case_type, case_no, case_year)
    if data:
        return jsonify({"result": data[0]})
    else:
        return jsonify({"error": "Failed after retries"}), 500
