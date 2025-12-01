from flask import Blueprint, request, jsonify
from .causelist_hcb import generate_causelist
import traceback
import os
from datetime import datetime
from common_code import common_module as cm

hcb_blueprint = Blueprint("hcb_blueprint", __name__)
LOG_FILE =  cm.BASE_DIR_LOGS + '/'+datetime.now().strftime('%Y-%m-%d')+"/hcb_cause_list_log.txt"
def write_log(bench, side, date, status):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{now} - {bench}/{side}/{date} | status : {status}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)

@hcb_blueprint.route("")
def hcb_causelist():
    bench = request.args.get("bench")
    side = request.args.get("side")
    date = request.args.get("date")
    if not bench or not side or not date:
        write_log(bench or "-", side or "-", date or "-", "error")
        return jsonify({"result": "error", "message": "No Record Found."})
    try:
        file_path = generate_causelist(bench, side, date)
        if file_path and os.path.exists(file_path):
            write_log(bench, side, date, "completed")
            return jsonify({"status": "success", "message": "Downloaded successfully!"}), 200
        else:
            write_log(bench, side, date, "error")
            return jsonify({"result": "error", "message": "No Record Found."}), 500
    except Exception as e:
        traceback.print_exc()
        write_log(bench, side, date, "error")
        return jsonify({"result": "error", "message": "No Record Found."}), 500