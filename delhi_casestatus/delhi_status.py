# import sys
# sys.path.insert(0, '/var/www/mml_python_code')
from flask import Flask, request, jsonify, Blueprint
import requests
from bs4 import BeautifulSoup as bs
from common_code import proxy_implement
import json
import re
from datetime import datetime
import os
from common_code import common_module as cm

app = Flask(__name__)

delhi_status_bp = Blueprint('delhi', __name__)

def parse_date(d):
    for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(d.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return d.strip()


def clean_list(data):
    return [re.sub(r'\s+', ' ', item).strip() for item in data if item.strip()]


def save_json(data, case_name):
    try:
        output_dir = os.path.join(cm.BASE_DIR_OUTPUTS, "delhi_casestatus")
        os.makedirs(output_dir, exist_ok=True)

        filename = os.path.join(output_dir, f"{case_name.replace(' ', '_')}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    except Exception as e:
        print(f"Error saving JSON: {e}")


def log_status(case, status, filename="delhi_casestatus_log.txt"):
    try:
        date_folder = datetime.now().strftime('%Y-%m-%d')
        log_dir = os.path.join(cm.BASE_DIR_LOGS, date_folder)
        os.makedirs(log_dir, exist_ok=True)

        log_path = os.path.join(log_dir, filename)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{now} {case} | status : {status}\n")

    except Exception as e:
        print(f"Error logging: {e}")


# @app.route("/delhi_status", methods=["GET"])
@delhi_status_bp.route('',methods=['GET'])
def get_case_status():
    case_type = request.args.get("case_type", "")
    case_number = request.args.get("case_number", "")
    case_year = request.args.get("case_year", "")
    include_order = request.args.get("order", "").lower() == "true"

    pros = proxy_implement.get_requests_proxy()
    main_urls = f"https://delhihighcourt.nic.in/app/get-case-type-status?draw=3&columns%5B0%5D%5Bdata%5D=DT_RowIndex&columns%5B0%5D%5Bname%5D=DT_RowIndex&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=false&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B1%5D%5Bdata%5D=ctype&columns%5B1%5D%5Bname%5D=ctype&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=true&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B2%5D%5Bdata%5D=pet&columns%5B2%5D%5Bname%5D=pet&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=true&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B3%5D%5Bdata%5D=orderdate&columns%5B3%5D%5Bname%5D=orderdate&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=true&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false&order%5B0%5D%5Bcolumn%5D=0&order%5B0%5D%5Bdir%5D=asc&order%5B0%5D%5Bname%5D=DT_RowIndex&start=0&length=-1&search%5Bvalue%5D=&search%5Bregex%5D=false&case_type={case_type}&case_number={case_number}&case_year={case_year}&_=1754996384911"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://delhihighcourt.nic.in/case-status-search",
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        response = requests.get(main_urls, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json().get('data', [])
    except Exception as e:
        case_name = f"{case_type}-{case_number}-{case_year}"
        log_status(case_name, f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

    results = []
    case_name_for_file = None

    for datas in data:
        sol = {}

        types = bs(datas['ctype'], 'html.parser')
        case_type_tag = types.find('a')

        sol['case_type'] = case_type_tag.text if case_type_tag else ''
        sol['status'] = types.find('font').text.replace('[', '').replace(']', '') if types.find('font') else ''

        order_link = case_type_tag.find_next('a')['href'] if case_type_tag and case_type_tag.find_next('a') else ''
        sol['order_link'] = order_link

        sol['case_no'] = datas.get('cno', '')
        sol['case_year'] = datas.get('cyear', '')
        sol['cases'] = f"{sol['case_type']}-{sol['case_no']}-{sol['case_year']}"

        pet = [k.strip() for k in clean_list(datas['pet'].split('<br>')) if k]
        sol['petitioner'] = clean_list([pet[0]]) if pet else []
        sol['respondent'] = clean_list([pet[-1]]) if len(pet) > 1 else []

        sol['pet_adv'] = clean_list([datas.get('pet_adv', '')])
        sol['res_adv'] = clean_list([datas.get('res_adv', '')])
        sol['court_no'] = clean_list([datas['courtno']])

        order_data = clean_list(str(datas['orderdate']).split('<br>'))
        dates = clean_list([k.split(':')[-1] for k in order_data if 'next date' in str(k).lower()])
        sol['next_date'] = next((parse_date(d) for d in dates if d.strip().upper() != 'NA'), dates[0])

        last_data = clean_list([k.split(':')[-1] for k in order_data if 'last date' in str(k).lower()])
        sol['last_data'] = next((parse_date(k) for k in last_data if k.strip() != 'NA'), last_data[0])

        if include_order and order_link:
            prefix = "?draw=1&columns%5B0%5D%5Bdata%5D=DT_RowIndex&columns%5B0%5D%5Bname%5D=DT_RowIndex&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=false&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B1%5D%5Bdata%5D=case_no_order_link&columns%5B1%5D%5Bname%5D=case_no_order_link&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=true&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B2%5D%5Bdata%5D%5B_%5D=order_date.display&columns%5B2%5D%5Bdata%5D%5Bsort%5D=order_date.timestamp&columns%5B2%5D%5Bname%5D=order_date.timestamp&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=true&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B3%5D%5Bdata%5D=corrigendum&columns%5B3%5D%5Bname%5D=corrigendum&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=true&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B4%5D%5Bdata%5D=hindi_order&columns%5B4%5D%5Bname%5D=hindi_order&columns%5B4%5D%5Bsearchable%5D=true&columns%5B4%5D%5Borderable%5D=true&columns%5B4%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B4%5D%5Bsearch%5D%5Bregex%5D=false&order%5B0%5D%5Bcolumn%5D=0&order%5B0%5D%5Bdir%5D=asc&order%5B0%5D%5Bname%5D=DT_RowIndex&start=0&length=-1&search%5Bvalue%5D=&search%5Bregex%5D=false&_=1763109405244"
            main_link = order_link + prefix

            headers2 = {'user-agent': 'Mozilla/5.0','x-requested-with': 'XMLHttpRequest', 'connection': 'keep-alive',"Referer": "https://delhihighcourt.nic.in/case-status-search"}

            try:
                response = requests.get(main_link, headers=headers2)
                response = response.json()['data']

                full_order = []
                for o in response:
                    order_sol = {
                        'case_no': o['caseno'],
                        'date': str(o['orderdate']).split(' ')[0],
                        'link': bs(o['case_no_order_link'], 'html.parser').find('a')['href'],
                        'judgement': 'Order'
                    }
                    full_order.append(order_sol)

                sol['judgement'] = full_order
            except:
                pass

        results.append(sol)

        if case_name_for_file is None:
            case_name_for_file = sol['cases']

    if not results:
        case_name_for_file = f"{case_type}-{case_number}-{case_year}"

    save_json(results, case_name_for_file)

    for case in results:
        log_status(case['cases'], "completed")

    return jsonify({'result': results})









# from flask import Flask, request, jsonify,Blueprint
# import requests
# from bs4 import BeautifulSoup as bs
# from common_code import proxy_implement
# import json
# import re
# from datetime import datetime
# import os
# from common_code import common_module as cm
#
# delhi_status_bp = Blueprint('delhi',__name__)
#
# def parse_date(d):
#     for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
#         try:
#             return datetime.strptime(d.strip(), fmt).strftime("%Y-%m-%d")
#         except ValueError:
#             continue
#     return d.strip()
#
# def clean_list(data):
#     return [re.sub(r'\s+', ' ', item).strip() for item in data if item.strip()]
#
# def save_json(data, case_name):
#     try:
#         output_dir = os.path.join(cm.BASE_DIR_OUTPUTS, "delhi_casestatus")
#         os.makedirs(output_dir, exist_ok=True)  # make sure folder exists
#
#         filename = os.path.join(output_dir, f"{case_name.replace(' ', '_')}.json")
#         with open(filename, "w", encoding="utf-8") as f:
#             json.dump(data, f, indent=4, ensure_ascii=False)
#
#     except Exception as e:
#         print(f"Error saving JSON: {e}")
#
# def log_status(case, status, filename="delhi_casestatus_log.txt"):
#     try:
#         # Folder path with today's date
#         date_folder = datetime.now().strftime('%Y-%m-%d')
#         log_dir = os.path.join(cm.BASE_DIR_LOGS, date_folder)
#         os.makedirs(log_dir, exist_ok=True)
#
#         log_path = os.path.join(log_dir, filename)
#         now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#
#         with open(log_path, "a", encoding="utf-8") as f:
#             f.write(f"{now} {case} | status : {status}\n")
#
#     except Exception as e:
#         print(f"Error logging: {e}")
#
# @delhi_status_bp.route('',methods=['GET'])
# # @app.route("/delhi_status", methods=["GET"])
# def get_case_status():
#     case_type = request.args.get("case_type", "")
#     case_number = request.args.get("case_number", "")
#     case_year = request.args.get("case_year", "")
#
#     pros = proxy_implement.get_requests_proxy()
#     main_urls = f"https://delhihighcourt.nic.in/app/get-case-type-status?draw=3&columns%5B0%5D%5Bdata%5D=DT_RowIndex&columns%5B0%5D%5Bname%5D=DT_RowIndex&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=false&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B1%5D%5Bdata%5D=ctype&columns%5B1%5D%5Bname%5D=ctype&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=true&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B2%5D%5Bdata%5D=pet&columns%5B2%5D%5Bname%5D=pet&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=true&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B3%5D%5Bdata%5D=orderdate&columns%5B3%5D%5Bname%5D=orderdate&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=true&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false&order%5B0%5D%5Bcolumn%5D=0&order%5B0%5D%5Bdir%5D=asc&order%5B0%5D%5Bname%5D=DT_RowIndex&start=0&length=-1&search%5Bvalue%5D=&search%5Bregex%5D=false&case_type={case_type}&case_number={case_number}&case_year={case_year}&_=1754996384911"
#     headers = { "User-Agent": "Mozilla/5.0","Referer": "https://delhihighcourt.nic.in/case-status-search","X-Requested-With": "XMLHttpRequest"}
#
#     try:
#         response = requests.get(main_urls, proxies=pros, headers=headers, timeout=15)
#         response.raise_for_status()
#         data = response.json().get('data', [])
#     except Exception as e:
#         # Log error with case info from query params
#         case_name = f"{case_type}-{case_number}-{case_year}"
#         log_status(case_name, f"Error: {str(e)}")
#         return jsonify({"error": str(e)}), 500
#
#     results = []
#     case_name_for_file = None
#
#     for datas in data:
#         sol = dict()
#         types = bs(datas['ctype'], 'html.parser')
#         case_type_tag = types.find('a')
#
#         sol['case_type'] = case_type_tag.text if case_type_tag else ''
#         sol['status'] = types.find('font').text.replace('[','').replace(']','') if types.find('font') else ''
#         sol['order_link'] = case_type_tag.find_next('a')['href'] if case_type_tag and case_type_tag.find_next('a') else ''
#         sol['case_no'] = datas.get('cno', '')
#         sol['case_year'] = datas.get('cyear', '')
#         sol['cases'] = f"{sol['case_type']}-{sol['case_no']}-{sol['case_year']}"
#         pet = [k.strip() for k in clean_list(datas['pet'].split('<br>')) if k]
#         sol['petitioner'] = clean_list([pet[0]]) if pet else []
#         sol['respondent'] = clean_list([pet[-1]]) if len(pet) > 1 else []
#
#         sol['pet_adv'] = clean_list([datas.get('pet_adv', '')])
#         sol['res_adv'] = clean_list([datas.get('res_adv', '')])
#         sol['court_no'] = clean_list([datas['courtno']])
#
#         order_data = clean_list(str(datas['orderdate']).split('<br>'))
#         dates = clean_list([k.split(':')[-1] for k in order_data if 'next date' in str(k).lower()])
#         sol['next_date'] = next((parse_date(d) for d in dates if d.strip().upper() != 'NA'), dates[0])
#
#         last_data = clean_list([k.split(':')[-1] for k in order_data if 'last date' in str(k).lower()])
#         sol['last_data'] = next((parse_date(k) for k in last_data if k.strip() != 'NA'), last_data[0])
#
#         results.append(sol)
#
#         if case_name_for_file is None:
#             case_name_for_file = sol['cases']
#
#     if not results:
#         case_name_for_file = f"{case_type}-{case_number}-{case_year}"
#
#     save_json(results, case_name_for_file)
#
#     for case in results:
#         log_status(case['cases'], "completed")
#
#     return jsonify({'result':results})
#
# # if __name__ == "__main__":
# #     app.run(debug=True, host="0.0.0.0", port=5000)
#
# # http://192.168.2.116:5000/case-status?case_type=ARB.A.&case_number=1&case_year=2025