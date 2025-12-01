import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime
from flask import Flask, request, jsonify, Blueprint
from common_code import proxy_implement
from common_code import common_module as cm
import os
import traceback

app = Flask(__name__)
log_dir = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'cgit_labour.txt')

proxy = proxy_implement.get_requests_proxy()
cgit_blueprint = Blueprint('cgit_labour', __name__)

def write_log(state_type, case_no, status, error_msg=None):
    time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a', encoding='utf-8') as f:
        if error_msg:
            f.write(f"{time_now} | {state_type} | {case_no} | Status : Failed | Error : {error_msg}\n")
        else:
            f.write(f"{time_now} | {state_type} | {case_no} | Status : Completed\n")

def main(state_code, case_no):
    state_type = str(state_code).replace('all', 'All')
    case_number = "%22" + str(case_no).replace(' ', '+').replace('/', '%2F') + "%22"
    results = []

    try:
        url = (
            f'https://cgit.labour.gov.in/cause-list?field_date_value%5Bvalue%5D%5Bdate%5D='
            f'&field_term_cgit_tid={state_type}&field_name_of_appellant_value='
            f'&field_respondent__value=&field_case_no__value={case_number}&field_case_type_tid=All'
        )

        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/117.0.5938.132 Safari/537.36',
            'referer': url
        }

        response = requests.get(url, headers=headers, proxies=proxy)
        response.raise_for_status()
        soup = bs(response.text, 'html.parser')

        table = soup.find('table', {'class': "views-table cols-10"})
        if not table:
            write_log(state_type, case_no, status="Failed", error_msg="No data table found")
            return jsonify({'message': 'no record found', 'result': ''})

        tbody = table.find('tbody')

        def clean_text(text):
            return str(text).replace('\n', '').strip()

        for row in tbody.find_all('tr'):
            sol = {}
            tds = row.find_all('td')
            if len(tds) < 7:
                continue

            sol['cases'] = clean_text(tds[1].text)
            case_parts = sol['cases'].split('/')
            sol['case_no'] = case_parts[-2].split(' ')[-1] if len(case_parts) >= 2 else ''
            sol['case_year'] = case_parts[-1] if case_parts else ''
            sol['subject'] = clean_text(tds[2].text)
            sol['case_type'] = clean_text(tds[3].text)
            sol['petitioner'] = clean_text(tds[4].text)
            sol['respondent'] = clean_text(tds[5].text)

            next_dates = [span.text.strip() for span in tds[6].find_all('span')]
            date_objs = []
            for d in next_dates:
                for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
                    try:
                        date_objs.append(datetime.strptime(d, fmt))
                        break
                    except ValueError:
                        continue
            sol['next_hearing_date'] = max(date_objs).strftime("%Y-%m-%d") if date_objs else ''

            details_td = tds[7] if len(tds) > 7 else None
            sol['details'] = clean_text(details_td.text) if details_td else ''

            orders_td = tds[8] if len(tds) > 8 else None
            links = [a['href'] for a in orders_td.find_all('a')] if orders_td else []
            order_list = []
            seen = set()
            for lk, dt in zip(links, [d.strftime("%Y-%m-%d") for d in date_objs]):
                if (lk, dt) not in seen:
                    order_list.append({
                        "judgement": "Order",
                        "date": dt,
                        "link": lk
                    })
                    seen.add((lk, dt))

            sol['judgement'] = order_list
            results.append(sol)

        if results:
            write_log(state_type, case_no, status="Completed")
            return jsonify({'result': results[0]})
        else:
            write_log(state_type, case_no, status="Failed", error_msg="No record found")
            return jsonify({'message': 'no record found', 'result': ''})

    except Exception as e:
        err_msg = f"{str(e)} | Traceback: {traceback.format_exc().splitlines()[-1]}"
        write_log(state_type, case_no, status="Failed", error_msg=err_msg)
        return jsonify({'message': 'error occurred', 'error': str(e)})

@cgit_blueprint.route('', methods=['GET'])
def cgit_labour():
    state_code = request.args.get('state_code')
    case_no = request.args.get('case_no')
    if not state_code or not case_no:
        return jsonify({'message': 'state_code and case_no are required', 'result': ''})
    return main(state_code, case_no)

# app.register_blueprint(cgit_blueprint)




















# import requests
# from bs4 import BeautifulSoup as bs
# import json
# from datetime import datetime
# from flask import Flask, request, jsonify, Blueprint
# from common_code import proxy_implement
# from common_code import common_module as cm
# import os
# import traceback
#
# log_dir = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
# os.makedirs(log_dir, exist_ok=True)
# log_file = os.path.join(log_dir, 'cgit_labour.txt')
#
# proxy = proxy_implement.get_requests_proxy()
# cgit_blueprint = Blueprint('cgit_labour', __name__)
#
# def write_log(state_type, case_no, status, error_msg=None):
#     time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#     with open(log_file, 'a', encoding='utf-8') as f:
#         if error_msg:
#             f.write(f"{time_now} | {state_type} | {case_no} | Status : Failed | Error : {error_msg}\n")
#         else:
#             f.write(f"{time_now} | {state_type} | {case_no} | Status : Completed\n")
#
# def main(state_code, case_no):
#     state_type = str(state_code).replace('all', 'All')
#     case_number = "%22" + str(case_no).replace(' ', '+').replace('/', '%2F') + "%22"
#     results = []
#
#     try:
#         url = f'https://cgit.labour.gov.in/cause-list?field_date_value%5Bvalue%5D%5Bdate%5D=&field_term_cgit_tid={state_type}&field_name_of_appellant_value=&field_respondent__value=&field_case_no__value={case_number}&field_case_type_tid=All'
#         headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.132 Safari/537.36','referer': url}
#
#         response = requests.get(url, headers=headers, proxies=proxy)
#         response.raise_for_status()
#         soup = bs(response.text, 'html.parser')
#
#         table = soup.find('table', {'class': "views-table cols-10"})
#         if not table:
#             write_log(state_type, case_no, status="Failed", error_msg="No data table found")
#             return jsonify({'message': 'no record found', 'result': ''})
#
#         tbody = table.find('tbody')
#
#         def clean_text(text):
#             return str(text).replace('\n', '').strip()
#
#         for row in tbody.find_all('tr'):
#             sol = {}
#             sno = row.find('td')
#             case_no_td = sno.find_next('td') if sno else None
#             sol['cases'] = clean_text(case_no_td.text) if case_no_td else ''
#             case_parts = clean_text(case_no_td.text).split('/') if case_no_td else []
#             sol['case_no'] = case_parts[-2].split(' ')[-1] if len(case_parts) >= 2 else ''
#             sol['case_year'] = case_parts[-1] if case_parts else ''
#             subject = case_no_td.find_next('td') if case_no_td else None
#             sol['subject'] = clean_text(subject.text) if subject else ''
#             case_type = subject.find_next('td') if subject else None
#             sol['case_type'] = clean_text(case_type.text) if case_type else ''
#             appellant_name = case_type.find_next('td') if case_type else None
#             sol['petitioner'] = clean_text(appellant_name.text) if appellant_name else ''
#             respondent = appellant_name.find_next('td') if appellant_name else None
#             sol['respondent'] = clean_text(respondent.text) if respondent else ''
#             next_date = respondent.find_next('td') if respondent else None
#
#             next_dates = [k.text.strip() for k in next_date.find_all('span')] if next_date else []
#             date_objs = []
#             for d in next_dates:
#                 for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
#                     try:
#                         date_objs.append(datetime.strptime(d, fmt))
#                         break
#                     except ValueError:
#                         continue
#             latest_date = max(date_objs).strftime("%Y-%m-%d") if date_objs else ''
#             sol['next_hearning_date'] = latest_date
#
#             details = next_date.find_next('td') if next_date else None
#             sol['details'] = clean_text(details.text) if details else ''
#             orders = details.find_next('td') if details else None
#             sol['order_link'] = [k['href'] for k in orders.find_all('a')] if orders else []
#
#             results.append(sol)
#
#         if results:
#             write_log(state_type, case_no, status="Completed")
#             return jsonify({'result': results[0]})
#         else:
#             write_log(state_type, case_no, status="Failed", error_msg="No record found")
#             return jsonify({'message': 'no record found', 'result': ''})
#
#     except Exception as e:
#         err_msg = f"{str(e)} | Traceback: {traceback.format_exc().splitlines()[-1]}"
#         write_log(state_type, case_no, status="Failed", error_msg=err_msg)
#         return jsonify({'message': 'error occurred', 'error': str(e)})
#
# @cgit_blueprint.route('', methods=['GET'])
# def cgit_labour():
#     state_code = request.args.get('state_code')
#     case_no = request.args.get('case_no')
#     return main(state_code, case_no)
