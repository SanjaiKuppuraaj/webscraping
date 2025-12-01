from flask import Blueprint, request, jsonify
from common_code import mysql_common
from datetime import datetime

district_bp = Blueprint("district", __name__)

@district_bp.route("/district_causelist", methods=["GET"])
def fetch_court_data_route():
    date_input = request.args.get("date")
    if not date_input:
        return jsonify({"status": "error", "message": "date is required"}), 400

    try:
        causelist_date = datetime.strptime(date_input, "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format, use dd-mm-yyyy"}), 400

    filters = {
        "state_code": request.args.get("state_code", type=int),
        "district_code": request.args.get("district_code", type=int),
        "complex_code": request.args.get("complex_code", type=int),
        "est_code": request.args.get("est_code", type=int),
        "judge_id": request.args.get("judge_id", type=int),
        "causelist_date": causelist_date
    }

    conn = mysql_common.get_conn()
    with mysql_common.get_cursor(conn) as cursor:
        where_clause = ["causelist_date=%s"]
        params = [filters["causelist_date"]]

        for key in ["state_code", "district_code", "complex_code", "est_code", "judge_id"]:
            value = filters[key]
            if value not in (None, ""):
                where_clause.append(f"{key}=%s")
                params.append(value)

        sql = f"SELECT * FROM district_court_causelist WHERE {' AND '.join(where_clause)}"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        data_rows = [dict(zip(columns, row)) for row in rows]

    if not data_rows:
        final_json = {
            "status": "success",
            "message": "No record found"}
        conn.close()
        return jsonify(final_json)

    state_name = data_rows[0]["state_name"]
    state_code = str(data_rows[0]["state_code"])

    complex_dict = {}

    for row in data_rows:
        complex_key = (
            row["complex_code"],
            row["est_code"],
            row["judge_id"]
        )

        if complex_key not in complex_dict:
            complex_dict[complex_key] = {
                "district_name": row["district_name"],
                "district_code": str(row["district_code"]),
                "complex_name": row["complex_name"],
                "complex_code": row["complex_code"],
                "est_code": row["est_code"],
                "judge_name": f"{row['judge_id']}:{row['judge_name']}",
                "court_hall_address": row["judge_designation"],
                "causelist_date": causelist_date,
                "court_hall_no": f"CR NO {row['judge_id']}",
                "note": "",
                "row_data": []
            }

        complex_dict[complex_key]["row_data"].append({
            "sno": row.get("sno"),
            "matter_type": row.get("matter_type"),
            "full_caseno": row.get("full_caseno"),
            "cnr_no": row.get("cnr_no"),
            "case_type": row.get("case_type"),
            "case_no": row.get("case_no"),
            "case_year": row.get("case_year"),
            "petitioner": row.get("petitioner"),
            "respondent": row.get("respondent"),
            "petitioner_advocate": row.get("petitioner_advocate"),
            "respondent_advocate": row.get("respondent_advocate"),
            'type': row.get('case_category')
        })
    for c in complex_dict.values():
        c["row_data"].sort(key=lambda x: int(x.get("sno") or 0))

    final_json = {
        "status": "success",
        "count": len(data_rows),
        "message": "Data fetch completed",
        "data": {
            "state": state_name,
            "state_code": state_code,
            "complexes": list(complex_dict.values())
        }
    }

    conn.close()
    return jsonify(final_json)

 # http://165.232.190.40/district_causelist?state_code=3&district_code=20&complex_code=1030210&est_code=&judge_id=&date=28-11-2025

