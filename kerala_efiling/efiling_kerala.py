import sys
sys.path.insert(0, '/var/www/mml_python_code')
import time
import re
import pytesseract
from datetime import datetime
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup as bs
from playwright.sync_api import sync_playwright
from flask import Blueprint, jsonify, request, Flask
from kerala_efiling.kerala_district import kerala_districts
from common_code import proxy_implement
from common_code import common_module as cm
import os

app = Flask(__name__)
prox = proxy_implement.get_playwright_proxy()
kerala_bp = Blueprint("kerala", __name__)
LOG_FILE = "kerala_e-filing.txt"


def write_log(cnr_no, district_name, court_id, status, captcha_attempts=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        dist_name = kerala_districts[district_name]['District Name']
        court_name = kerala_districts[district_name]['Courts'][court_id]
    except Exception:
        dist_name = district_name
        court_name = court_id

    log_dir = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, LOG_FILE)

    log_line = f"{now} | {cnr_no}/{dist_name}/{court_name} | status: {status}"
    if captcha_attempts is not None:
        log_line += f" | captcha_attempts: {captcha_attempts}"
    log_line += "\n"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_line)

# @app.route('/kerala', methods=['GET'])
@kerala_bp.route('', methods=['GET'])
def case_details():
    cnr_no = request.args.get("cnr_no")
    district_name = request.args.get("district")
    court_id = request.args.get("court")
    case_type = request.args.get("case_type")
    case_no = request.args.get("case_no")
    case_year = request.args.get("case_year")

    if not district_name or not court_id:
        write_log(cnr_no or "-", district_name or "-", court_id or "-", "error: missing params")
        return jsonify({"result": "error", "message": "No Record Found."}), 400

    if not cnr_no and (not case_type or not case_no or not case_year):
        write_log(cnr_no or "-", district_name, court_id, "error: missing search parameters")
        return jsonify({"result": "error", "message": "No Record Found."}), 400

    url = 'https://filing.keralacourts.in/caseSearch'

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True,args=['--no-sandbox', '--disable-setuid-sandbox'])
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

        try:
            page.goto(url)
        except Exception as e:
            browser.close()
            write_log(cnr_no or "-", district_name, court_id, f"error: {str(e)}")
            return jsonify({"result": "error", "message": "No Record Found."}), 502

        page.wait_for_load_state("domcontentloaded")

        dist_name = kerala_districts[district_name]['District Name']
        district_input = page.locator("input[placeholder='Select a district']")
        district_input.wait_for(state="visible", timeout=10000)
        district_input.click(force=True)
        district_input.fill(dist_name)
        page.locator("div[role='option']", has_text=dist_name).first.click(force=True)

        court_input = page.locator("input[placeholder='Select a court']")
        court_input.click(force=True)

        options = page.locator("div[role='option']")
        count = options.count()

        courts_dynamic = {}

        for i in range(count):
            opt = options.nth(i)
            value = opt.get_attribute("value")
            text = opt.inner_text().strip()
            if value:
                courts_dynamic[value] = text

        court_id_clean = str(int(court_id))
        if court_id_clean not in courts_dynamic:
            browser.close()
            write_log(cnr_no or "-", district_name, court_id, "error: court id not found")
            # return jsonify({
            #     "error": f"Invalid court_id {court_id}. Available: {list(courts_dynamic.keys())}"
            # }), 400
            return jsonify({"result": "error", "message": "No Record Found."})

        court_name = courts_dynamic[court_id_clean]

        court_input.fill(court_name)
        page.locator("div[role='option']", has_text=court_name).first.click(force=True)
        # time.sleep(1)

        if cnr_no:
            page.locator("span:has-text('CNR No')").click()
            page.locator("[placeholder='CNR Number']").fill(cnr_no)
            search_tab = page.get_by_role("tabpanel", name="CNR No")

        else:
            page.locator("span:has-text('Case No')").click()
            search_tab = page.get_by_role("tabpanel", name="Case No")

            case_type_input = search_tab.locator("input[placeholder='Choose Case Type']")
            case_type_input.click(force=True)

            html_content = page.content()
            soup = bs(html_content, 'html.parser')
            form = soup.find('form')
            case_labels = [k['id'] for k in form.find_all('label') if 'Case Type' in k.text]
            case_div = soup.find('div', {'aria-labelledby': case_labels[0]})
            case_options = case_div.find_all('div', {'role': 'option'})

            target_option = next((opt for opt in case_options if opt.get('value') == str(case_type)), None)

            if target_option:
                case_type_text = target_option.text.strip()
                case_type_input.fill(case_type_text)
                try:
                    page.locator(f"div[role='option']", has_text=case_type_text ).first.click(force=True)
                except Exception:
                    page.evaluate("""
                               (optionValue) => {
                                   const input = document.querySelector("input[placeholder='Choose Case Type']");
                                   input.value = '';
                                   input.dispatchEvent(new Event('input', { bubbles: true }));
                                   const options = Array.from(document.querySelectorAll("div[role='option']"));
                                   const target = options.find(o => o.getAttribute("value") === optionValue);
                                   if (target) {
                                       target.scrollIntoView({ block: 'center' });
                                       target.click();
                                   }
                               }
                               """, str(case_type))
            else:
                page.evaluate("""
                           (optionValue) => {
                               const input = document.querySelector("input[placeholder='Choose Case Type']");
                               input.value = '';
                               input.dispatchEvent(new Event('input', { bubbles: true }));
                               const options = Array.from(document.querySelectorAll("div[role='option']"));
                               const target = options.find(o => o.getAttribute("value") === optionValue);
                               if (target) {
                                   target.scrollIntoView({ block: 'center' });
                                   target.click();
                               }
                           }
                           """, str(case_type))

            case_no_input = search_tab.locator("[placeholder='Case Number']")
            case_no_input.fill(case_no)
            case_year_input = search_tab.locator("[placeholder='Year']")
            case_year_input.fill(case_year)
        success = False
        attempt = 0
        max_attempts = 4

        while not success and attempt < max_attempts:
            attempt += 1
            try:
                captcha_bytes = search_tab.locator("canvas").nth(0).screenshot()
                img = Image.open(BytesIO(captcha_bytes)).convert("L")

                raw = pytesseract.image_to_string( img, config="--psm 8 -c tessedit_char_whitelist=0123456789")
                text = re.sub(r"\D", "", raw).strip()

                if len(text) == 5:
                    captcha_input = search_tab.get_by_placeholder("Enter Captcha")
                    captcha_input.fill(text)

                    btn = search_tab.locator("button:has-text('Search')")
                    if btn.is_visible() and btn.is_enabled():
                        btn.click()
                        success = True
                        break

                clicked = False
                refresh_icons = page.locator("button:has(svg.tabler-icon-refresh)")

                for i in range(refresh_icons.count()):
                    btn = refresh_icons.nth(i)
                    if btn.is_visible() and btn.is_enabled():
                        btn.click(force=True)
                        clicked = True
                        time.sleep(0.8)
                        break

                if not clicked:
                    refresh_btn = page.locator("button:has-text('Refresh')").first
                    if refresh_btn.count() > 0 and refresh_btn.is_visible():
                        refresh_btn.click(force=True)
                        time.sleep(0.8)

            except Exception:
                continue

        if not success:
            browser.close()
            write_log(cnr_no or "-", district_name, court_id, "error: captcha failed", captcha_attempts=attempt)
            return jsonify({"result": "error", "message": "No Record Found."}), 500

        page.wait_for_load_state("load")
        time.sleep(1.8)
        html_data = page.content()
        browser.close()

    response = bs(html_data, 'html.parser')
    result_card = response.find('div', {'class': 'm_e615b15f mantine-Card-root m_1b7284a3 mantine-Paper-root'})
    sol = {}

    def convert_date(date_str: str):
        try:
            return datetime.strptime(date_str, "%d-%m-%Y").strftime("%Y-%m-%d")
        except Exception:
            return ""

    def clean_list(lst):
        return [re.sub(r'<[^>]+>', '', x).strip() for x in lst if x and x.strip()]

    def safe_extract(datas, keyword, mode="text"):
        try:
            th = next((k for k in datas.find_all('th') if keyword in str(k)), None)
            if th:
                val = th.find_next('td')
                if not val:
                    return ""
                if mode == "span":
                    span = val.find('span')
                    return span.text.strip() if span else ""
                return val.text.strip()
        except Exception:
            return ""
        return ""

    if result_card:
        sol = {}
        datas = response.find('thead', {'class': 'm_b242d975 mantine-Table-thead'})

        case_no_full = safe_extract(datas, "Case No")
        if case_no_full and "/" in case_no_full:
            parts = case_no_full.split('/')
            if len(parts) == 3:
                sol['case_type'], sol['case_no'], sol['case_year'] = parts

        sol['cino'] = safe_extract(datas, "CNR Number")
        sol['case_cnr'] = safe_extract(datas, "CNR Number")
        # sol['act'] = safe_extract(datas, "Acts and Section")
        sol['desgname'] = safe_extract(datas, "Establishment")
        sol['case_status'] = safe_extract(datas, "Case Status", mode="span")
        sol['efile_no'] = safe_extract(datas, "E-File No")
        # sol['date_of_filing'] = convert_date(safe_extract(datas, "Filing Date"))
        sol['case_filed_date'] = convert_date(safe_extract(datas, "Filing Date"))
        sol['date_last_list'] = convert_date(safe_extract(datas, "Disposed Date"))
        sol['date_next_list'] = convert_date(safe_extract(datas, "Next List"))

        under_section = safe_extract(datas,'Acts and Section')
        under_section = str(under_section).split('/')
        sol['under_act'] = under_section[0] if under_section else ''
        sol['under_section'] = under_section[1] if under_section else ''

        filing_number = safe_extract(datas, "Filing Number")
        if filing_number and "/" in filing_number:
            parts = filing_number.split('/')
            if len(parts) == 3:
                sol['fil_type'], sol['fil_no'], sol['fil_year'] = parts

        try:
            peti = [k.find_next('div') for k in response.find_all('h3') if 'PETITIONER AND ADVOCATE' in str(k)][0]
            rows = peti.find('tbody').find_all('tr')
            petitioner_da, pet_advo = [], []
            for r in rows:
                cells = r.find_all('td')
                if len(cells) >= 2:
                    petitioner_da.append(cells[1].text.strip())
                if len(cells) >= 3:
                    pet_advo.append(cells[2].text.strip())
                if len(cells) >= 4:
                    pet_advo.append(cells[3].text.strip())
            sol['petitioner'] = clean_list(petitioner_da)
            sol['petitioner_adv'] = clean_list(sorted(set(pet_advo)))
        except Exception:
            sol['petitioner'], sol['petitioner_adv'] = [], []

        try:
            resp = [k.find_next('div') for k in response.find_all('h3') if 'RESPONDENT AND ADVOCATE' in str(k)][0]
            rows = resp.find('tbody').find_all('tr')
            res_da, res_adv = [], []
            for r in rows:
                cells = r.find_all('td')
                if len(cells) >= 2:
                    res_da.append(cells[1].text.strip())
                if len(cells) >= 3:
                    res_adv.append(cells[2].text.strip())
                if len(cells) >= 4:
                    res_adv.append(cells[3].text.strip())
            sol['respondent'] = clean_list(res_da)
            sol['respondent_adv'] = clean_list(sorted(set(res_adv)))
            sol['case_title'] = sol['petitioner'][0] + ' V/s ' + sol['respondent'][0]
        except Exception:
            sol['respondent'], sol['respondent_adv'] = [], []
            sol['case_title'] = sol['petitioner'][0] + ' V/s ' + sol['respondent'][0]



        case_det = []
        try:
            history = [k.find_previous('div') for k in response.find_all('h3') if 'Case History' in str(k)][0]
            items = history.find('div', {'class': 'mantine-Timeline-root'}).find_all(
                'div', {'class': 'm_436178ff mantine-Timeline-item'})
            for it in items:
                d = {}
                hearing = it.find('div', {'class': 'm_2ebe8099 mantine-Timeline-itemTitle'})
                # if hearing and 'Hearing Date' in hearing.text:
                #     d['next_hearing'] = convert_date(hearing.text.split(':')[1].strip())

                p = it.find('p')
                if p and 'Proceedings' in p.text:
                    d['proceeding'] = p.text.split(':', 1)[1].strip()

                j = it.find('p', string=lambda x: x and 'Judicial Officer' in x)
                if j:
                    d['hearing_judge'] = j.text.split(':')[1].strip()

                # ph = it.find('p', string=lambda x: x and 'Purpose of Hearing' in x)
                # if ph:
                #     d['purpose_of_hearing'] = ph.text.split(':')[1].strip()

                ph = it.find('p', string=lambda x: x and 'Purpose of Hearing' in x)
                if ph:
                    d['case_stage'] = ph.text.split(':')[1].strip()
                    d['bussiness_date'] = { 'bussiness':ph.text.split(':')[1].strip()}

                nd = it.find('p', string=lambda x: x and 'Next Date' in x)
                if nd:
                    # d['next_date'] = convert_date(nd.text.split(':')[1].strip())
                    d['next_hearing'] = convert_date(nd.text.split(':')[1].strip())

                case_det.append(d)
        except Exception:
            pass

        sol['next_hearing_date'] = case_det[::-1]

    write_log(cnr_no or "-", district_name, court_id, "completed", captcha_attempts=attempt)
    if sol:
        return jsonify(sol)
    else : return jsonify({"result": "error", "message": "No Record Found."})


# if __name__ == '__main__':
#     app.run(debug=True)

# http://167.71.225.203/kerala?cnr_no=KLAL300018582024&district=4&court=18&case_type=&case_no=&case_year=
# http://167.71.225.203/kerala?cnr_no=&district=7&court=49&case_type=23&case_no=300889&case_year=2023
# http://167.71.225.203/kerala?cnr_no=&district=9&court=409&case_type=12&case_no=100154&case_year=2023