import sys
sys.path.insert(0, '/var/www/mml_python_code')

import json
import time
import re
import os
from datetime import datetime
from collections import defaultdict
from bs4 import BeautifulSoup as bs
from playwright.sync_api import sync_playwright, TimeoutError

from common_code import proxy_implement
from common_code import common_module as cm

SEND_MAIL = True
# RUN_ONLY_DISTRICT = "WAYANAD"

with open("/var/www/mml_python_code/kerala_causelist/kerala_courts.json", "r", encoding="utf-8") as f:
    court_data = json.load(f)

def parse_html(html_data, district_name):
    soup = bs(html_data, 'html.parser')
    grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

    current_court = None
    current_judge = None
    current_category = None
    current_matter = None

    for element in soup.find_all(['h3', 'div', 'tbody']):
        if element.name == 'h3':
            current_court = element.get_text(strip=True)
            continue

        if element.name == 'div' and 'causelist_headerBox__I89rf' in element.get('class', []):
            raw = element.decode_contents().replace('<br>', ' ').replace('<br/>', ' ')
            judge_text = bs(raw, 'html.parser').get_text(" ", strip=True)
            judge_text = re.sub(r'^\s*In\s+the\s+Court\s+of:\s*', '', judge_text, flags=re.IGNORECASE)
            judge_text = re.sub(r'\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\w+\s+\d{1,2}\s+\d{4}$', '', judge_text).strip()
            current_judge = judge_text
            continue

        if element.name == 'tbody':
            for row in element.find_all('tr'):

                td = row.find('td', colspan="4")
                if td and 'background-color: rgb(6, 115, 186)' in td.get('style', ''):
                    current_category = td.get_text(strip=True).upper()
                    continue

                if td and 'background-color: rgb(237, 248, 255)' in td.get('style', ''):
                    current_matter = td.get_text(strip=True).upper()
                    continue

                if not all([current_court, current_judge, current_category, current_matter]):
                    continue

                if 'print_hideMobile__m8_yF' in row.get('class', []):
                    continue

                cols = row.find_all('td')
                if len(cols) < 4:
                    continue

                sr_no = cols[0].get_text(strip=True)

                main_case_number = cols[1]
                case_number = main_case_number.find('strong').text.strip() if main_case_number.find('strong') else ''
                cnr_no = main_case_number.find('span').text.strip() if main_case_number.find('span') else ''

                connected_cases = []
                conn_td = main_case_number.find('span').find_previous('td') if main_case_number.find('span') else None

                if conn_td:
                    for t in conn_td.stripped_strings:
                        clean = t.strip()
                        if clean and clean not in (case_number, cnr_no):
                            if not clean.lower().startswith(('td', 'div')):
                                connected_cases.append(clean)

                parties = cols[2].text.split('/')
                petitioner = [parties[0].strip()] if len(parties) > 0 else []
                respondent = [parties[1].strip()] if len(parties) > 1 else []

                advocate = cols[3].get_text(separator='\n').strip()
                parts = [p.strip() for p in advocate.split('/')]
                pet_adv = [x.strip() for x in parts[0].split('\n') if x.strip()] if len(parts) > 0 else []
                resp_adv = [x.strip() for x in parts[1].split('\n') if x.strip()] if len(parts) > 1 else []

                case_info = {"sno": sr_no,
                    "case_number": case_number,
                    "cnr_no": cnr_no,
                    "connected_case": connected_cases,
                    "petitioner_name": petitioner,
                    "respondent_name": respondent,
                    "petitioner_adv": pet_adv,
                    "respondent_adv": resp_adv }

                grouped[current_court][current_judge][current_category][current_matter].append(case_info)

    final_list = []
    for court, judges in grouped.items():
        court_block = {"court": court, "results": []}
        for judge, categories in judges.items():
            judge_block = {"judge_name": judge, "categories": []}
            for cat, matters in categories.items():
                for mat, clist in matters.items():
                    judge_block["categories"].append({
                        "category": cat,
                        "matter_type": mat,
                        "clist": clist
                    })
            court_block["results"].append(judge_block)
        final_list.append(court_block)

    return final_list

start_time = datetime.now()
print("Scraping started at:", start_time)
summary = []

try:
    with sync_playwright() as p:

        prx = proxy_implement.get_new_requests_playwright()

        browser = p.chromium.launch(
            headless=True,args=["--disable-blink-features=AutomationControlled","--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"],)

        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto("https://filing.keralacourts.in/causeList")
        time.sleep(1)

        page.wait_for_load_state("networkidle")
        page.wait_for_selector("input[placeholder='Causelist Date']", timeout=15000)

        for _ in range(20):
            date_value = page.locator("input[placeholder='Causelist Date']").input_value().strip()
            if re.match(r"\d{2}-\d{2}-\d{4}", date_value):
                break
            time.sleep(0.3)

        print("Detected causelist date:", date_value)

        output_dir = os.path.join(cm.BASE_DIR_OUTPUTS, "kerala_causelist", date_value)
        os.makedirs(output_dir, exist_ok=True)

        for district_name, courts in court_data.items():

            # if RUN_ONLY_DISTRICT and district_name != RUN_ONLY_DISTRICT:
            #     continue

            district_cases = []
            time.sleep(1)
            district_input = page.locator("input[placeholder='Select a district']")
            district_input.click()
            time.sleep(1)
            page.get_by_role("option", name=district_name, exact=True).click()
            page.wait_for_timeout(1000)

            for court in courts:
                court_name = court["name"]

                try:
                    court_input = page.locator("input[placeholder='Select a court']")
                    court_input.click()
                    page.get_by_role("option", name=court_name, exact=True).click()

                    for _ in range(30):
                        if page.locator("tbody tr").count() > 0:
                            break
                        time.sleep(1)

                    acc = page.locator(".mantine-Accordion-label")
                    for i in range(acc.count()):
                        try:
                            acc.nth(i).click()
                            time.sleep(1.2)
                        except:
                            pass

                    html = page.content()
                    parsed = parse_html(html, district_name)
                    if parsed:
                        district_cases.extend(parsed)

                except TimeoutError:
                    print(f"Could not select court {court_name}, skipping...")

            district_total = sum(len(cat["clist"]) for court in district_cases for judge in court["results"] for cat in judge["categories"])

            if district_cases:
                data_with_date = {"scraped_date": date_value,
                    "district_name": district_name,
                    "district_total_cases": district_total,
                    "data": district_cases}

                out_path = os.path.join(output_dir, f"{district_name}.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data_with_date, f, indent=2, ensure_ascii=False)

                summary.append(f"{district_name}: {district_total}")
                print(f"{district_name} - Done ({district_total} cases)")
                print("Saved", out_path)

finally:
    try:
        browser.close()
    except:
        pass

end_time = datetime.now()
print("Scraping ended at:", end_time)
print("Duration:", end_time - start_time)
print("Scraping completed!")

mail_body = f"""Kerala Causelist Daily report
Report generated at 

{chr(10).join(summary)}
"""

print(mail_body)
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(subject, body):
    host = "email-smtp.us-west-2.amazonaws.com"
    port = 587

    username = "AKIAXZ2CHOT75B53GBNN"
    password = "BHw8IFHZsCr+5IKgXP04oDhU2P846oQSVcWY5IgllILj"

    from_email = "deepak@managemylawsuits.com"
    to_email = ["sanjai@jbkinfotech.com","manoj@jbkinfotech.com"]

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = ", ".join(to_email)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(username, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print("Email error:", e)

subject = f"Kerala Causelist date {date_value}"

if SEND_MAIL and summary:
    send_email(subject, mail_body)
else:
    print("Email skipped.")
