import time
import os
import requests
from bs4 import BeautifulSoup as bs
from playwright.sync_api import sync_playwright
from flask import Blueprint, jsonify, request, send_file
from datetime import datetime
session = requests.session()

delhi_bp = Blueprint("delhi_display_board", __name__)

urls = "https://delhihighcourt.nic.in/app/physical-display-board?draw=3&columns%5B0%5D%5Bdata%5D=court&columns%5B0%5D%5Bname%5D=court&start=0&length=-1"
headers = {"user-agent": "Mozilla/5.0", "x-requested-with": "XMLHttpRequest", "referer": "https://delhihighcourt.nic.in/app/physical-display-board"}

def fetch_json():
    res = session.get(urls, headers=headers).json()
    total_count = res.get("recordsTotal", 0)
    raw = res.get("data", [])
    parsed = []
    for item in raw:
        sol = {
            "court_no": item.get("court_no"),
            "disp_court_no": item.get("disp_court_no"),
            "item": item.get("item"),
            "case_no": item.get("case_no"),
        }
        sol["judge_name"] = [j for j in str(item["judge_name"]).split("<br>") if j]
        raw_party = str(item["party_name"]).replace("<br>", "")
        parts = raw_party.split("Vs")
        sol["petitioner"] = parts[0].strip()
        sol["respondent"] = parts[1].strip() if len(parts) > 1 else ""
        soup = bs(item["vc_link"], "html.parser")
        tag = soup.find("a")
        sol["vc_link"] = tag["href"] if tag else ""
        parsed.append(sol)
    return {"data": parsed, "count": total_count}

def fetch_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://delhihighcourt.nic.in/app/physical-display-board")
        page.select_option("select[name='physical_display_board_length']", "-1")
        time.sleep(1.8)
        soup = bs(page.content(), "html.parser")
        soup = soup.find("div", {"class": "dt-layout-row dt-layout-table"})
        table_title = soup.find('tr', {'role': 'row'}).decompose()
        div = soup.find("div", class_="dt-scroll-body")
        if div and div.has_attr("style"):
            del div["style"]
        browser.close()
        return str(soup)

@delhi_bp.route("",methods=['GET'])
def display_board():
    output_type = request.args.get("output_type", "json")
    if output_type == "html":
        html = fetch_html()
        date = datetime.now().strftime("%d-%m-%Y")
        file_name = f"delhi_{date}.html"

        file_path = os.path.join("/tmp", file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html)
        return send_file(file_path,as_attachment=True,download_name=file_name,mimetype="text/html",)

    return jsonify(fetch_json())


# http://localhost/delhi_display_board?output_type=json
# http://localhost/delhi_display_board?output_type=html