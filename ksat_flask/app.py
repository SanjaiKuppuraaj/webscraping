import os
import json
from flask import Blueprint, request, jsonify
from collections import OrderedDict  # Import OrderedDict to maintain key order
from .ksat_case import Ksat_Scraper
from datetime import datetime
from common_code import common_module as cm

ksat_blueprint = Blueprint('ksat', __name__)

def log_message(message):
    log_filename = cm.BASE_DIR_LOGS + '/' + datetime.now().strftime('%Y-%m-%d') + '/ksat_log.txt'
    os.makedirs(os.path.dirname(log_filename), exist_ok=True)  # make sure log dir exists
    with open(log_filename, 'a', encoding='utf-8') as log_file:
        log_file.write(f"{message}\n")

def ensure_json_folder_and_write(save_folder, filename, case_data, establishcode, apptype, case_num, case_year):
    try:
        if not os.path.exists(save_folder):
            os.makedirs(save_folder, exist_ok=True)
            os.chmod(save_folder, 0o777)

        if not os.access(save_folder, os.W_OK):
            raise PermissionError("Output folder not writable.")

        if not case_data or "case_status" not in case_data:
            raise ValueError("No valid case data found.")

        file_path = os.path.join(save_folder, filename)
        with open(file_path, 'w', encoding='utf-8') as json_file:
            json.dump({"result": case_data}, json_file, indent=4, ensure_ascii=False)

        log_message(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {establishcode}/{apptype}/{case_num}/{case_year} | Status : Completed"
        )

    except Exception as e:
        log_message(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {establishcode}/{apptype}/{case_num}/{case_year} | Status : Error - {str(e)}"
        )
        raise

@ksat_blueprint.route('')
def case_details():
    establishcode = request.args.get('bench')
    apptype = request.args.get('case_type')
    case_num = request.args.get('case_no')
    case_year = request.args.get('case_year')

    if not all([establishcode, apptype, case_num, case_year]):
        error_message = "No Record Found."
        log_message(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {establishcode}/{apptype}/{case_num}/{case_year} | Status : Error - {error_message}"
        )
        error_response = OrderedDict([('result', 'error'), ('message', error_message)])
        return jsonify(error_response)

    try:
        scraper = Ksat_Scraper(establishcode, apptype, case_num, case_year)
        scraper.datas()
        case_data = scraper.result_datas

        if not case_data or "case_status" not in case_data:
            error_message = "No Record Found."
            log_message(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {establishcode}/{apptype}/{case_num}/{case_year} | Status : Error - {error_message}"
            )
            error_response = OrderedDict([('result', 'error'), ('message', error_message)])
            return jsonify(error_response)

        save_folder = cm.BASE_DIR_OUTPUTS + '/ksat'
        filename = f"{establishcode}_{apptype}_{case_num}_{case_year}.json"

        ensure_json_folder_and_write(save_folder, filename, case_data, establishcode, apptype, case_num, case_year)

        return jsonify({"result": case_data})

    except ValueError:
        error_message = "No Record Found."
        log_message(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {establishcode}/{apptype}/{case_num}/{case_year} | Status : Error - {error_message}"
        )
        error_response = OrderedDict([('result', 'error'), ('message', error_message)])
        return jsonify(error_response)

    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        log_message(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {establishcode}/{apptype}/{case_num}/{case_year} | Status : Error - {error_message}"
        )
        error_response = OrderedDict([('result', 'error'), ('message', "No Record Found.")])
        return jsonify(error_response)

























# import os
# import json
# from flask import Blueprint, render_template, request
# from collections import OrderedDict  # Import OrderedDict to maintain key order
# from .ksat_case import Ksat_Scraper
# from datetime import datetime
# from common_code import common_module as cm
#
# ksat_blueprint = Blueprint('ksat', __name__, template_folder='templates')
# def log_message(message):
#     log_filename = cm.BASE_DIR_LOGS + '/'+datetime.now().strftime('%Y-%m-%d')+'/ksat_log.txt'
#     with open(log_filename, 'a', encoding='utf-8') as log_file:
#         log_file.write(f"{message}\n")
#
# def ensure_json_folder_and_write(save_folder, filename, case_data, establishcode, apptype, case_num, case_year):
#     try:
#         if not os.path.exists(save_folder):
#             os.makedirs(save_folder, exist_ok=True)
#             os.chmod(save_folder, 0o777)
#         if not os.access(save_folder, os.W_OK):
#             raise PermissionError({"result": "error", "message": "No Record Found."})
#
#         if not case_data or "case_status" not in case_data:
#             raise ValueError("No valid case data found.")
#
#         file_path = os.path.join(save_folder, filename)
#         with open(file_path, 'w', encoding='utf-8') as json_file:
#             json.dump({"result": case_data}, json_file, indent=4, ensure_ascii=False)
#         log_message(
#             f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {establishcode}/{apptype}/{case_num}/{case_year} | Status : Completed")
#
#     except Exception as e:
#         log_message(
#             f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {establishcode}/{apptype}/{case_num}/{case_year} | Status : Error - {str(e)}")
#         raise
#
# @ksat_blueprint.route('')
# def case_details():
#     establishcode = request.args.get('bench')
#     apptype = request.args.get('case_type')
#     case_num = request.args.get('case_no')
#     case_year = request.args.get('case_year')
#
#     if not all([establishcode, apptype, case_num, case_year]):
#         error_message = "No Record Found."
#         log_message(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {establishcode}/{apptype}/{case_num}/{case_year} | Status : Error - {error_message}")
#         error_response = OrderedDict([('result', 'error'), ('message', error_message)])
#         return render_template("index.html", case_data=error_response)
#
#     try:
#         scraper = Ksat_Scraper(establishcode, apptype, case_num, case_year)
#         scraper.datas()
#         case_data = scraper.result_datas
#
#         if not case_data or "case_status" not in case_data:
#             error_message = "No Record Found."
#             log_message(
#                 f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {establishcode}/{apptype}/{case_num}/{case_year} | Status : Error - {error_message}")
#
#             error_response = OrderedDict([('result', 'error'), ('message', error_message)])
#             return render_template("index.html", case_data=error_response)
#
#         save_folder = cm.BASE_DIR_OUTPUTS + '/ksat'
#         filename = f"{establishcode}_{apptype}_{case_num}_{case_year}.json"
#
#         ensure_json_folder_and_write(save_folder, filename, case_data, establishcode, apptype, case_num, case_year)
#         return render_template("index.html", case_data={'result': case_data})
#     except ValueError as ve:
#         error_message = "No Record Found."
#         log_message(
#             f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {establishcode}/{apptype}/{case_num}/{case_year} | Status : Error - {error_message}")
#         error_response = OrderedDict([('result', 'error'), ('message', error_message)])
#         return render_template("index.html", case_data=error_response, time_taken=0)
#
#     except Exception as e:
#         error_message = "No Record Found."
#         log_message(
#             f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {establishcode}/{apptype}/{case_num}/{case_year} | Status : Error - {error_message}")
#         error_response = OrderedDict([('result', 'error'), ('message', error_message)])
#         return render_template("index.html", case_data=error_response, time_taken=0)