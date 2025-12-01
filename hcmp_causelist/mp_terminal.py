from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
from bs4 import BeautifulSoup as bs
import pytesseract
import os
import re
import json
import random
from datetime import datetime
from common_code import common_module as cm

app = Flask(__name__)

proxy = False

PROXY_USER = 'jbkinfotech25-res-in'
PROXY_PASSWORD = 'Ip1fsukDrglaz0M'
PROXY_URL = 'gw-open.netnut.net'
PROXY_PORTS = ['5959']


mfb_map = {"1": "Motion", "4": "Lok Adalat", "5": "Mediation"}
sdbench_map = {"1": "Single Bench", "2": "Division Bench", "3": "Full Bench"}
city_map = {"01": "Jabalpur", "02": "Indore", "03": "Gwalior"}

def preprocess_image(image):
    image = image.convert("L")
    image = image.filter(ImageFilter.MedianFilter(size=3))
    image = ImageEnhance.Contrast(image).enhance(3)
    image = image.resize((image.width * 3, image.height * 3))
    image = image.point(lambda x: 0 if x < 140 else 255, '1')
    image = image.filter(ImageFilter.SHARPEN)
    return image

def extract_captcha_text(image):
    for psm in [6, 7]:
        text = pytesseract.image_to_string(image, config=f'--psm {psm} -c tessedit_char_whitelist=0123456789').strip()
        digits = ''.join(filter(str.isdigit, text))
        if len(digits) == 3:
            return digits
    return ""

def is_new_case(tr):
    tds = tr.find_all("td")
    if not tds:
        return False
    serial = tds[0].text.strip()
    try:
        float(serial)
        return True
    except ValueError:
        return False

def extract_case_data(case_rows):
    tds0 = case_rows[0].find_all("td")
    serial = tds0[0].text.strip()
    case_number = tds0[1].decode_contents().strip().replace("\n", "")
    petitioner_html = tds0[2].decode_contents().strip()
    respondent_html = ""
    if len(case_rows) > 1 and len(case_rows[1].find_all("td")) >= 3:
        respondent_html = case_rows[1].find_all("td")[2].decode_contents().strip()
    party_html = f"<div>Petitioner:<br/>{petitioner_html}<br/><br/>Respondent:<br/>{respondent_html}</div>"
    adv_pet = tds0[3].decode_contents().strip()
    adv_res = ""
    if len(case_rows) > 1 and len(case_rows[1].find_all("td")) >= 4:
        adv_res = case_rows[1].find_all("td")[3].decode_contents().strip()
    advocate_html = f"Petitioner: {adv_pet}<br/>Respondent: {adv_res}"
    remarks = tds0[4].decode_contents().strip()
    subject_lines = ""
    ia_lines = ""
    for tr in case_rows[2:]:
        tds = tr.find_all("td")
        for td in tds:
            html = td.decode_contents().strip()
            if "IA No" in html:
                ia_lines += "<br/>" + html
            elif "colspan" in td.attrs or len(tds) == 1:
                subject_lines += "<br/>" + html
    final_remarks = f"{remarks}{subject_lines}{ia_lines}".strip()
    return [serial, case_number, party_html, advocate_html, final_remarks]

def parse_cleaned_html(soup):
    final_result = []
    for h2 in soup.find_all('h2'):
        judge_names = h2.text.strip()
        court_number = [judge_names.split('[')[-1].replace(']-', '').replace(']', '').strip()]
        date_match = re.search(r'\d{2}-\d{2}-\d{4}', judge_names)
        causelist_date = date_match.group() if date_match else ''
        judge_info = judge_names.split(causelist_date, 1)[-1].strip() if causelist_date else judge_names
        if '[' in judge_info:
            judge_info = judge_info.split('[', 1)[0].strip()
        coram = [judge_info.replace('\xa0', ' ')]
        clist = []
        for tr in h2.find_all_next('tr'):
            if tr.find_previous('h2') != h2:
                break
            tds = tr.find_all('td')
            if not tds or len(tds) < 5:
                continue
            try:
                sol = {
                    'brd_slno': tds[0].text.strip(),
                    'case_type': '', 'case_no': '', 'case_year': '', 'cases': '',
                    'petitioner_name': '', 'respondent_name': '',
                    'petitioner_adv': [], 'respondent_adv': [],
                    'remark': '', 'Board_Remark': ''
                }
                case_details = tds[1]
                case_no = [k.strip() for k in bs(str(case_details).split('<br/>')[0], 'html.parser').text.split('-') if k]
                if len(case_no) < 2:
                    continue
                case_section = case_no[-1].split()[1] if len(case_no[-1].split()) > 1 else ''
                sol['case_type'] = case_no[0] + ' ' + case_section
                case_number = case_no[1].split(' ')[0].split('/')
                if len(case_number) < 2:
                    continue
                sol['case_no'] = case_number[0]
                sol['case_year'] = case_number[1]
                sol['cases'] = f"{case_no[0]}-{case_no[1].replace('/', '-').replace(' ', '-')}"

                peti = tds[2].text.split('Respondent:')
                sol['respondent_name'] = peti[1].strip() if len(peti) > 1 else ''
                sol['petitioner_name'] = peti[0].split('Petitioner:')[1].strip() if 'Petitioner:' in peti[0] else ''

                advo_petse = str(tds[3]).split('Respondent:')
                pet_advo = bs(advo_petse[0], 'html.parser')
                sol['petitioner_adv'] = [line.strip() for div in pet_advo.find_all("div") for line in div.decode_contents().split('<br/>') if line.strip()]
                res_advo = bs(advo_petse[1], 'html.parser') if len(advo_petse) > 1 else bs('', 'html.parser')
                sol['respondent_adv'] = list(dict.fromkeys([line.strip() for div in res_advo.find_all(["div", "span"]) for line in div.get_text(separator='<br/>').split('<br/>') if line.strip()]))

                board = tds[4]
                sol['remark'] = bs(str(board).split('<br/>')[0], 'html.parser').text.strip()
                board_remarks = [bs(k, 'html.parser').get_text(strip=True).replace('\n', '') for k in str(board).split('<br/>') if bs(k, 'html.parser').get_text(strip=True)]
                sol['Board_Remark'] = board_remarks[-1] if board_remarks else ''
                clist.append(sol)
            except:
                continue
        if clist:
            final_result.append({"Court_Number": court_number, "Date": causelist_date, "coram": coram, "clist": clist})
    return final_result

# def log_status(city, mfb, bench, log_date, status):
#     # log_folder = os.path.join("hcmp_causelist", log_date)
#     log_folder = cm.BASE_DIR_LOGS + '/'+datetime.now().strftime('%Y-%m-%d')+'/'
#     os.makedirs(log_folder, exist_ok=True)
#     log_path = os.path.join(log_folder, "mp_terminal.txt")
#     log_line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {city}/{mfb}/{bench}/{log_date} | Status: {status}\n"
#     with open(log_path, "a", encoding="utf-8") as log_file:
#         log_file.write(log_line)


def log_status(city, mfb, bench, log_date, status):
    try:
        log_folder = os.path.join(cm.BASE_DIR_LOGS, datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(log_folder, exist_ok=True)
        log_path = os.path.join(log_folder, "mp_terminal.txt")
    except PermissionError:
        log_folder = os.path.join("/tmp", "mp_logs", datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(log_folder, exist_ok=True)
        log_path = os.path.join(log_folder, "mp_terminal.txt")

    log_line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {city}/{mfb}/{bench}/{log_date} | Status: {status}\n"

    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(log_line)
    except Exception as e:
        print(f"[Log Error] {e}")


@app.route("/mp_causelist")
def get_mp_causelist():
    city = request.args.get("bench")
    refresh = request.args.get("refresh", "false").lower() == "true"

    city_val, city_name = None, None
    if city in city_map:
        city_val, city_name = city, city_map[city]
    elif city in city_map.values():
        city_val = next(k for k, v in city_map.items() if v == city)
        city_name = city
    else:
        return jsonify({"result": "error", "message": "Invalid city value"})

    today = datetime.now().strftime("%d-%m-%Y")
    # output_folder = os.path.join('hcmp_causelist', today)
    output_folder = os.path.join(cm.BASE_DIR_OUTPUTS, "Mp_causelist", today)

    os.makedirs(output_folder, exist_ok=True)

    final_summary = []

    if not refresh:
        for file in os.listdir(output_folder):
            if file.endswith(".json") and city_name.lower() in file:
                with open(os.path.join(output_folder, file), "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        if data.get("success"):
                            final_summary.extend(data.get("results", []))
                    except json.JSONDecodeError:
                        continue
        if final_summary:
            return jsonify({"success": True, "message": "Record Found.", "results": final_summary})

    with sync_playwright() as p:
        proxy_settings = {}
        if proxy:
            proxy_port = random.choice(PROXY_PORTS)
            full_proxy = f"http://{PROXY_USER}:{PROXY_PASSWORD}@{PROXY_URL}:{proxy_port}"
            proxy_settings = {"server": full_proxy}

        browser = p.chromium.launch(headless=True, args=["--no-sandbox"], proxy=proxy_settings or None)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        print('line no 197')
        page.goto("https://mphc.gov.in/causelist")
        print('line no 199')
        page.select_option('#my_city', value=city_val)
        page.wait_for_timeout(1000)
        print('line no 202')
        for mfb_val, mfb_name in mfb_map.items():
            print(mfb_name)
            for sd_val, sd_name in sdbench_map.items():
                success = False
                for _ in range(5):
                    try:
                        page.reload()
                        captcha_el = page.query_selector("img.cp_img")
                        if not captcha_el:
                            continue
                        captcha_el.click()
                        image = Image.open(BytesIO(captcha_el.screenshot(type="png")))
                        captcha_text = extract_captcha_text(preprocess_image(image))
                        if len(captcha_text) != 3:
                            continue

                        page.select_option('#aw1', value='0')
                        page.fill("#code", captcha_text)
                        page.locator(f'input[name="mfb"][value="{mfb_val}"]').check()
                        page.locator(f'input[id="sdbench"][value="{sd_val}"]').check()
                        page.evaluate("document.getElementById('dtd1').removeAttribute('readonly');")
                        page.fill('#dtd1', today)
                        page.click("input#bt11")
                        page.wait_for_timeout(2000)
                        if "Captcha code does not match" in page.content():
                            continue
                        page.wait_for_selector("#adv_cl_en_wp", timeout=60000)

                        try:
                            page.locator("xpath=//div[contains(text(),'Click to Expand')][1]").click(timeout=2000)
                        except PlaywrightTimeout:
                            pass

                        html_content = bs(page.content(), 'html.parser')
                        result_box = html_content.find('div', {'id': 'adv_cl_en_wp'})
                        for tag in result_box.select('[style*="#999999"], p.showhide'):
                            tag.decompose()

                        body = result_box or html_content
                        sections = []
                        current_section = {"date": "", "rows": []}
                        for tag in body.find_all(recursive=False):
                            children = tag.find_all(["font", "table", "tr"], recursive=True) if tag.name not in ["font", "tr"] else [tag]
                            for child in children:
                                if child.name == "font" and "Causelist dated" in child.text:
                                    if current_section["date"] and current_section["rows"]:
                                        sections.append(current_section)
                                    current_section = {"date": child.text.strip(), "rows": []}
                                elif child.name == "tr":
                                    current_section["rows"].append(child)
                        if current_section["date"] and current_section["rows"]:
                            sections.append(current_section)

                        html_cleaned = "<html><body>"
                        for section in sections:
                            html_cleaned += f"<h2>{section['date']}</h2>\n<table>"
                            cases = []
                            current_case = []
                            for tr in section["rows"]:
                                if is_new_case(tr):
                                    if current_case:
                                        cases.append(current_case)
                                        current_case = []
                                if tr.find_all("td"):
                                    current_case.append(tr)
                            if current_case:
                                cases.append(current_case)
                            for case_rows in cases:
                                try:
                                    data = extract_case_data(case_rows)
                                    html_cleaned += "<tr>" + "".join(f"<td>{cell}</td>" for cell in data) + "</tr>"
                                except:
                                    continue
                            html_cleaned += "</table>"
                        html_cleaned += "</body></html>"

                        soup = bs(html_cleaned, "html.parser")
                        parsed_data = parse_cleaned_html(soup)
                        for section in parsed_data:
                            section["ctype"] = mfb_name
                            section["bench"] = sd_name.replace('Bench', '').strip()
                            section["court_name"] = city_name

                        filename = f"{city_name.lower()}_{mfb_name.lower().replace(' ', '_')}_{sd_name.lower().replace(' ', '_')}_{today}.json"
                        filepath = os.path.join(output_folder, filename)
                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump({"success": True, "message": "Record Found.", "results": parsed_data}, f, ensure_ascii=False, indent=2)

                        final_summary.extend(parsed_data)
                        log_status(city_name, mfb_name, sd_name, today, "Completed")
                        success = True
                        break
                    except Exception as e:
                        continue
                if not success:
                    log_status(city_name, mfb_name, sd_name, today, "Error")

        browser.close()

    return jsonify({"success": True, "message": "Record Found.", "results": final_summary})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
