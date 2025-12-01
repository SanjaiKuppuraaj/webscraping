import requests
from bs4 import BeautifulSoup as bs
from common_code import common_module as cm
import time, json

class hc_bombay:
    def __init__(self, m_hc, m_sideflg, m_sr, m_skey, m_no, m_yr):
        self.session = requests.Session()
        if cm.USE_PROXY:
            proxy_url = cm.get_proxy()
            self.session.proxies.update({"http": proxy_url, "https": proxy_url})

        self.headers = {"cookie": "hidden=value; PHPSESSID=7inpmdv3mr6dojagfrrjjce763","host": "bombayhighcourt.nic.in","user-agent": "Mozilla/5.0" }
        self.m_hc = m_hc
        self.m_sideflg = m_sideflg
        self.m_sr = m_sr
        self.m_skey = m_skey
        self.m_no = m_no
        self.m_yr = m_yr

    def safe_request_with_retry(self, request_func, retries=3, delay=2):
        for attempt in range(retries):
            try:
                return request_func()
            except Exception as e:
                return {"result": "error", "message": "No Record Found."}

    def captcha(self):
        url = 'https://bombayhighcourt.nic.in/case_query.php'
        headers = {'referer': 'https://bombayhighcourt.nic.in/index.php', **self.headers}
        response = self.safe_request_with_retry(lambda: self.session.get(url, headers=headers, proxies=self.session.proxies))
        if isinstance(response, dict): return response
        soup = bs(response.text, 'html.parser')
        self.captchas = soup.find('img', {'id': "captchaimg"})['src'].split('=')[-1]
        self.csrf_name = soup.find('input', {'name': 'CSRFName'})['value']
        self.csrf_token = soup.find('input', {'name': 'CSRFToken'})['value']

    def misc_info(self):
        cap = self.captcha()
        if isinstance(cap, dict): return cap
        form_data = {"CSRFName": self.csrf_name,"CSRFToken": self.csrf_token,"submitflg": "C", "m_hc": self.m_hc,"m_sideflg": self.m_sideflg, "m_sr": self.m_sr,"m_skey": self.m_skey, "m_no": self.m_no,"m_yr": self.m_yr, "captchaflg": "", "captcha_code": self.captchas, "frmdate": "", "todate": "", "captcha_code_cq": ""}

        headers = {**self.headers, 'referer': 'https://bombayhighcourt.nic.in/case_query.php'}
        response = self.safe_request_with_retry(lambda: self.session.post("https://bombayhighcourt.nic.in/casequery_action.php", headers=headers, data=form_data, proxies=self.session.proxies))
        if isinstance(response, dict): return response
        soup = bs(response.text, 'html.parser')
        try:
            csrf_name_m = soup.find('input', {'name': 'CSRFName'})['value']
            csrf_token_m = soup.find('input', {'name': 'CSRFToken'})['value']
            m_fil_no = soup.find('input', {'name': 'm_fil_no'})['value']
            m_reg_no = soup.find('input', {'name': 'm_reg_no'})['value']
        except TypeError:
            return {"result": "error", "message": "No Record Found."}

        mis_formdata = {"CSRFName": csrf_name_m,"CSRFToken": csrf_token_m,"m_skey": self.m_skey,"m_no": self.m_no, "m_yr": self.m_yr, "m_hc": self.m_hc, "m_petno": "","m_resno": "", "m_padv": "","m_radv": "","m_sr": self.m_sr,"m_sideflg": self.m_sideflg, "m_fil_no": m_fil_no,"m_reg_no": m_reg_no,"hide_partyname": "N" }

        headers = {**self.headers, 'referer': 'https://bombayhighcourt.nic.in/casequery_action.php'}
        res = self.safe_request_with_retry(lambda: self.session.post("https://bombayhighcourt.nic.in/csubjectinfo.php", headers=headers, data=mis_formdata, proxies=self.session.proxies))
        if isinstance(res, dict): return res
        datas = bs(res.text, 'html.parser').find('table', {'class': "table1 table-bordered12"})
        if not datas:
            return {"result": "error", "message": "No Record Found."}

        sol = dict()
        sol['case_stamp_no'] = datas.select_one('tr:nth-child(2) b').text.split('&')[0].split(':-')[-1].strip()
        sol['reg_no'] = datas.select_one("tr:nth-child(2) b").text.split('&')[-1].split(':-')[-1].strip()
        sol['subjectcategory'] = datas.select_one("tr:nth-child(4) .text-center").text.split(':-')[-1].strip().replace(
            '   ', ' ')
        document = dict()
        document['sno'] = [k.get_text(strip=True) for k in datas.select(".text-center + .text-center td:nth-child(1)")]
        document['document_no'] = [k.get_text(strip=True) for k in datas.select(".text-center + .text-center td:nth-child(2)")]
        document['date_of_receving'] = [k.get_text(strip=True) for k in datas.select(".text-center + .text-center td:nth-child(3)")]
        document['field_by'] = [k.get_text(strip=True).replace('\n', '') for k in datas.select(".text-center + .text-center td:nth-child(4)")]
        document['name_of_advocate'] = [k.get_text(strip=True) for k in datas.select(".text-center + .text-center td:nth-child(5)")]
        document['document_field'] = [k.get_text(strip=True) for k in datas.select(".text-center + .text-center td:nth-child(6)")]
        document['fees'] = [k.get_text(strip=True) for k in datas.select(".text-center + .text-center td:nth-child(7)")]
        document['remarks'] = [k.get_text(strip=True) for k in datas.select(".text-center + .text-center td:nth-child(8)")]

        documents2 = [{'sno': sno, 'document_no': doc_no, 'date_of_receving': date, 'field_by': field_by, 'name_of_advocate': advocate, 'document_field': doc_field, 'fees': fee, 'remarks': remark}
                for sno, doc_no, date, field_by, advocate, doc_field, fee, remark in zip(
                document['sno'], document['document_no'], document['date_of_receving'], document['field_by'],
                document['name_of_advocate'], document['document_field'], document['fees'], document['remarks'])]
        sol['documents'] = documents2
        return sol

    def paper_case(self):
        cap = self.captcha()
        if isinstance(cap, dict): return cap
        form_data = {"CSRFName": self.csrf_name,"CSRFToken": self.csrf_token, "submitflg": "C", "m_hc": self.m_hc, "m_sideflg": self.m_sideflg,"m_sr": self.m_sr, "m_skey": self.m_skey, "m_no": self.m_no,"m_yr": self.m_yr, "captchaflg": "","captcha_code": self.captchas,  "frmdate": "", "todate": "",  "captcha_code_cq": ""}
        headers = {**self.headers, 'referer': 'https://bombayhighcourt.nic.in/case_query.php'}
        response = self.safe_request_with_retry(lambda: self.session.post("https://bombayhighcourt.nic.in/casequery_action.php", headers=headers, data=form_data, proxies=self.session.proxies))
        if isinstance(response, dict): return response
        soup = bs(response.text, 'html.parser')
        try:
            csrf_name_p = soup.find('input', {'name': 'CSRFName'})['value']
            csrf_token_p = soup.find('input', {'name': 'CSRFToken'})['value']
            m_fil_no_p = soup.find('input', {'name': 'm_fil_no'})['value']
            m_reg_no_p = soup.find('input', {'name': 'm_reg_no'})['value']
        except TypeError:
            return {"result": "error", "message": "No Record Found."}
        info_formdata = { "CSRFName": csrf_name_p,"CSRFToken": csrf_token_p,"m_skey": self.m_skey, "m_no": self.m_no,"m_yr": self.m_yr, "m_hc": self.m_hc,"m_petno": "", "m_resno": "","m_padv": "", "m_radv": "", "m_sr": self.m_sr, "m_sideflg": self.m_sideflg,"m_fil_no": m_fil_no_p,"m_reg_no": m_reg_no_p,  "hide_partyname": "N" }
        headers = {**self.headers, 'referer': 'https://bombayhighcourt.nic.in/casequery_action.php'}
        response = self.safe_request_with_retry(lambda: self.session.post("https://bombayhighcourt.nic.in/cindexinfo.php", headers=headers, data=info_formdata, proxies=self.session.proxies))
        if isinstance(response, dict): return response
        soup = bs(response.text, 'html.parser')
        datas = soup.find("table", {'class': 'table table-border'})
        if not datas:
            return {"result": "error", "message": "No Record Found."}
        sols = dict()
        sols['case_stamp_no'] = datas.select_one("td.text-center b").text.split('&')[0].split(':-')[-1].strip()

        reg_no_raw = datas.select_one("td.text-center b").text.split('&')
        reg_no = reg_no_raw[1] if len(reg_no_raw) > 1 else ''
        sols['reg_no'] = reg_no.split(':-')[-1].strip()

        docum = dict()
        docum['document'] = [k.get_text(strip=True) for k in datas.select(".text-center + .text-center td:nth-child(1)")]
        docum['filing_date'] = [k.get_text(strip=True) for k in datas.select(".text-center + .text-center td:nth-child(2)")]
        docum['start_page'] = [k.get_text(strip=True) for k in datas.select(".text-center + .text-center td:nth-child(3)")]
        docum['end_page'] = [k.get_text(strip=True) for k in datas.select(".text-center + .text-center td:nth-child(4)")]
        docum['no_of_pages'] = [k.get_text(strip=True) for k in datas.select(".text-center + .text-center td:nth-child(5)")]
        filed_by = [k.get_text(strip=True) for k in datas.select(".text-center + .text-center td:nth-child(6)")]

        sols['document'] = [ {'document': doc, 'filing_date': filing_date, 'start_page': start, 'end_page': end, 'no_of_pages': pages,  'filed_by': filed}
            for doc, filing_date, start, end, pages, filed in
            zip(docum['document'], docum['filing_date'], docum['start_page'], docum['end_page'], docum['no_of_pages'],filed_by)]
        return sols

    def case_main_info(self):
        def remove_empty(lst):
            return [item for item in lst if item.strip()]
        cap = self.captcha()
        if isinstance(cap, dict):
            return cap
        form_data = {"CSRFName": self.csrf_name,"CSRFToken": self.csrf_token,"submitflg": "C", "m_hc": self.m_hc,"m_sideflg": self.m_sideflg,"m_sr": self.m_sr,"m_skey": self.m_skey,"m_no": self.m_no,"m_yr": self.m_yr,"captchaflg": "","captcha_code": self.captchas,  "frmdate": "","todate": "","captcha_code_cq": ""}
        headers = {**self.headers,'referer': 'https://bombayhighcourt.nic.in/case_query.php' }
        response = self.safe_request_with_retry(lambda: self.session.post("https://bombayhighcourt.nic.in/casequery_action.php", headers=headers, data=form_data,proxies=self.session.proxies))
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
                            sol['petitioner'] = [opt.text.strip() for opt in tds[j + 1].find_all('option')]

                    elif 'respondent' in text:
                        if j + 1 < len(tds):
                            sol['respondent'] = [opt.text.strip() for opt in tds[j + 1].find_all('option')]

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

                    elif 'act' in text:
                        sol['act'] = text.split(':-')[-1].strip()

                    elif 'under' in text:
                        if j + 1 < len(tds):
                            sol['under_section'] = tds[j + 1].text.strip()

                    elif 'next date' in text:
                        sol['next_date'] = text.strip().split(':-')[-1].strip()
                    elif 'last coram' in text:

                        last_coram_row = [td.text.split(':-')[-1].strip() for td in tds if 'last coram' ]
                        coram_extra = []

                        if i + 1 < len(rows):
                            next_tds = rows[i + 1].find_all('td')
                            coram_extra = [td.text.strip() for td in next_tds if "hon'ble" in td.text.lower()]

                        sol['last_coram'] = last_coram_row + coram_extra
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

                    # elif 'coram' in text:
                    #     coram_row = [td.text.strip() for td in tds if 'coram']
                    #     coram_extra = []
                    #
                    #     if i + 1 < len(rows):
                    #         next_tds = rows[i + 1].find_all('td')
                    #         coram_extra = [td.text.strip() for td in next_tds if "hon'ble" in td.text.lower()]
                    #
                    #     sol['coram'] = coram_row + coram_extra
                    #     i += 1

                i += 1
            return sol

        except Exception as e:
            return {"result": "error", "message": f"Exception occurred: {str(e)}"}
