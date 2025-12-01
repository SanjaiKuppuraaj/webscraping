from flask import Blueprint, request, jsonify, send_file
import requests
from bs4 import BeautifulSoup as bs
import os
from datetime import datetime

session = requests.session()
display_board_bp = Blueprint("display_board", __name__)

url = "https://judiciary.karnataka.gov.in/display_board_bench.php"

BENCH_MAP = {"01": "bengaluru","02": "dharwad","03": "kalaburagi"}

def scrape_bench(bench_id):
    headers = {'user-agent': 'Mozilla/5.0', 'referer': 'https://judiciary.karnataka.gov.in/'}
    res = session.get(url, headers=headers)
    soup = bs(res.text, "html.parser")

    root = soup.find("div", {"class": "common_tabs"})
    section = root.find("div", {"id": bench_id})

    if not section:
        return [], None

    tbodys = section.find_all("tbody")
    data_list = []
    for tbody in tbodys:
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 5:
                continue

            data_list.append({
                "ch_no": tds[0].get_text(strip=True),
                "list_no": tds[1].get_text(strip=True),
                "si_no": tds[2].get_text(strip=True),
                "case_no": tds[3].get_text(strip=True),
                "stage": tds[4].get_text(strip=True)
            })

    table_html = section.prettify()
    return data_list, table_html

@display_board_bp.route("",methods=['GET'])
def display_board():
    bench = request.args.get("bench")
    output_type = request.args.get("output_type", "json").lower()

    if bench not in BENCH_MAP:
        return jsonify({"error": "bench must be 01, 02, or 03"}), 400
    bench_id = BENCH_MAP[bench]
    data, table_html = scrape_bench(bench_id)

    if output_type == "json":
        return jsonify({"bench": bench, "bench_name": bench_id,"count": len(data),"data": data})

    if output_type == "html":
        today = datetime.now().strftime("%d-%m-%Y")
        file_name = f"{bench_id}_{today}.html"
        file_path = os.path.join("/tmp", file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(table_html)

        return send_file(file_path,as_attachment=True,download_name=file_name, mimetype="text/html" )
    return jsonify({"error": "output_type must be json or html"}), 400


# http://167.71.225.203/karantaka_display_board?bench=01&output_type=json == json view
# http://167.71.225.203/karantaka_display_board?bench=01&output_type=html == html download
