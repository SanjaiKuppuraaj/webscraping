from flask import Flask, request, jsonify, abort,Blueprint
import os
import concurrent.futures
# import orjson  # pip install orjson
import json
from common_code import common_module as cm

app = Flask(__name__)
kerala_causelist_bp = Blueprint('kerala_causlist','__name__')

def process_file(file_path):
    try:
        with open(file_path, "rb") as f:
            file_json = json.loads(f.read())
    except Exception:
        return None  # skip invalid JSON

    district_name = file_json.get("district_name", "Unknown")
    district_total_cases = 0

    for court_entry in file_json.get("data", []):
        case_count = sum(len(category.get("clist", []))
                         for result in court_entry.get("results", [])
                         for category in result.get("categories", []))
        district_total_cases += case_count

    return district_name, file_json.get("data", []), district_total_cases

# @app.route("/kerala_causelist")
@kerala_causelist_bp.route('/kerala_causelist')
def kerala_causelist():
    date_value = request.args.get("date")
    if not date_value:
        return jsonify({"error": "Missing 'date' query parameter"}), 400

    output_dir = os.path.join(cm.BASE_DIR_OUTPUTS, "kerala_causelist", date_value)
    if not os.path.exists(output_dir):
        abort(404, description=f"No folder found for date {date_value}")

    combined_data = {
        "scraped_date": date_value,
        "result": [],
        "total_cases": 0
    }

    district_map = {}
    files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".json")]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_file, files))

    for res in results:
        if res is None:
            continue
        district_name, data, district_total_cases = res
        if district_name not in district_map:
            district_map[district_name] = {
                "data": [],
                "district_total_cases": 0
            }
        district_map[district_name]["data"].extend(data)
        district_map[district_name]["district_total_cases"] += district_total_cases
        combined_data["total_cases"] += district_total_cases

    for district_name, info in district_map.items():
        combined_data["result"].append({
            "district_name": district_name,
            "data": info["data"],
            "district_total_cases": info["district_total_cases"]
        })

    if not combined_data["result"]:
        return jsonify({"message": f"No valid JSON files found for date {date_value}"}), 200

    return jsonify(combined_data), 200

# if __name__ == "__main__":
#     app.run(debug=True)
