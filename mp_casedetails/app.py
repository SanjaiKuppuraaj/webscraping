from flask import Blueprint, jsonify, request
from datetime import datetime
import os
import json
from mp_casedetails.case_details import url_parsing
from common_code import common_module as cm

mp_case_bp = Blueprint('mp_case_bp', __name__)
bench_map = {"01": "Jabalpur", "02": "Indore", "03": "Gwalior"}
# OUTPUT_DIR = os.path.join(cm.BASE_DIR_OUTPUTS, 'mp_casedetails')
today_str = datetime.now().strftime('%Y-%m-%d')
LOG_DIR = os.path.join(cm.BASE_DIR_LOGS, today_str)
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "mp_casedetails.txt")

def write_log(entry):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(f"{timestamp} {entry}\n")
    except PermissionError:
        print(f"Cannot write to log file: {LOG_FILE}. Check permissions.")

@mp_case_bp.route('')
def casedetails():
    bench = request.args.get('bench')
    case_type = request.args.get('case_type')
    case_no = request.args.get('case_no')
    case_year = request.args.get('case_year')

    bench_name = bench_map.get(bench, "Unknown")

    if not all([bench, case_type, case_no, case_year]):
        msg = "Missing required parameters"
        write_log(f"{bench_name}/{case_type}/{case_no}/{case_year} | status: Error - {msg}")
        return jsonify({"error": msg}), 400

    if bench not in bench_map:
        msg = "Invalid bench code"
        write_log(f"{bench_name}/{case_type}/{case_no}/{case_year} | status: Error - {msg}")
        return jsonify({"error": f"{msg}. Allowed: {list(bench_map.keys())}"}), 400

    bench_name = bench_map[bench]
    filename = f"{bench_name}_{case_type}_{case_no}_{case_year}.json"
    # filepath = os.path.join(OUTPUT_DIR, filename)

    try:
        # os.makedirs(OUTPUT_DIR, exist_ok=True)
        result = url_parsing(bench, case_type, case_no, case_year)

        if result.get("status") == "Result not Found":
            write_log(f"{bench_name}/{case_type}/{case_no}/{case_year} | status: Error - Result not Found")
            return jsonify({"error": "Case result not found"}), 404

        # with open(filepath, "w", encoding="utf-8") as f:
        #     json.dump({'result': result}, f, ensure_ascii=False, indent=4)

        write_log(f"{bench_name}/{case_type}/{case_no}/{case_year} | status: Completed")
        return jsonify({'result': result})

    except PermissionError as pe:
        write_log(f"{bench_name}/{case_type}/{case_no}/{case_year} | status: Error - Permission denied: {str(pe)}")
        return jsonify({"error": "Permission denied. Check write access to output directory."}), 500

    except Exception as e:
        write_log(f"{bench_name}/{case_type}/{case_no}/{case_year} | status: Error - {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500
