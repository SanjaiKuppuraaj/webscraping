import requests
from bs4 import BeautifulSoup as bs
import time, json, re
from common_code import proxy_implement

USE_PROXY = True
PROXY_USER = 'jbkinfotech25-res-in'
PROXY_PASSWORD = 'Ip1fsukDrglaz0M'
PROXY_URL = 'gw-open.netnut.net'
PROXY_PORT = '5959'

if USE_PROXY:
    proxes = {
        "http": f"http://{PROXY_USER}:{PROXY_PASSWORD}@{PROXY_URL}:{PROXY_PORT}",
        "https": f"http://{PROXY_USER}:{PROXY_PASSWORD}@{PROXY_URL}:{PROXY_PORT}"
    }
else:
    proxes = None


class hc_bombay:
    def __init__(self, m_hc, m_sideflg, m_sr, m_skey, m_no, m_yr):
        self.session = requests.Session()
        # print(f"rocessing: {m_hc}/{m_sideflg}/{m_sr}/{m_skey}/{m_no}/{m_yr}")
        self.headers = {"cookie": "hidden=value; PHPSESSID=7inpmdv3mr6dojagfrrjjce763","host": "bombayhighcourt.nic.in","user-agent": "Mozilla/5.0" }
        self.m_hc = m_hc
        self.m_sideflg = m_sideflg
        self.m_sr = m_sr
        self.m_skey = m_skey
        self.m_no = m_no
        self.m_yr = m_yr

    def get_current_ip(self):
        try:
            res = self.session.get("https://api.ipify.org", proxies=proxes)
            return res.text.strip()
        except Exception as e:
            return f"IP fetch failed: {e} | Maybe proxy down"

    def safe_request_with_retry(self, request_func, retries=3, delay=2):
        for attempt in range(retries):
            try:
                return request_func()
            except Exception as e:
                return {"result": "error", "message": "No Record Found."}

    def captcha(self):
        url = 'https://bombayhighcourt.nic.in/case_query.php'
        headers = {'referer': 'https://bombayhighcourt.nic.in/index.php', **self.headers}
        response = self.safe_request_with_retry(lambda: self.session.get(url, headers=headers, proxies=proxes))
        if isinstance(response, dict): return response
        soup = bs(response.text, 'html.parser')
        self.captchas = soup.find('img', {'id': "captchaimg"})['src'].split('=')[-1]
        self.csrf_name = soup.find('input', {'name': 'CSRFName'})['value']
        self.csrf_token = soup.find('input', {'name': 'CSRFToken'})['value']


    def case_main_info(self):
        def remove_empty(lst):
            return [item for item in lst if item.strip()]

        def extract_acts_from_rows(rows):
            acts = []
            for tr in rows:
                tds = tr.find_all('td')
                for j, td in enumerate(tds):

                    if 'Act :-' in td.get_text(" ", strip=True):
                        next_td = td.find_next('td')
                        if next_td:
                            datas = next_td.get_text(" ", strip=True)
                            if not datas.lower().startswith('under section'):
                                acts.append(datas)

                    raw = td.get_text(" ", strip=True)
                    if 'act' not in raw.lower():
                        continue

                    if re.match(r'^\s*act\b[\s\:\-]*$', raw, flags=re.I):
                        candidate = tds[j + 1].get_text(" ", strip=True) if (j + 1) < len(tds) else raw
                    else:
                        if ':-' in raw:
                            candidate = raw.split(':-', 1)[1].strip()
                        else:
                            candidate = raw
                    candidate = re.sub(r'^\W+|\W+$', '', candidate).strip()
                    candidate = re.sub(r'\s+', ' ', candidate)
                    if candidate:
                        acts.append(candidate)
            seen = set()
            cleaned = []
            for a in acts:
                key = a.lower()
                if key not in seen:
                    seen.add(key)
                    cleaned.append(a)
            return cleaned

        cap = self.captcha()
        if isinstance(cap, dict):
            return cap

        form_data = {"CSRFName": self.csrf_name,"CSRFToken": self.csrf_token,"submitflg": "C","m_hc": self.m_hc,"m_sideflg": self.m_sideflg,"m_sr": self.m_sr,"m_skey": self.m_skey,"m_no": self.m_no,"m_yr": self.m_yr,"captchaflg": "","captcha_code": self.captchas,"frmdate": "", "todate": "","captcha_code_cq": ""}
        headers = {**self.headers,'referer': 'https://bombayhighcourt.nic.in/case_query.php' }
        response = self.safe_request_with_retry(lambda: self.session.post("https://bombayhighcourt.nic.in/casequery_action.php", headers=headers, data=form_data,proxies=proxes))

        if isinstance(response, dict):
            return response

        soup = bs(response.text, 'html.parser')
        datas = soup.find('table')
        if not datas:
            return {"result": "error", "message": "No Record Found."}

        try:
            sol = {}
            rows = datas.find_all('tr')
            i = 0

            while i < len(rows):
                tr = rows[i]
                tds = tr.find_all('td')

                for j in range(len(tds)):
                    text = tds[j].text.strip().lower()

                    if 'cnr no.' in text:
                        if j + 1 < len(tds):
                            sol['cnr_no'] = tds[j + 1].text.strip()

                    elif 'stamp no.' in text:
                        if j + 1 < len(tds):
                            sol['stamp_no'] = tds[j + 1].text.strip()

                    elif 'filing date' in text:
                        if j + 1 < len(tds):
                            sol['filing_date'] = tds[j + 1].text.strip()

                    elif 'reg. no.' in text:
                        if j + 1 < len(tds):
                            sol['reg_no'] = tds[j + 1].text.strip()

                    elif 'reg. date' in text:
                        if j + 1 < len(tds):
                            sol['reg_date'] = tds[j + 1].text.strip()

                    elif 'petitioner' in text:
                        if j + 1 < len(tds):
                            sol['petitioner'] = [opt.text.replace('-','').strip() for opt in tds[j + 1].find_all('option')]

                    elif 'respondent' in text:
                        if j + 1 < len(tds):
                            sol['respondent'] = [opt.text.replace('-','').strip() for opt in tds[j + 1].find_all('option')]

                    elif 'petn.adv.' in text:
                        if j + 1 < len(tds):
                            sol['pet_adv'] = [opt.text.strip() for opt in tds[j + 1].find_all('option')]

                    elif 'district' in text:
                        sol['district'] = str(text.split(':-')[-1].strip()).capitalize()

                    elif 'status' in text:
                        font = tds[j].find('font')
                        if font:
                            sol['status'] = font.text.strip()

                    elif 'last date' in text and 'last_date' not in sol:
                        sol['last_date'] = text.split(':-')[-1].strip()

                    elif 'disp. date' in text and 'last_date' not in sol:
                        sol['last_date'] = text.strip().split(':-')[-1].strip()

                    elif 'disp.type' in text and 'last_type' not in sol:
                        sol['last_type'] = text.strip().split(':-')[-1].strip()

                    # elif 'act' in text:
                    #     sol['act'] = text.split(':-')[-1].strip()

                    elif 'under' in text:
                        if j + 1 < len(tds):
                            sol['under_section'] = tds[j + 1].text.strip()

                    elif 'next date' in text:
                        sol['next_date'] = text.strip().split(':-')[-1].strip()

                    elif 'last coram' in text:

                        last_coram_row = [td.text.split(':-')[-1].strip() for td in tds if 'last coram']
                        coram_extra = []

                        if i + 1 < len(rows):
                            next_tds = rows[i + 1].find_all('td')
                            coram_extra = [td.text.strip() for td in next_tds if "hon'ble" in td.text.lower()]

                        sol['last_coram'] = remove_empty(last_coram_row) + remove_empty(coram_extra)
                        i += 1

                    elif 'disp.by' in text or 'coram' in text.lower():
                        if 'disp.by' in text:
                            coram_row = [td.text.split(':-')[-1].strip() for td in tds if 'disp.by']
                            # coram_extra = []
                        elif 'coram' in text.lower():
                            coram_row = [td.text.split(':-')[-1].strip() for td in tds if 'coram']
                        if i + 1 < len(rows):
                            next_tds = rows[i + 1].find_all('td')
                            coram_extra = [td.text.strip() for td in next_tds if "hon'ble" in td.text.lower()]

                        sol['coram'] = remove_empty(coram_row) + remove_empty(coram_extra)

                        i += 1

                i += 1
            sol['act'] = ' '.join(extract_acts_from_rows(rows))
            return sol

        except Exception as e:
            return {"result": "error", "message": f"Exception occurred: {str(e)}"}
