from flask import Blueprint, request, render_template
from .hc_bombay import hc_bombay
from datetime import datetime
import time, os, json, sys
from common_code import common_module as cm

sys.dont_write_bytecode = True
bombay_hc_blueprint = Blueprint('bombay_hc', __name__, template_folder='templates')

@bombay_hc_blueprint.route("", methods=["GET", "POST"])
def scrape():
    start_time = time.time()
    m_hc = request.args.get("bench")
    m_sideflg = request.args.get("side")
    m_sr = request.args.get("stamp")
    m_skey = request.args.get("case_type")
    m_no = request.args.get("case_no")
    m_yr = request.args.get("case_year")
    mode = request.args.get("mode")

    if not all([m_hc, m_sideflg, m_sr, m_skey, m_no, m_yr, mode]):
        return render_template("index.html", error={"result": "error", "message": "No Record Found."})

    scraper = hc_bombay(m_hc, m_sideflg, m_sr, m_skey, m_no, m_yr)
    output = {}
    status = "Completed"
    try:

        if mode not in ["misc", "paper", "main", "all"]:
            output["error"] = "Invalid mode. Choose from: misc, paper, main, all"
        else:
            if mode in ["misc", "all"]:
                output["misc_info"] = scraper.misc_info()
            if mode in ["paper", "all"]:
                output["paper_case"] = scraper.paper_case()
            if mode in ["misc", "paper", "main", "all"]:
                output["main_info"] = scraper.case_main_info()
        # misc = {}
        # paper = {}
        # if mode == 'misc':
        #     misc = scraper.misc_info()
        #     output["misc_info"] = misc
        #
        # elif mode == 'paper':
        #     paper = scraper.paper_case()
        #     output["paper_case"] = paper
        #
        # elif mode == 'all':
        #     misc = scraper.misc_info()
        #     paper = scraper.paper_case()
        #     output["misc_info"] = misc
        #     output["paper_case"] = paper

        filename = f"{m_sideflg}_{m_sr}_{m_skey}_{m_no}_{m_yr}.json"
        save_dir = cm.BASE_DIR_OUTPUTS + '/bombay_hc'
        save_path = os.path.join(save_dir, filename)
        os.makedirs(save_dir, exist_ok=True)

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=4, ensure_ascii=False)
        except Exception as file_error:
            output["file_error"] = {"result": "error", "message": "No Record Found."}
            status = "Error"

    except Exception as e:
        status = "Error"

    try:
        log_dir = cm.BASE_DIR_LOGS + '/' + datetime.now().strftime('%Y-%m-%d') + '/'
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "high_court_bombay_log.txt")
        log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{log_time} - {m_hc}/{m_sideflg}/{m_sr}/{m_skey}/{m_no}/{m_yr}/{mode} | Status: {status}\n"
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(log_entry)
    except Exception as log_err:
        print(f"Logging Error: {log_err}")

    return render_template("index.html", case_data={'results': output})
