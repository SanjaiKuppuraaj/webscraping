import sys
from flask import Flask
import common_code.common_module as cm

sys.dont_write_bytecode = True
cm.USE_PROXY = False
app = Flask(__name__)

blueprint_configs = {
    'ksat': ('ksat_flask.app', 'ksat_blueprint', '/tribunal_ksat_casestatus'),
    'mptribunal': ('mp_atribunal.app', 'mp_blueprint', '/mptribunal'),
    'mptribunal_order': ('mp_atribunal.mp_awards', 'mpaward_blueprint', '/mptribunal_order'),
    'mporders': ('mp_causelist.app', 'mp_causelist_blueprint', '/mporders'),
    'hc_bombay': ('bombay_hc.app', 'bombay_hc_blueprint', '/hc_bombay'),
    'hcb_causelist': ('hcb_cause_list.app', 'hcb_blueprint', '/hcb_causelist'),
    'ecourt': ('ecourt.app', 'ecourt_blueprint', '/ecourt'),
    'pdf_to_text': ('pdf_to_text.app', 'pdf_to_text_blueprint', '/pdf_to_text'),
    'consumer_forum' : ('consumer_forum.app','consumer_forum','/consumer_forum'),
    'proxy_browser': ('proxy_browser_playwright.proxy_browser', 'fetcher_blueprint', '/proxy_browser'),
    'proxy_browser_playwright': ('proxy_browser_playwright.proxy_playwright', 'proxy_blueprint', '/proxy_browser_playwright'),
    'html_to_excel': ('html_to_excel.app', 'html_to_excel_bp', '/html_to_excel'),
    # 'aptel': ('aptel.app','aptel_blueprint','/aptel'),
    'hcmp_causelist': ('hcmp_causelist.app', 'mp_causelist_blueprint', '/mp_causelist'),
    'mp_casestatus': ('hcmp_casestatus.app', 'mp_casestatus_bp', '/mp_casestatus'),
    'mpcauselist': ('mp_causelist_terminal.app', 'mpcauselist_bp', '/mpcauselist'), #crontab
    'mp_casedetails' : ('mp_casedetails.app','mp_case_bp','/mp_casedetails'),
    'delhi_causelist' : ('hc_delhi.app','delhi_cause_bp','/delhi_causelist'),
    'supreme_court' : ('new_supreme_causelist.supreme_courtdata', 'supreme_blueprint','/supreme_court'),
    'delhi_status': ('delhi_casestatus.delhi_status', 'delhi_status_bp', '/delhi_status'),
    'greentribunal' : ('greentribunal.new_ngt','ngt_case_bp',''),
    'rera_case': ('rera_haryana.rera_scrape', 'rera_bp', '/rera_case'),
    'kerala_efiling' : ('kerala_efiling.efiling_kerala','kerala_bp','/kerala'),
    'kat': ('kat.app', 'kat_bp', ''),
    'aptel': ('aptel.new_aptel', 'aptel_bp', '/aptel'),
    'gujarat': ('gujarat_causelist.gujarat_causelist', 'gujarat_bp', '/gujarat_causelist'),
    'supreme_case_details':('supreme_case_details.app','supreme_case_bp','/supreme_case_details'),
    'cgit_ecourt': ('cgit_labour.cgit_labour_flask', 'cgit_blueprint', '/cgit_labor'),
    'madras_causelist' : ('madras_causelist.madras_causelist','madras_bp','/madras_causelist'),
    'rct_rail': ('rct_india.rct_railway', 'rct_rail_bp', '/rct_rail'),
    'kerala_causelist' : ('kerala_causelist.kerala_flask','kerala_causelist_bp',''),
    'karantaka_display_board': ('display_board.karnataka_disp_board', 'display_board_bp', '/karantaka_display_board'),
    'delhi_diplay_board': ('display_board.delhi_disp_board', 'delhi_bp', '/delhi_display_board'),
    "service_ecourt": ('servie_ecourt.causelist_crontab', 'district_bp', ''),
    'ecourt_flask': ('servie_ecourt.service_ecourt_flask', 'ecourt_bp', ''),

}

for name, (module_path, blueprint_var, url_prefix) in blueprint_configs.items():
    try:
        module = __import__(module_path, fromlist=[blueprint_var])
        blueprint = getattr(module, blueprint_var)
        app.register_blueprint(blueprint, url_prefix=url_prefix)
    except Exception as e:
        print(f"Failed to register {name}: {e}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)