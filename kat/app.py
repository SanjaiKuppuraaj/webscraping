import json
from flask import Flask, jsonify, request, Blueprint, send_file
from datetime import datetime
from common_code import common_module as cm
import os
from kat.kat import main

kat_bp = Blueprint('kat_bp', __name__)


@kat_bp.route('/tribunal_kat_casestatus', methods=['GET'])
def kst_detail():
    types = request.args.get('case_type')
    caseno = request.args.get('case_no')
    case_year = request.args.get('case_year')

    if not (types and caseno and case_year and case_year.isdigit() and len(case_year) == 4):
        return jsonify({"result": "error", "message": "Invalid or missing parameters."}), 400

    filename = f"{types}_{caseno}_{case_year}.json"
    output_dir = os.path.join(cm.BASE_DIR_OUTPUTS, 'kat')
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    log_file = cm.BASE_DIR_LOGS + '/' + datetime.now().strftime('%Y-%m-%d') + '/kst_log.txt'
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"{now} | {types}_{caseno}_{case_year} | "

    try:
        data = main(types, caseno, case_year)
        if not data or (
                isinstance(data, dict) and data.get("result") == "error" and data.get("message") == "No Record Found."):
            with open(log_file, 'a') as log:
                log.write(log_entry + "Status: Error | Message: No Record Found\n")
            return jsonify({"result": "error", "message": "No Record Found."}), 404

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=3)

        with open(log_file, 'a') as log:
            log.write(log_entry + "Status: Completed\n")
        return jsonify(data), 200

    except Exception as e:
        with open(log_file, 'a') as log:
            log.write(log_entry + f"Status: Error | Message: {str(e)}\n")
        return jsonify({"result": "error", "message": "Something went wrong processing your request."}), 500

@kat_bp.route('/tribunal_kat_casestatus/download/<appid>', methods=['GET'])
def pdf_link(appid):
    directory = os.path.join(cm.BASE_DIR_OUTPUTS, 'kat', 'downloads')
    filename = f"{appid}.pdf"
    filepath = os.path.join(directory, filename)

    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return jsonify({"result": "error", "message": "PDF file not found."}), 404
















# import json
# from flask import Flask, jsonify, request, Blueprint
# from datetime import datetime
# from kat.kat import main
# from common_code import common_module as cm
# import os
#
# kat_bp = Blueprint('kat_bp', __name__)
#
# @kat_bp.route('', methods=['GET'])
# def kst_detail():
#     types = request.args.get('case_type')
#     caseno = request.args.get('case_no')
#     case_year = request.args.get('case_year')
#
#     if not (types and caseno and case_year and case_year.isdigit() and len(case_year) == 4):
#         return jsonify({"result": "error", "message": "Invalid or missing parameters."}), 400
#
#     filename = f"{types}_{caseno}_{case_year}.json"
#     output_dir = os.path.join(cm.BASE_DIR_OUTPUTS, 'kat')
#     os.makedirs(output_dir, exist_ok=True)
#     filepath = os.path.join(output_dir, filename)
#     # log_file = '/home/jbk/python_code/kat/kst_log.txt'
#     log_file = cm.BASE_DIR_LOGS + '/'+datetime.now().strftime('%Y-%m-%d')+'/kst_log.txt'
#     now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#     log_entry = f"{now} | {types}_{caseno}_{case_year} | "
#
#     try:
#         data = main(types, caseno, case_year)
#         if not data or ( isinstance(data, dict) and data.get("result") == "error"and data.get("message") == "No Record Found."):
#             with open(log_file, 'a') as log:
#                 log.write(log_entry + "Status: Error | Message: No Record Found\n")
#             return jsonify({"result": "error", "message": "No Record Found."}), 404
#
#         with open(filepath, 'w') as f:
#             json.dump(data, f, indent=3)
#
#         with open(log_file, 'a') as log:
#             log.write(log_entry + "Status: Completed\n")
#         return jsonify(data), 200
#
#     except Exception as e:
#         with open(log_file, 'a') as log:
#             log.write(log_entry + f"Status: Error | Message: {str(e)}\n")
#         return jsonify({"result": "error", "message": "Something went wrong processing your request."}), 500
