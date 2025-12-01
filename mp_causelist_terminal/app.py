from flask import Blueprint, request, jsonify
from mp_causelist_terminal.mp_manually import fetch_mp_causelist
# from mp_causelist_terminal.mp_causelist_bs4 import fetch_mp_causelist

mpcauselist_bp = Blueprint("mpcauselist", __name__)

@mpcauselist_bp.route("")
def causelist_route():
    date = request.args.get("date")
    bench = request.args.get("bench")
    refresh = request.args.get("refresh", "false").lower() == "true"

    if not date or not bench:
        return jsonify({"success": False, "message": "Missing date or bench params"})

    result = fetch_mp_causelist(date, bench, refresh)
    if result.get("error"):
        return jsonify({"success": False, "message": result["message"]})

    count = sum(len(item.get("clist", [])) for item in result.get("results", []))

    return jsonify({"success": True,"message": "Record Found.","data_count": count,"results": result["results"] })












# from flask import Blueprint, request, jsonify
# # from mp_causelist_terminal.mp_manually import fetch_mp_causelist
# from mp_causelist_terminal.mp_causelist_bs4 import fetch_mp_causelist
#
# mpcauselist_bp = Blueprint("mpcauselist", __name__)
#
# @mpcauselist_bp.route("")
# def causelist_route():
#     date = request.args.get("date")
#     bench = request.args.get("bench")
#     refresh = request.args.get("refresh", "false").lower() == "true"
#
#     if not date or not bench:
#         return jsonify({"success": False, "message": "Missing date or bench params"})
#
#     result = fetch_mp_causelist(date, bench, refresh)
#     if result.get("error"):
#         return jsonify({"success": False, "message": result["message"]})
#
#     count = sum(len(item.get("clist", [])) for item in result.get("results", []))
#
#     return jsonify({"success": True,"message": "Record Found.","data_count": count,"results": result["results"] })
