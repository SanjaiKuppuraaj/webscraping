import json
import time
import random
import logging
import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime
from common_code import proxy_implement
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_session(proxy_mode=None):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/139.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
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
            time.sleep(random.randint(3, 6))
    raise Exception(f"Failed to fetch {url} after retries")

def parse_court_html(html):
    results = {}
    try:
        results["date"] = html.find("h5", {"title": "Date"}).get_text(strip=True).split(":")[1].strip()
        results["coram"] = [k.replace("\n", "").strip() for k in html.find("h5", {"title": "Bench Details"}).get_text(strip=True).split("And") if k]
        results["court_no"] = [html.find("h5", {"title": "COURT LOCATION"}).get_text(strip=True)]
    except Exception:
        results["date"] = ""
        results["coram"] = []
        results["court_no"] = []

    result = []
    main_case_counter = 1
    headings = html.select("h4[title='ADVANCE CAUSELIST'], h5[title='SUPPLEMENTARY CAUSELIST'], h5[title='REGULAR LIST']")
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
                case_type = caseno.split("-")[0].split("(")[0].split(" ")[0].strip()
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
    return results

def get_causelist(date_str, output_file, refresh=False):
    try:
        formatted_date = datetime.strptime(date_str, "%d-%m-%Y").strftime("%Y-%m-%d")
    except Exception:
        return {"success": [], "failed": [], "message": "Invalid date format"}

    proxy_mode = proxy_implement.get_requests_proxy()
    session = get_session(proxy_mode)
    base_url = "https://delhihighcourt.nic.in/app/online-causelist"

    attempts = 2 if refresh else 1
    for _ in range(attempts):
        try:
            resp = fetch_with_retry(session, "GET", base_url)
            soup = bs(resp.text, "html.parser")
            token = soup.find("input", {"name": "_token"})["value"]
            captcha = soup.find("span", {"id": "captcha-code"}).text.strip()
            captcha_input = captcha
            break
        except Exception:
            if refresh:
                time.sleep(2)
                continue
            return {"success": [], "failed": [], "message": "No Record Found"}

    data = {"_token": token, "cause_list_date": formatted_date,
            "randomid": captcha, "captchaInput": captcha_input}
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Referer": base_url}

    try:
        res = fetch_with_retry(session, "POST", "https://delhihighcourt.nic.in/app/get-bench",
                               data=data, headers=headers)
        soup = bs(res.text, "html.parser")
        main_token = soup.find("input", {"name": "_token"})["value"]
        court_values = [k["value"] for k in soup.find("select", {"id": "courtno"}).find_all("option") if k]
    except Exception:
        return {"success": [], "failed": [], "message": "No Record Found"}

    success_data = []
    failed_courts = []

    bench_url = "https://delhihighcourt.nic.in/app/get-bench-details"

    for court in court_values:
        payload = {"_token": main_token, "cause_list_date": formatted_date, "courtno": court}
        try:
            bench_res = fetch_with_retry(session, "POST", bench_url, data=payload, headers=headers)
            html = bs(bench_res.text, "html.parser")
            court_data = parse_court_html(html)
            success_data.append(court_data)
        except Exception as e:
            failed_courts.append({"court": court, "error": str(e)})
            continue

    # Append to existing file
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            existing = json.load(f).get("result", [])
        success_data = existing + success_data

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({"result": success_data}, f, indent=4, ensure_ascii=False)

    return {"success": success_data, "failed": failed_courts}
