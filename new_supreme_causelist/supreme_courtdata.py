import sys
sys.path.insert(0, '/var/www/mml_python_code')
from flask import Flask, request, jsonify,Blueprint
import os
import time
import requests
import subprocess
import sys
import json
from datetime import datetime
from bs4 import BeautifulSoup as bs
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from common_code.proxy_implement import get_requests_proxy, get_playwright_proxy,get_new_requests_playwright
from common_code import common_module as cm

BASE_PATH = "/var/www/mml_python_code/new_supreme_causelist"
BASE_FOLDER = os.path.join(cm.BASE_DIR_OUTPUTS, 'new_supreme_causelist')
OUTPUT_FOLDER = os.path.join(BASE_FOLDER, 'output')
LOG_FILE = os.path.join(BASE_FOLDER, "supreme_court.txt")

SUPREME_HTML = os.path.join(BASE_PATH, 'supreme_html.py')
SUPREME_SCRAPING = os.path.join(BASE_PATH, 'supreme_scraping.py')

# app = Flask(__name__)

supreme_blueprint = Blueprint('supreme_court', __name__)


def log_status(label_name, status):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"[{timestamp}] {label_name} - {status}\n")

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()
    else:
        log_status("Shutdown", "Skipped: Not running with Werkzeug")


# @app.route('/supremecourt', methods=['GET'])
@supreme_blueprint.route('', methods=['GET'])
def supreme_court_handler():
    search_date = request.args.get('date')
    update = request.args.get('update', 'false').lower() == 'true'
    if not search_date:
        return jsonify({"error": "Missing 'date' parameter"}), 400
    result = run_supreme_court_fetch(search_date, update)
    if update:
        shutdown_server()
    return jsonify(result)
def run_supreme_court_fetch(search_date, update=False):
    # json_folder = os.path.join(BASE_FOLDER, search_date)
    json_folder = os.path.join(BASE_FOLDER, 'json_data', search_date)

    os.makedirs(json_folder, exist_ok=True)

    if update:
        with open(LOG_FILE, "w") as f:
            f.write(f"--- Supreme Court Cause List Run Started: {search_date} ---\n")

    if not update:
        json_files = [f for f in os.listdir(json_folder) if f.endswith('.json')]
        if json_files:
            results = []
            for f in json_files:
                try:
                    with open(os.path.join(json_folder, f), 'r', encoding='utf-8') as j:
                        results.append(json.load(j))
                except Exception as e:
                    results.append({"file": f, "error": str(e)})
            return {"status": "cached", "date": search_date, "results": results}
        else:
            return {"status": "no cached data found", "date": search_date}

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    clean_old_files(OUTPUT_FOLDER)

    result = get_pdf_links_for_date(search_date)
    if not result:
        return {"status": "No data found on SCI website", "date": search_date}

    processed_files = []

    for section, value in result.items():
        if isinstance(value, dict):
            for sub_section, sub_value in value.items():
                if isinstance(sub_value, dict):
                    for label, link in sub_value.items():
                        if link:
                            label_name = f"{section}_{sub_section}_{label}".replace(" ", "_").upper()
                            if process_pdf(link, label_name, search_date):
                                json_file_path = os.path.join(json_folder, f"{label_name}-{search_date}.json")
                                if os.path.exists(json_file_path):
                                    with open(json_file_path, 'r') as f:
                                        processed_files.append(json.load(f))
                else:
                    if sub_value:
                        label_name = f"{section}_{sub_section}".replace(" ", "_").upper()
                        if process_pdf(sub_value, label_name, search_date):
                            json_file_path = os.path.join(json_folder, f"{label_name}-{search_date}.json")
                            if os.path.exists(json_file_path):
                                with open(json_file_path, 'r') as f:
                                    processed_files.append(json.load(f))
        else:
            if value:
                label_name = f"{section}".replace(" ", "_").upper()
                if process_pdf(value, label_name, search_date):
                    json_file_path = os.path.join(json_folder, f"{label_name}-{search_date}.json")
                    if os.path.exists(json_file_path):
                        with open(json_file_path, 'r') as f:
                            processed_files.append(json.load(f))

    return {"status": "updated", "date": search_date, "results": processed_files}

def clean_old_files(folder):
    for fname in os.listdir(folder):
        if fname.endswith(('.pdf', '.csv', '.html')):
            try:
                os.remove(os.path.join(folder, fname))
            except Exception as e:
                print(f"Error removing file {fname}: {e}")

def get_pdf_links_for_date(search_date):
    url = 'https://www.sci.gov.in/cause-list/'
    try:
        response = requests.get(url, proxies=get_requests_proxy())
    except Exception as e:
        print(f"Failed to fetch cause list page: {e}")
        return {}

    soup = bs(response.text, 'html.parser')
    time.sleep(5)

    table_div = soup.find('div', {'class': 'cause_list_future_published over-x-scroll'})
    if not table_div:
        return {}

    table = table_div.find('table')
    if not table:
        return {}

    rows = table.find('tbody').find_all('tr')

    categories = [
        ("JUDGE", "MISCELLANEOUS", "ADVANCE"),
        ("JUDGE", "MISCELLANEOUS", "MAIN"),
        ("JUDGE", "MISCELLANEOUS", "supplementary"),
        ("JUDGE", "REGULAR", "MAIN"),
        ("JUDGE", "REGULAR", "supplementary"),
    ]
    labels = ["CHAMBER", "SINGLE JUDGE", "REVIEW & CURATIVE", "REGISTRAR"]
    for label in labels:
        categories.append((label, "MAIN"))
        categories.append((label, "SUPPL."))

    result = {}
    for row in rows:
        cells = row.find_all('td')
        data_cells = cells[1:] if cells[0].get('rowspan') else cells
        if not any(a and a.text.strip() == search_date for td in data_cells for a in td.find_all('a')):
            continue
        for i, td in enumerate(data_cells):
            link_tag = td.find('a')
            link = link_tag['href'] if link_tag else ""
            if i >= len(categories):
                continue
            key = categories[i]
            current = result
            for part in key[:-1]:
                current = current.setdefault(part, {})
            current[key[-1]] = 'https://www.sci.gov.in' + link if link and not link.startswith("http") else link

    return result

def download_pdf(pdf_url, pdf_path, retries=3):
    try:
        proxy = get_requests_proxy()
    except Exception:
        proxy = None

    for attempt in range(1, retries + 1):
        try:
            print(f"[Download Attempt {attempt}] {pdf_url}")
            response = requests.get(pdf_url, proxies=proxy, timeout=30)
            if response.status_code == 200:
                os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                print(f"Failed with status: {response.status_code}")
        except Exception as e:
            print(f"Attempt {attempt} failed to download PDF: {e}")
        time.sleep(3)
    return False

def convert_pdf_to_csv(pdf_path, csv_path, retries=3):
    # proxy = get_playwright_proxy()
    proxy = get_new_requests_playwright()

    for attempt in range(1, retries + 1):
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, proxy=proxy)
            page = browser.new_page()
            try:
                print(f"[CSV Conversion Attempt {attempt}] {pdf_path}")
                page.goto("https://www.zamzar.com/convert/pdf-to-csv/", wait_until="domcontentloaded", timeout=100000)
                time.sleep(3)
                page.locator("input[type='file'][multiple]").set_input_files(pdf_path)
                time.sleep(5)
                page.click("button:has-text('Convert Now')")
                time.sleep(15)
                page.wait_for_selector("[class='btn btn-blue-4 btn-lg']", timeout=130000)
                with page.expect_download(timeout=90000) as download_info:
                    page.locator("[class='btn btn-blue-4 btn-lg']").click()
                download = download_info.value
                os.makedirs(os.path.dirname(csv_path), exist_ok=True)
                download.save_as(csv_path)

                if os.path.exists(csv_path):
                    return True
            except Exception as e:
                print(f"Conversion attempt {attempt} failed: {e}")
                time.sleep(10)
            finally:
                browser.close()
    return False

def process_pdf(link, label_name, search_date):
    # json_folder = os.path.join(BASE_FOLDER, search_date)
    json_folder = os.path.join(BASE_FOLDER, 'json_data', search_date)

    os.makedirs(json_folder, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    pdf_path = os.path.join(OUTPUT_FOLDER, os.path.basename(link))
    csv_path = os.path.join(OUTPUT_FOLDER, os.path.basename(link).replace('.pdf', '_csv.csv'))
    json_file_name = f"{label_name}-{search_date}.json"
    json_path = os.path.join(json_folder, json_file_name)

    try:
        if not download_pdf(link, pdf_path):
            log_status(json_file_name, "error: PDF download failed after retries")
            return False

        if not convert_pdf_to_csv(pdf_path, csv_path):
            log_status(json_file_name, "error: CSV conversion failed after retries")
            return False

        try:
            subprocess.run([sys.executable, SUPREME_HTML, csv_path, json_path], check=True)
        except subprocess.CalledProcessError as e:
            log_status(json_file_name, f"error in supreme_html.py: {e}")
            return False

        try:
            subprocess.run([sys.executable, SUPREME_SCRAPING, csv_path, json_path, link, label_name], check=True)
        except subprocess.CalledProcessError as e:
            log_status(json_file_name, f"error in supreme_scraping.py: {e}")
            return False

        log_status(json_file_name, "completed")
        return True

    except Exception as e:
        log_status(json_file_name, f"error: {str(e)}")
        return False
