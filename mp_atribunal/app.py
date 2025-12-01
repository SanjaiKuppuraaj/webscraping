import re
import json
import os
from datetime import datetime
from flask import Blueprint, request, Response
from .mp_atribunals import mp_atribunal

from common_code import common_module as cm

import sys
sys.dont_write_bytecode = True

mp_blueprint = Blueprint('mp_blueprint', __name__)


def log_case_activity(case_number, status):
    log_dir = cm.BASE_DIR_LOGS + '/'+datetime.now().strftime('%Y-%m-%d')+'/'
    log_file = os.path.join(log_dir, 'mp_atribunal_logs.txt')
    time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message = f"{time_now} | Case: {case_number} | Status: {status}\n"

    try:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        with open(log_file, 'a') as log:
            log.write(message)
    except Exception as e:
        print(f"Failed to write log: {e}")


def validate_case_number(case_number):
    pattern = r"^[A-Za-z]+-?\s*\d+/\d{4}$"
    return bool(re.match(pattern, case_number))


def sanitize_filename(case_number):
    cleaned = re.sub(r'[\s\-]+', '_', case_number)
    cleaned = cleaned.replace('/', '_')
    return cleaned.upper() + ".json"


@mp_blueprint.route('')
def mp_case_details():
    case_number = request.args.get('case_number')

    if not case_number:
        log_case_activity("UNKNOWN", "Error - Missing case number")
        return Response(json.dumps({"result": "error", "message": "No Record Found."}), mimetype='application/json')

    if not validate_case_number(case_number):
        error_message = "Invalid case number format. Ensure it follows the pattern 'RC-115/2018' or 'RC 115/2018'."
        log_case_activity(case_number, f"Error - {error_message}")
        return Response(json.dumps({"result": "error", "message": "No Record Found."}), mimetype='application/json')

    json_dir = cm.BASE_DIR_OUTPUTS + '/mp_atribunal'
    json_filename = sanitize_filename(case_number)
    json_path = os.path.join(json_dir, json_filename)

    scraper = mp_atribunal(case_number)
    case_data = scraper.get_case_data()

    if "error" in case_data:
        log_case_activity(case_number, f"Error - {case_data['error']}")
        return Response(json.dumps({"result": "error", "message": "No Record Found."}), mimetype='application/json')

    try:
        if not os.path.exists(json_dir):
            os.makedirs(json_dir)

        if not case_data.get("results"):
            log_case_activity(case_number, "Error - No record found")
            return Response(json.dumps({"result": "error", "message": "No Record Found."}), mimetype='application/json')

        final_data = {"result": case_data["results"]}

        with open(json_path, 'w') as f:
            json.dump(final_data, f, indent=4)

        log_case_activity(case_number, "Completed")
        return Response(json.dumps(final_data), mimetype='application/json')

    except Exception as e:
        error_msg = "No Record Found."
        log_case_activity(case_number, f"Error - {error_msg}")
        return Response(json.dumps({"result": "error", "message": error_msg}), mimetype='application/json')

