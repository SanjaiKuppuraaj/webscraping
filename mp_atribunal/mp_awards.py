import re
import time
import html
import json
import os
from datetime import datetime
from dateutil import parser as date_parser
from bs4 import BeautifulSoup as bs
from flask import Blueprint, request, jsonify
from common_code import common_module as cm
from playwright.sync_api import sync_playwright

mpaward_blueprint = Blueprint('mpaward_blueprint', __name__, template_folder='templates')


@mpaward_blueprint.route('', methods=['GET'])
def mp_awards():
    case_no = request.args.get('case_number')

    # Basic validation
    pattern = r"^[A-Za-z]+-?\s*\d+/\d{4}$"
    if not case_no or not re.match(pattern, case_no.strip()):
        return jsonify({
            "message": "No Record Found.",
            "result": "error"
        })

    status = "Completed"
    base_folder = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(base_folder, exist_ok=True)
    log_file_path = os.path.join(base_folder, 'mp_atribunal_orders_logs.txt')

    try:
        with sync_playwright() as p:
            # --- Launch chromium safely for server ---
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )

            # --- Ignore SSL issues ---
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            # --- Navigate ---
            print(f"Searching case: {case_no}")
            page.goto('https://atribunal.mp.gov.in/cause-download', timeout=30000)
            page.wait_for_load_state('load')

            # --- Search case ---
            page.fill('#search_text_4', case_no)
            page.click('#search')
            page.wait_for_load_state('networkidle')

            # --- Wait for results to appear ---
            page.wait_for_selector('#ajaxdata table tbody tr td:nth-child(8) a', timeout=20000)
            page.click('#ajaxdata table tbody tr td:nth-child(8) a')

            # --- Wait for award details table ---
            page.wait_for_selector('#ajaxAwardOrderDetails', timeout=20000)
            time.sleep(1)

            # --- Extract HTML ---
            page_source = page.content()
            soup = bs(page_source, 'html.parser')
            results = []

            # --- Find details section ---
            details_div = soup.find('div', id='ajaxAwardOrderDetails')
            if not details_div:
                raise Exception("No award details found in the page")

            tbody = details_div.find('tbody')
            if not tbody:
                raise Exception("No table body found in award order details")

            rows = tbody.find_all('tr')
            for row in rows:
                sol = {}

                sno_td = row.find('td')
                sol['sno'] = sno_td.text.strip() if sno_td else ''

                reason_td = sno_td.find_next('td') if sno_td else None
                sol['judgement'] = reason_td.text.strip() if reason_td else ''

                date_td = reason_td.find_next('td') if reason_td else None
                if date_td:
                    raw_date = date_td.text.strip()
                    try:
                        dt_obj = datetime.strptime(raw_date, "%d-%m-%Y")
                        sol['date'] = dt_obj.strftime("%B %d, %Y")
                    except Exception:
                        sol['date'] = raw_date
                else:
                    sol['date'] = ''

                link_tag = row.find('a')
                if link_tag and 'href' in link_tag.attrs:
                    href = link_tag['href']
                    fixed_link = href.replace('\u0026', '&')
                    decoded_href = fixed_link.encode().decode('unicode_escape')
                    sol['link'] = html.unescape(decoded_href)
                else:
                    sol['link'] = ''

                results.append(sol)

            # --- Sort results by date (desc) ---
            def parse_date_safe(item):
                try:
                    return date_parser.parse(item['date'])
                except Exception:
                    return datetime.min

            results.sort(key=parse_date_safe, reverse=True)

            # --- Save output JSON ---
            case_folder = os.path.join(cm.BASE_DIR_OUTPUTS, 'mp_atribunal')
            os.makedirs(case_folder, exist_ok=True)
            case_filename = case_no.replace('/', '_') + '_order.json'
            json_file_path = os.path.join(case_folder, case_filename)

            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump({'result': results}, f, indent=4, ensure_ascii=False)

            # --- Log success ---
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file_path, 'a') as log_file:
                log_file.write(f"{current_time} - {case_no} | status: {status}\n")

            browser.close()
            return jsonify({"result": results})

    except Exception as e:
        # --- Error handling ---
        status = "Error"
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file_path, 'a') as log_file:
            log_file.write(f"{current_time} - {case_no} | status: {status} - Error: {e}\n")

        print(f"Error: {e}")
        return jsonify({
            "message": "No Record Found.",
            "result": "error"
        })














# import re
# import time
# import html
# import json
# import os
# from datetime import datetime
# from dateutil import parser as date_parser
# from bs4 import BeautifulSoup as bs
# from flask import Blueprint, request, jsonify
# from common_code import common_module as cm
# from playwright.sync_api import sync_playwright
#
# mpaward_blueprint = Blueprint('mpaward_blueprint', __name__, template_folder='templates')
#
# @mpaward_blueprint.route('', methods=['GET'])
# def mp_awards():
#     case_no = request.args.get('case_number')
#     pattern = r"^[A-Za-z]+-?\s*\d+/\d{4}$"
#     if not case_no or not re.match(pattern, case_no.strip()):
#         return jsonify({"message": "No Record Found.","result": "error"})
#     status = "Completed"
#     base_folder = cm.BASE_DIR_LOGS + '/' + datetime.now().strftime('%Y-%m-%d') + '/'
#     os.makedirs(base_folder, exist_ok=True)
#     log_file_path = os.path.join(base_folder, 'mp_atribunal_orders_logs.txt')
#     try:
#         with sync_playwright() as p:
#             browser = p.chromium.launch(headless=True)
#             context = browser.new_context()
#             page = context.new_page()
#             page.goto('https://atribunal.mp.gov.in/cause-download', timeout=10000)
#             page.fill('#search_text_4', case_no)
#             page.click('#search')
#             page.wait_for_selector('//*[@id="ajaxdata"]/div[1]/table/tbody/tr/td[8]/a', timeout=5000)
#             page.click('//*[@id="ajaxdata"]/div[1]/table/tbody/tr/td[8]/a')
#             page.wait_for_selector('#ajaxAwardOrderDetails', timeout=5000)
#             time.sleep(1)
#             page_source = page.content()
#             soup = bs(page_source, 'html.parser')
#             results = []
#             rows = soup.find('div', {'id': 'ajaxAwardOrderDetails'}).find('tbody').find_all('tr')
#             for row in rows:
#                 sol = {}
#                 sol['sno'] = row.find('td').text.strip() if row.find('td') else ''
#                 reason_td = row.find('td').find_next('td')
#                 sol['judgement'] = reason_td.text.strip() if reason_td else ''
#                 date_td = reason_td.find_next('td') if reason_td else ''
#                 if date_td:
#                     raw_date = date_td.text.strip()
#                     try:
#                         dt_obj = datetime.strptime(raw_date, "%d-%m-%Y")
#                         sol['date'] = dt_obj.strftime("%B %d, %Y")
#                     except Exception:
#                         sol['date'] = raw_date
#                 else:
#                     sol['date'] = ''
#
#                 link_tag = row.find('a')
#                 if link_tag and 'href' in link_tag.attrs:
#                     href = link_tag['href']
#                     fixed_link = href.replace('\u0026', '&')
#                     decoded_href = fixed_link.encode().decode('unicode_escape')
#                     sol['link'] = html.unescape(decoded_href)
#                 results.append(sol)
#             def parse_date_safe(item):
#                 try:
#                     return date_parser.parse(item['date'])
#                 except:
#                     return datetime.min
#             results.sort(key=parse_date_safe, reverse=True)
#             case_folder = os.path.join(cm.BASE_DIR_OUTPUTS, 'mp_atribunal')
#             os.makedirs(case_folder, exist_ok=True)
#             case_filename = case_no.replace('/', '_') + '_order.json'
#             json_file_path = os.path.join(case_folder, case_filename)
#             with open(json_file_path, 'w') as f:
#                 json.dump({'result': results}, f, indent=4)
#             current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             with open(log_file_path, 'a') as log_file:
#                 log_file.write(f"{current_time} - {case_no} | status: {status}\n")
#             browser.close()
#             return jsonify({"result": results})
#     except Exception as e:
#         status = "Error"
#         current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         with open(log_file_path, 'a') as log_file:
#             log_file.write(f"{current_time} - {case_no} | status: {status} - Error: {e}\n")
#
#         return jsonify({"message": "No Record Found.", "result": "error"})
