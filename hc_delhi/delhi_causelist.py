import sys
sys.path.insert(0, '/var/www/mml_python_code')
import json
import time
import random
import logging
import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime, timedelta
from common_code import proxy_implement
from common_code import common_module as cm
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

output = cm.BASE_DIR_OUTPUTS + '/delhi_causelist'

SEND_MAIL = True

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_session(proxy_mode=None):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/139.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",}
    session.headers.update(headers)
    if proxy_mode:
        session.proxies.update(proxy_mode)
    return session

def fetch_with_retry(session, method, url, **kwargs):
    for attempt in range(3):
        try:
            resp = session.request(method, url, timeout=30, **kwargs)
            resp.raise_for_status()
            return resp
        except (requests.exceptions.SSLError, requests.exceptions.Timeout,
                requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
            logging.warning(f"{method} {url} failed on attempt {attempt+1}: {e}")
            time.sleep(random.randint(3, 8))
    raise Exception(f"Failed to fetch {url} after retries")

def get_causelist(date_str, output_file):
    proxy_mode = proxy_implement.get_requests_proxy()  # load proxy config
    session = get_session(proxy_mode)

    base_url = "https://delhihighcourt.nic.in/app/online-causelist"
    resp = fetch_with_retry(session, "GET", base_url)
    soup = bs(resp.text, "html.parser")

    token = soup.find("input", {"name": "_token"})["value"]
    captcha = soup.find("span", {"id": "captcha-code"}).text.strip()

    captcha_input = captcha

    data = {
        "_token": token,
        "cause_list_date": date_str,
        "randomid": captcha,
        "captchaInput": captcha_input,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Referer": base_url}

    main_url = "https://delhihighcourt.nic.in/app/get-bench"
    res = fetch_with_retry(session, "POST", main_url, data=data, headers=headers)
    main_soup = bs(res.text, "html.parser")

    try:
        main_token = main_soup.find("input", {"name": "_token"})["value"]
        court_values = [k["value"] for k in main_soup.find("select", {"id": "courtno"}).find_all("option") if k]
    except Exception:
        logging.error("Failed to extract bench details. Likely captcha/token issue.")
        return []

    bench_url = "https://delhihighcourt.nic.in/app/get-bench-details"
    final_data = []

    for court in court_values:
        payload = {"_token": main_token, "cause_list_date": date_str, "courtno": court}
        try:
            bench_res = fetch_with_retry(session, "POST", bench_url, data=payload, headers=headers)
            html = bs(bench_res.text, "html.parser")

            results = {}
            try:
                results["date"] = html.find("h5", {"title": "Date"}).get_text(strip=True).split(":")[1].strip()
                results["coram"] = [k.replace("\n", "").strip() for k in html.find("h5", {"title": "Bench Details"}).get_text(strip=True).split("And") if k]
                results["court_no"] = [html.find("h5", {"title": "COURT LOCATION"}).get_text(strip=True)]
            except Exception as e:
                logging.warning(f"Failed to parse header details for {court}: {e}")
                results["date"] = ""
                results["coram"] = []
                results["court_no"] = []

            result = []
            main_case_counter = 1

            headings = html.select("h4[title='ADVANCE CAUSELIST'], "
                                   "h5[title='SUPPLEMENTARY CAUSELIST'], "
                                   "h5[title='REGULAR LIST']")
            for heading in headings:
                matter_type = heading.get("title", "").strip()
                next_table = heading.find_next("table")
                if not next_table:
                    continue

                rows = next_table.select("tbody tr")
                for datas in rows:
                    tds = datas.find_all("td")
                    if len(tds) < 6:
                        continue
                    case_no_td = tds[1]
                    for tag in case_no_td.find_all(["a", "mark"]):
                        tag.decompose()

                    casenos = [text.strip() for text in case_no_td.get_text(separator="\n").split("\n") if text.strip()]
                    case_pet = tds[2].get_text(strip=True)
                    casepet = [k.strip() for k in case_pet.split("v/s")] if "v/s" in case_pet else ["", ""]
                    petitioner = casepet[0] if len(casepet) > 1 else ""
                    respondent = casepet[1] if len(casepet) > 1 else ""

                    advs = [k.strip().replace("  ", " ") for k in tds[3].get_text(strip=True).split(",") if k]
                    while len(advs) < len(casenos):
                        advs.append(advs[-1] if advs else "")

                    case_stage = tds[4].get_text(strip=True)
                    board_remark = tds[5].get_text(strip=True)

                    for idx, caseno in enumerate(casenos):
                        # case_type = caseno.split("-")[0].split("(")[0].split(" ")[0].strip()
                        case_type = str(re.sub(r'\d+', '', caseno.split("-")[0].replace('WITH', '').replace('/','').strip())).strip()
                        caseyears = caseno.split("-")[-1].split("/")
                        case_no = caseyears[0].split(" ")[-1].split("/")[0].strip()
                        case_year = caseyears[1].strip() if len(caseyears) > 1 else ""

                        cases_noes = f"{case_type}-{case_no}-{case_year}"
                        sno = str(main_case_counter) if idx == 0 else f"{main_case_counter}.{idx}"

                        sol = {
                            "sno": sno,
                            "caseno": cases_noes,
                            "case_type": case_type,
                            "case_no": case_no,
                            "case_year": case_year,
                            "petitioner": [petitioner],
                            "respondent": [respondent],
                            "adv_name": [advs[idx]] if idx < len(advs) else "",
                            "case_stage": case_stage,
                            "Board_Remark": board_remark,
                            "matter_type": matter_type,
                        }
                        result.append(sol)
                    main_case_counter += 1

            results["clist"] = result
            logging.info(f"Court {court} → {len(result)} cases extracted")
            final_data.append(results)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump({'result':final_data}, f, indent=4, ensure_ascii=False)

        except Exception as e:
            logging.error(f"Failed to fetch/process court {court}: {e}")
            continue
    return  final_data

def send_email(subject, body):
    host = "email-smtp.us-west-2.amazonaws.com"
    port = 587
    username = "AKIAXZ2CHOT75B53GBNN"
    password = "BHw8IFHZsCr+5IKgXP04oDhU2P846oQSVcWY5IgllILj"

    from_email = "deepak@managemylawsuits.com"
    to_email = ["sanjai@jbkinfotech.com",'manoj@jbkinfotech.com']

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
        print("Error sending email:", e)


if __name__ == "__main__":
    import sys

    today = datetime.today()
    tomorrow = today + timedelta(days=1)

    date_arg = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if date_arg == "today":
        target_date = today
    else:
        target_date = tomorrow

    # target_date_str = '26-09-2025'
    # target_date = datetime.strptime(target_date_str, "%d-%m-%Y")

    date_str = target_date.strftime("%Y-%m-%d")
    output_dir = cm.BASE_DIR_OUTPUTS + '/delhi_causelist'
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, target_date.strftime("%d-%m-%Y.json"))
    all_results = get_causelist(date_str, output_file)

    if all_results:
        total_records = sum(len(court.get("clist", [])) for court in all_results)
        msg = f"Saved {len(all_results)} courts with {total_records} total cases to {output_file}"
        print(msg)

        subject = f"Delhi Cause List {target_date.strftime('%d-%m-%Y')}"
        body = (
            f"Delhi Cause List Daily Report\n\n"
            f"Report generated at: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n"
            f"Total Courts: {len(all_results)}\n"
            f"Total Cases: {total_records}\n"
        )

        if SEND_MAIL:
            send_email(subject, body)
    else:
        print("No data extracted (likely captcha/token issue)")
        subject = f"Delhi Cause List {target_date.strftime('%d-%m-%Y')}"
        body = (
            f"Delhi Cause List Daily Report\n\n"
            f"Report generated at: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n"
            f"No data extracted (likely captcha/token issue).\n"
        )

        if SEND_MAIL:
            send_email(subject, body)
