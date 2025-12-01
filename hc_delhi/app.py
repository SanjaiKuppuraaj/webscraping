from flask import Flask, jsonify, request, Blueprint
from datetime import datetime
import os
import json
from common_code import common_module as cm
from hc_delhi.delhi_scraper import get_causelist

app = Flask(__name__)
delhi_cause_bp = Blueprint('delhi_causelist', __name__)

def write_log(status, date):
    if status.lower() not in ['completed', 'error']:
        raise ValueError("Status must be 'completed' or 'error'")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{now} {date} | Status : {status.capitalize()}\n"
    log_dir = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, 'delhi_log.txt')
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(log_entry)

@delhi_cause_bp.route('', methods=['GET'])
def parsing():
    date = request.args.get('date')
    refresh = request.args.get('refresh', 'false').lower() == 'true'

    if not date:
        return jsonify({'result': 'error', 'message': 'Date parameter is required'}), 400

    try:
        datetime.strptime(date, '%d-%m-%Y')
        output_dir = os.path.join(cm.BASE_DIR_OUTPUTS, 'delhi_causelist')
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.join(output_dir, f"{date}.json")

        # refresh=false → only use cached file
        if not refresh:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                return jsonify(cached_data)
            else:
                return jsonify({'result': 'error', 'message': 'No Record Found'})

        # refresh=true → scrape fresh data
        datas = get_causelist(date_str=date, output_file=filename, refresh=True)

        if datas.get("success"):
            write_log("completed", date)
        if datas.get("failed"):
            write_log("error", date)

        if not datas.get("success"):
            return jsonify({'result': 'error', 'message': 'No Record Found'})

        return jsonify({'result': datas["success"], 'failed': datas.get("failed", [])})

    except ValueError:
        write_log("error", date)
        return jsonify({'result': 'error', 'message': 'Invalid date format. Use dd-mm-yyyy'}), 400
    except Exception as e:
        write_log("error", date if 'date' in locals() else 'unknown')
        return jsonify({'result': 'error', 'message': str(e)}), 500

app.register_blueprint(delhi_cause_bp, url_prefix='/delhi_causelist')

if __name__ == '__main__':
    app.run(debug=True)