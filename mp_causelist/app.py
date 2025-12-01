from flask import Flask, request, jsonify, render_template, Blueprint
from .mp_highcourt import fetch_case_data
import os
import json
from datetime import datetime
from common_code import common_module as cm

mp_causelist_blueprint = Blueprint('mp_causelist_blueprint', __name__)

@mp_causelist_blueprint.route('', methods=['GET', 'POST'])
def scrape_case():
    id_map = {'01': 'JBP','02': 'IND','03': 'GWL'}

    raw_case_id = request.args.get('bench')
    lst_case = request.args.get('case_type')
    txt_no = request.args.get('case_no')
    year = request.args.get('case_year')

    if not raw_case_id or not lst_case or not txt_no or not year:
        return jsonify({"result": "error", "message": "No Record Found."})

    case_id = id_map.get(raw_case_id.upper())
    if not case_id:
        return jsonify({"result": "error", "message": "No Record Found."})

    case_code = f"{case_id}/{lst_case}/{txt_no}/{year}"
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    log_dir = cm.BASE_DIR_LOGS + '/'+datetime.now().strftime('%Y-%m-%d')+'/'
    log_file_path = os.path.join(log_dir, "mpcauselist_log.txt")

    try:
        output = fetch_case_data(case_id, lst_case, txt_no, year)

        if not output or ("result" not in output) or not output["result"]:
            raise ValueError({"result": "error", "message": "No Record Found."})

        filename = f"{case_id}_{lst_case}_{txt_no}_{year}.json"
        json_dir = cm.BASE_DIR_OUTPUTS
        json_dir = os.path.join(json_dir, "mpcauselist_json")
        os.makedirs(json_dir, exist_ok=True)
        filepath = os.path.join(json_dir, filename)
        with open(filepath, 'w') as json_file:
            json.dump(output, json_file, indent=2)

        log_line = f"{now} - {case_code} | Status : Completed\n"
        with open(log_file_path, 'a') as log_file:
            log_file.write(log_line)

        return jsonify({"success": True, "message": "Records Found.", "results": output["result"]})

    except Exception as e:
        log_line = f"{now} - {case_code} | Status : Error\n"
        os.makedirs(log_dir, exist_ok=True)
        with open(log_file_path, 'a') as log_file:
            log_file.write(log_line)

        return jsonify({"result": "error", "message": "No Record Found."})
