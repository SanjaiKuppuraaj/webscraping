from flask import Blueprint, request, jsonify, send_file
from playwright.sync_api import sync_playwright
import os
import base64
from datetime import datetime
from common_code import common_module as cm
import logging
import sys
from io import BytesIO

consumer_forum = Blueprint('consumer_forum', __name__)

# Setup logging
LOG_DIR = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, 'consumer_order_debug.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8')]
)

sys.stdout = open(LOG_FILE, 'a', encoding='utf-8')
sys.stderr = open(LOG_FILE, 'a', encoding='utf-8')

BASE_DIR = os.path.join(LOG_DIR, 'consumer_order_log.txt')


def log_entry(case_number, status, reason=None):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    message = f"{timestamp} - {case_number} | Status: {status} | IP: {client_ip}"
    if reason:
        message += f" - Reason: {reason}"

    with open(BASE_DIR, 'a', encoding='utf-8') as log_file:
        log_file.write(message + '\n')
    logging.info(message)

def create_no_order_pdf():
    return BytesIO(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
                   b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
                   b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                   b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
                   b"4 0 obj\n<< /Length 50 >>\nstream\nBT /F1 14 Tf 70 820 Td (No Order Found) Tj ET\n"
                   b"endstream\nendobj\n"
                   b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
                   b"xref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000061 00000 n "
                   b"0000000116 00000 n \n0000000270 00000 n \n0000000382 00000 n \n"
                   b"trailer\n<< /Root 1 0 R /Size 6 >>\nstartxref\n463\n%%EOF")


@consumer_forum.route('')
def view_pdf():
    case_number = request.args.get('caseNumber')
    fillingReferenceNumber = request.args.get('fillingReferenceNumber')
    date_of_hearing = request.args.get('dateOfHearing')
    order_type_id = request.args.get('orderTypeId')

    if not (case_number or fillingReferenceNumber) or not date_of_hearing:
        log_entry(case_number or fillingReferenceNumber or "UNKNOWN", "Error", "Missing parameters")
        filename = f"{(case_number or fillingReferenceNumber or 'UNKNOWN').replace('/', '_')}_{date_of_hearing or 'NA'}.pdf"
        return send_file(create_no_order_pdf(), mimetype='application/pdf', as_attachment=True, download_name=filename)

    if fillingReferenceNumber:
        url = f"https://e-jagriti.gov.in/services/courtmaster/courtRoom/judgement/v1/getDailyOrderJudgementPdf?filingReferenceNumber={fillingReferenceNumber}&dateOfHearing={date_of_hearing}&orderTypeId={order_type_id}"
    elif case_number:
        url = f"https://e-jagriti.gov.in/services/courtmaster/courtRoom/judgement/v1/getDailyOrderJudgementPdf?caseNumber={case_number}&dateOfHearing={date_of_hearing}&orderTypeId={order_type_id}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, proxy={'server': cm.get_proxy()} if cm.USE_PROXY else None)
            context = browser.new_context()
            page = context.new_page()

            response = page.request.get(url)
            if response.status != 200:
                log_entry(case_number or fillingReferenceNumber, "Error", "No Record Found")
                filename = f"{(case_number or fillingReferenceNumber).replace('/', '_')}_{date_of_hearing}.pdf"
                return send_file(create_no_order_pdf(), mimetype='application/pdf', as_attachment=True, download_name=filename)

            data = response.json()
            pdf_base64 = data['data'].get('dailyOrderPdf')
            if not pdf_base64:
                log_entry(case_number or fillingReferenceNumber, "Error", "PDF data missing")
                filename = f"{(case_number or fillingReferenceNumber).replace('/', '_')}_{date_of_hearing}.pdf"
                return send_file(create_no_order_pdf(), mimetype='application/pdf', as_attachment=True, download_name=filename)

            pdf_bytes = base64.b64decode(pdf_base64)
            filename = f"{(case_number or fillingReferenceNumber).replace('/', '_')}_{date_of_hearing}.pdf"
            log_entry(case_number or fillingReferenceNumber, "Completed")
            return send_file(BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, download_name=filename)

    except Exception as e:
        log_entry(case_number or fillingReferenceNumber, "Error", str(e))
        logging.exception("Exception in view_pdf")
        filename = f"{(case_number or fillingReferenceNumber or 'UNKNOWN').replace('/', '_')}_{date_of_hearing or 'NA'}.pdf"
        return send_file(create_no_order_pdf(), mimetype='application/pdf', as_attachment=True, download_name=filename)


# Example usage:
# http://localhost/consumer_forum?caseNumber=NC/CC/3009/2017&dateOfHearing=2025-08-18
# http://localhost/consumer_forum?fillingReferenceNumber=100000136888&dateOfHearing=2025-08-18&orderTypeId=1







# from flask import Blueprint, request, send_file
# from playwright.sync_api import sync_playwright
# import os
# import base64
# from datetime import datetime
# from common_code import common_module as cm
# import logging
# import sys
# from io import BytesIO
# import requests
#
# consumer_forum = Blueprint('consumer_forum', __name__)
#
# LOG_DIR = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
# os.makedirs(LOG_DIR, exist_ok=True)
#
# LOG_FILE = os.path.join(LOG_DIR, 'consumer_order_debug.log')
#
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s %(levelname)s %(message)s',
#     handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8')]
# )
#
# sys.stdout = open(LOG_FILE, 'a', encoding='utf-8')
# sys.stderr = open(LOG_FILE, 'a', encoding='utf-8')
#
# BASE_DIR = os.path.join(LOG_DIR, 'consumer_order_log.txt')
#
#
# def log_entry(case_number, status, reason=None):
#     timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#     client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
#     message = f"{timestamp} - {case_number} | Status: {status} | IP: {client_ip}"
#     if reason:
#         message += f" - Reason: {reason}"
#     with open(BASE_DIR, 'a', encoding='utf-8') as log_file:
#         log_file.write(message + '\n')
#     logging.info(message)
#
#
# def create_no_order_pdf():
#     return BytesIO(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
#                    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
#                    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
#                    b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
#                    b"4 0 obj\n<< /Length 50 >>\nstream\nBT /F1 14 Tf 70 820 Td (No Order Found) Tj ET\n"
#                    b"endstream\nendobj\n"
#                    b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
#                    b"xref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000061 00000 n "
#                    b"0000000116 00000 n \n0000000270 00000 n \n0000000382 00000 n \n"
#                    b"trailer\n<< /Root 1 0 R /Size 6 >>\nstartxref\n463\n%%EOF")
#
#
# @consumer_forum.route('')
# def view_pdf():
#     case_number = (request.args.get('caseNumber') or '').strip()
#     fillingReferenceNumber = (request.args.get('fillingReferenceNumber') or '').strip()
#     date_of_hearing = (request.args.get('dateOfHearing') or '').strip()
#     order_type_id = request.args.get('orderTypeId')
#
#     if case_number:
#         case_number = case_number.upper()
#
#     if not (case_number or fillingReferenceNumber) or not date_of_hearing:
#         log_entry(case_number or fillingReferenceNumber or "UNKNOWN", "Error", "Missing parameters")
#         filename = f"{(case_number or fillingReferenceNumber or 'UNKNOWN').replace('/', '_')}_{date_of_hearing or 'NA'}.pdf"
#         return send_file(create_no_order_pdf(), mimetype='application/pdf', as_attachment=True, download_name=filename)
#
#     try:
#         if case_number and not fillingReferenceNumber:
#             try:
#                 status_url = f"https://e-jagriti.gov.in/services/case/caseFilingService/v2/getCaseStatus?caseNumber={case_number}"
#                 headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'}
#                 resp = requests.get(status_url, headers=headers, timeout=15)
#                 if resp.status_code == 200:
#                     data = resp.json().get('data')
#                     if data and 'fillingReferenceNumber' in data:
#                         fillingReferenceNumber = data['fillingReferenceNumber']
#                         log_entry(case_number, "Info", f"Got fillingReferenceNumber: {fillingReferenceNumber}")
#                     else:
#                         log_entry(case_number, "Error", "fillingReferenceNumber not found in API response")
#                 else:
#                     log_entry(case_number, "Error", f"getCaseStatus returned {resp.status_code}")
#             except Exception as e:
#                 log_entry(case_number, "Error", f"Fetching fillingReferenceNumber failed: {e}")
#
#         if not fillingReferenceNumber:
#             log_entry(case_number or "UNKNOWN", "Error", "No fillingReferenceNumber found")
#             filename = f"{(case_number or 'UNKNOWN').replace('/', '_')}_{date_of_hearing}.pdf"
#             return send_file(create_no_order_pdf(), mimetype='application/pdf', as_attachment=True, download_name=filename)
#
#         url = f"https://e-jagriti.gov.in/services/courtmaster/courtRoom/judgement/v1/getDailyOrderJudgementPdf?filingReferenceNumber={fillingReferenceNumber}&dateOfHearing={date_of_hearing}&orderTypeId={order_type_id}"
#
#         with sync_playwright() as p:
#             browser = p.chromium.launch(headless=True, proxy={'server': cm.get_proxy()} if cm.USE_PROXY else None)
#             context = browser.new_context()
#             page = context.new_page()
#
#             response = page.request.get(url)
#             if response.status != 200:
#                 log_entry(case_number or fillingReferenceNumber, "Error", "No Record Found")
#                 filename = f"{(case_number or fillingReferenceNumber).replace('/', '_')}_{date_of_hearing}.pdf"
#                 return send_file(create_no_order_pdf(), mimetype='application/pdf', as_attachment=True, download_name=filename)
#
#             data = response.json()
#             pdf_base64 = data['data'].get('dailyOrderPdf')
#             if not pdf_base64:
#                 log_entry(case_number or fillingReferenceNumber, "Error", "PDF data missing")
#                 filename = f"{(case_number or fillingReferenceNumber).replace('/', '_')}_{date_of_hearing}.pdf"
#                 return send_file(create_no_order_pdf(), mimetype='application/pdf', as_attachment=True, download_name=filename)
#
#             pdf_bytes = base64.b64decode(pdf_base64)
#             filename = f"{(case_number or fillingReferenceNumber).replace('/', '_')}_{date_of_hearing}.pdf"
#             log_entry(case_number or fillingReferenceNumber, "Completed")
#             return send_file(BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, download_name=filename)
#
#     except Exception as e:
#         log_entry(case_number or fillingReferenceNumber, "Error", str(e))
#         logging.exception("Exception in view_pdf")
#         filename = f"{(case_number or fillingReferenceNumber or 'UNKNOWN').replace('/', '_')}_{date_of_hearing or 'NA'}.pdf"
#         return send_file(create_no_order_pdf(), mimetype='application/pdf', as_attachment=True, download_name=filename)
#
#
# # Example URLs
# # http://localhost/consumer_forum?caseNumber=nc/cc/3009/2017&fillingReferenceNumber=&dateOfHearing=2025-08-18&orderTypeId=1
# # http://localhostorderType/consumer_forum?fillingReferenceNumber=100000136888&caseNumber=&dateOfHearing=2025-08-18&Id=1
#
#
