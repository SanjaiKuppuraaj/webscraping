import time
import requests
import json
from bs4 import BeautifulSoup as bs
import pytesseract
from PIL import Image
from io import BytesIO
from datetime import datetime
import re
from common_code import common_module as cm

sessions = requests.Session()


class Ksat_Scraper:
    def __init__(self, establishcode, apptype, case_num, case_year):

        self.session = requests.Session()
        if cm.USE_PROXY:
            proxy_url = cm.get_proxy()
            self.session.proxies.update({"http": proxy_url, "https": proxy_url})

        self.establishcode = establishcode
        self.apptype = str(apptype)
        self.case_num = case_num
        self.case_year = case_year
        self.result_datas = {}
        self.hearings = {"next_hearing_date": []}
        self.token = None
        self.captcha_text = None

    def captcha(self):
        captcha_response = sessions.get('https://ksat.karnataka.gov.in/ksatweb/public/captcha-image',
                                        proxies=self.session.proxies)
        pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
        image = Image.open(BytesIO(captcha_response.content))
        gray = image.convert("L")
        bw = gray.point(lambda x: 0 if x < 150 else 255, '1')
        raw_text = pytesseract.image_to_string(bw, config='--psm 7')
        self.captcha_text = re.sub(r'[^A-Z0-9]', '', raw_text.upper())

    def get_csrf_token(self):
        csrf_response = sessions.get('https://ksat.karnataka.gov.in/ksatweb/public/getcasestatus',
                                     proxies=self.session.proxies)
        soup = bs(csrf_response.text, 'html.parser')
        token_element = soup.find('input', {'name': '_token'})
        self.token = token_element['value'].strip() if token_element else None

    def datas(self):
        max_attempts = 7
        for attempt in range(max_attempts):
            try:
                self.captcha()
                self.get_csrf_token()
                form_data = {"_token": self.token, "establishcode": self.establishcode, "apptype": self.apptype,
                             "appnum": self.case_num, "applyear": self.case_year, "entered_captcha": self.captcha_text}
                headers = {'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': 'Mozilla/5.0'}
                submit_url = 'https://ksat.karnataka.gov.in/ksatweb/public/appstatusresult'
                response = sessions.post(submit_url, data=form_data, headers=headers, proxies=self.session.proxies)
                case_data = self.parse_case_status(response, form_data["appnum"])

                if case_data and case_data.get("case_status"):
                    hearing_data = self.parse_hearing_status(response)
                    final_result = {"result": case_data}
                    if hearing_data:
                        final_result["result"].update(hearing_data)
                    case_updates = self.case_updates(response)
                    if case_updates:
                        final_result['result'].update({'judgement': case_updates})
                    return final_result
                else:
                    print({"result": "error", "message": "No Record Found."})

            except Exception as e:
                print({"result": "error", "message": "No Record Found."})

        return {"result": "error", "message": "No Record Found."}

    def parse_case_status(self, html, case_no):
        soup = bs(html.text, 'html.parser')
        case_info = soup.find('div', {'id': 'caseinfo'})

        if case_info:
            case_info = case_info.find_next('div', {'class': 'accordion_body'})
            datas = case_info.find('table') if case_info and case_info.find('table') else None

            if datas:
                self.result_datas['case_number'] = f'{self.apptype}/{self.case_num}/{self.case_year}'
                self.result_datas['case_type'] = self.apptype
                self.result_datas['case_no'] = self.case_num
                self.result_datas['case_year'] = self.case_year
                self.result_datas['case_status'] = datas.find('td', {'class': 'text_animate'}).text.strip()

                date = next((k.find_next('td').text for k in datas.find_all('td') if "Filling Date" in str(k)), None)
                self.result_datas['case_filed_date'] = datetime.strptime(date, "%d/%m/%Y").strftime(
                    "%d-%m-%Y") if date else ""

                self.result_datas['classification'] = next(
                    (k.find_next('td').text for k in datas.find_all('td') if "Application Category" in str(k)), "")
                last_hearing = next(
                    (k.find_next('td').text.strip() for k in datas.find_all('td') if "Hearing Date" in str(k)), "")
                self.result_datas['case_last_action_date'] = datetime.strptime(last_hearing, "%d/%m/%Y").strftime(
                    "%d-%m-%Y") if last_hearing else ""

                self.result_datas['petitioner'] = next(
                    (k.find_next('td').text.split('\n')[0] for k in datas.find_all('td') if
                     "Name of the Applicant" in str(k)), "")
                petitioner_adv = [k.find_next('td') for k in datas.find_all('td') if 'Applicant Advocate' in k]
                for k in petitioner_adv:
                    petitioner_adv = str(k).replace('<br/>', ' ').replace('</td>', '').replace('<td>', '')
                    self.result_datas['petitioner_adv'] = petitioner_adv if petitioner_adv else ''

                self.result_datas['respondent'] = next(
                    (k.find_next('td').text.split('\n')[0] for k in datas.find_all('td') if
                     "Name of the Respondent" in str(k)), "")
                respondent_adv = [k.find_next('td') for k in datas.find_all('td') if 'Name of the Respondent' in k]
                for j in respondent_adv:
                    self.result_datas['respondent_adv'] = str(j).split('</td>')[1].replace('<td>', '').replace('<br/>',
                                                                                                               ' ').replace(
                        '\n', '')

                self.result_datas[
                    'case_title'] = f"{self.result_datas['petitioner']} V/s {self.result_datas['respondent']}"
                self.result_datas['application_id'] = next(
                    (k.find_next('td').text.split('\n')[0] for k in datas.find_all('td') if
                     "Un Application ID" in str(k)), "")

        return self.result_datas if self.result_datas else None

    def parse_hearing_status(self, response):
        soup = bs(response.text, 'html.parser')
        datas = soup.find('div', {'id': 'searchcontent_1'}).find('table', {
            'class': 'table table-bordered table-striped table-hover'})
        hear_datas = [k.find_next('td').text for k in datas.find_all('td') if 'Next Hearing Date' in str(k)][0]

        hearing_modal = soup.find('div', {'id': 'hearingModal'})
        next_hearing_date = []
        if hearing_modal:
            hearing_rows = hearing_modal.find('table').find_all('tbody')
            next_datas_test = [tds[-1].get_text(strip=True) for k in hearing_rows if k for tr in k.find_all('tr') if
                               (tds := tr.find_all('td'))]
            next_stage_test = [tds[3].get_text(strip=True) for k in hearing_rows if k for tr in k.find_all('tr') if
                               (tds := tr.find_all('td'))]

            def normalize_date(date_str):
                for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
                    try:
                        return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                    except ValueError:
                        continue
                return date_str

            next_hearing_date = [{"next_hearing": normalize_date(date).replace('---', ''), "stage": stage} for
                                 date, stage in zip(next_datas_test, next_stage_test)]
        return {"next_hearing_date_list": next_hearing_date[::-1], 'next_hearing_date': hear_datas.replace('----', '')}

    def case_updates(self, response):
        judgement_details = self.judgement_details(response)
        order_details = self.order_details(response)
        case_updates = []
        if judgement_details:
            case_updates.extend(judgement_details.get('judgement', []))
        if order_details:
            case_updates.extend(order_details.get('order_details', []))
        return case_updates

    def judgement_details(self, response):
        soup = bs(response.text, 'html.parser')
        datas = soup.find('div', {'id': 'searchcontent_4'}).find('tbody')
        datas = datas.find_all('tr')
        jud_data = []
        for j_details in datas:
            sol = dict()
            application_no = j_details.find('td')
            # sol['application_no'] = application_no.text if application_no else ''
            # sol['document_type'] = 'Judgement'
            subject = application_no.find_next('td')
            # sol['subject'] = subject.text if subject else ''
            applicant_name = subject.find_next('td')
            # sol['applicant_name'] = applicant_name.text if applicant_name else ''
            respondent_name = applicant_name.find_next('td')
            # sol['respondent_name'] = respondent_name.text if respondent_name else ''
            judgement_date = respondent_name.find_next('td')
            sol['date'] = judgement_date.text if judgement_date else ''
            sol['link'] = [k['href'] for k in judgement_date.find_next('td').find_all('a') if 'https' in str(k)][0]
            sol['judgement'] = 'Judgement'
            jud_data.append(sol)
        return {'judgement': jud_data}

    def order_details(self, response):
        soup = bs(response.text, 'html.parser')
        datas = soup.find('div', {'id': 'searchcontent_5'}).find_all('tbody')
        order_detail = []
        for ord_de in datas:
            for order_der in ord_de.find_all('tr'):
                sol = dict()
                application_no = order_der.find('td')
                # sol['application_no'] = application_no.text if application_no else ''
                # sol['document_type'] = 'Order'
                subject = application_no.find_next('td')
                # sol['subject'] = subject.text if subject else ''
                applicant_name = subject.find_next('td')
                # sol['applicant_name'] = applicant_name.text if applicant_name else ''
                respondent_name = applicant_name.find_next('td')
                # sol['respondent_name'] = respondent_name.text if respondent_name else ''
                bench = respondent_name.find_next('td')
                # sol['bench'] = bench.text if bench else ''
                order_date = bench.find_next('td')
                sol['date'] = order_date.text if order_date else ''
                order_type = order_date.find_next('td')
                sol['order_type'] = order_type.text if order_type else ''
                sol['link'] = [k['href'] for k in order_type.find_next('td').find_all('a') if 'https' in str(k)][0]
                sol['judgement'] = 'Order'
                order_detail.append(sol)

        return {'order_details': order_detail}











# import time
# import requests
# import json
# from bs4 import BeautifulSoup as bs
# import pytesseract
# from PIL import Image
# from io import BytesIO
# from datetime import datetime
# import re
# from common_code import common_module as cm
#
# sessions = requests.Session()
#
# class Ksat_Scraper:
#     def __init__(self, establishcode, apptype, case_num, case_year):
#
#         self.session = requests.Session()
#         if cm.USE_PROXY:
#             proxy_url = cm.get_proxy()
#             self.session.proxies.update({"http": proxy_url, "https": proxy_url})
#
#         self.establishcode = establishcode
#         self.apptype = str(apptype)
#         self.case_num = case_num
#         self.case_year = case_year
#         self.result_datas = {}
#         self.hearings = {"next_hearing_date": []}
#         self.token = None
#         self.captcha_text = None
#
#     def captcha(self):
#         captcha_response = sessions.get('https://ksat.karnataka.gov.in/ksatweb/public/captcha-image', proxies=self.session.proxies)
#         pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
#         image = Image.open(BytesIO(captcha_response.content))
#         gray = image.convert("L")
#         bw = gray.point(lambda x: 0 if x < 150 else 255, '1')
#         raw_text = pytesseract.image_to_string(bw, config='--psm 7')
#         self.captcha_text = re.sub(r'[^A-Z0-9]', '', raw_text.upper())
#
#     def get_csrf_token(self):
#         csrf_response = sessions.get('https://ksat.karnataka.gov.in/ksatweb/public/getcasestatus', proxies=self.session.proxies)
#         soup = bs(csrf_response.text, 'html.parser')
#         token_element = soup.find('input', {'name': '_token'})
#         self.token = token_element['value'].strip() if token_element else None
#
#     def datas(self):
#         max_attempts = 7
#         for attempt in range(max_attempts):
#             try:
#                 self.captcha()
#                 self.get_csrf_token()
#                 form_data = { "_token": self.token,"establishcode": self.establishcode, "apptype": self.apptype, "appnum": self.case_num, "applyear": self.case_year,"entered_captcha": self.captcha_text }
#                 headers = {'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': 'Mozilla/5.0'}
#                 submit_url = 'https://ksat.karnataka.gov.in/ksatweb/public/appstatusresult'
#                 response = sessions.post(submit_url, data=form_data, headers=headers, proxies=self.session.proxies)
#                 case_data = self.parse_case_status(response, form_data["appnum"])
#
#                 if case_data and case_data.get("case_status"):
#                     hearing_data = self.parse_hearing_status(response)
#                     final_result = {"result": case_data}
#                     # if hearing_data and hearing_data.get("next_hearing_date"):
#                     #     final_result["result"].update(hearing_data)
#                     if hearing_data:
#                         final_result["result"].update(hearing_data)
#                     return final_result
#                 else:
#                     print({"result": "error", "message": "No Record Found."})
#
#             except Exception as e:
#                 print({"result": "error", "message": "No Record Found."})
#
#         return {"result": "error", "message": "No Record Found."}
#
#     def parse_case_status(self, html, case_no):
#         soup = bs(html.text, 'html.parser')
#         case_info = soup.find('div', {'id': 'caseinfo'})
#
#         if case_info:
#             case_info = case_info.find_next('div', {'class': 'accordion_body'})
#             datas = case_info.find('table') if case_info and case_info.find('table') else None
#
#             if datas:
#                 self.result_datas['case_number'] = f'{self.apptype}/{self.case_num}/{self.case_year}'
#                 self.result_datas['case_type'] = self.apptype
#                 self.result_datas['case_no'] = self.case_num
#                 self.result_datas['case_year'] = self.case_year
#                 self.result_datas['case_status'] = datas.find('td', {'class': 'text_animate'}).text.strip()
#
#                 date = next((k.find_next('td').text for k in datas.find_all('td') if "Filling Date" in str(k)), None)
#                 self.result_datas['case_filed_date'] = datetime.strptime(date, "%d/%m/%Y").strftime("%d-%m-%Y") if date else ""
#
#                 self.result_datas['classification'] = next((k.find_next('td').text for k in datas.find_all('td') if "Application Category" in str(k)), "")
#                 last_hearing = next((k.find_next('td').text.strip() for k in datas.find_all('td') if "Hearing Date" in str(k)), "")
#                 self.result_datas['case_last_action_date'] = datetime.strptime(last_hearing, "%d/%m/%Y").strftime("%d-%m-%Y") if last_hearing else ""
#
#                 self.result_datas['petitioner'] = next((k.find_next('td').text.split('\n')[0] for k in datas.find_all('td') if "Name of the Applicant" in str(k)), "")
#                 petitioner_adv = [k.find_next('td') for k in datas.find_all('td') if 'Applicant Advocate' in k]
#                 for k in petitioner_adv:
#                     petitioner_adv = str(k).replace('<br/>',' ').replace('</td>','').replace('<td>','')
#                     self.result_datas['petitioner_adv'] = petitioner_adv if petitioner_adv else ''
#
#                 self.result_datas['respondent'] = next((k.find_next('td').text.split('\n')[0] for k in datas.find_all('td') if "Name of the Respondent" in str(k)), "")
#                 respondent_adv = [k.find_next('td') for k in datas.find_all('td') if 'Name of the Respondent' in k]
#                 for j in respondent_adv:
#                     self.result_datas['respondent_adv'] = str(j).split('</td>')[1].replace('<td>','').replace('<br/>',' ').replace('\n','')
#
#                 self.result_datas['case_title'] = f"{self.result_datas['petitioner']} V/s {self.result_datas['respondent']}"
#                 self.result_datas['application_id'] = next((k.find_next('td').text.split('\n')[0] for k in datas.find_all('td') if "Un Application ID" in str(k)), "")
#
#
#         return self.result_datas if self.result_datas else None
#
#     def parse_hearing_status(self, response):
#         soup = bs(response.text, 'html.parser')
#         datas = soup.find('div', {'id': 'searchcontent_1'}).find('table', {'class': 'table table-bordered table-striped table-hover'})
#         hear_datas = [k.find_next('td').text for k in datas.find_all('td') if 'Next Hearing Date' in str(k)][0]
#
#         hearing_modal = soup.find('div', {'id': 'hearingModal'})
#         next_hearing_date = []
#         if hearing_modal:
#             hearing_rows = hearing_modal.find('table').find_all('tbody')
#             next_datas_test = [tds[-1].get_text(strip=True) for k in hearing_rows if k for tr in k.find_all('tr') if (tds := tr.find_all('td'))]
#             next_stage_test = [tds[3].get_text(strip=True) for k in hearing_rows if k for tr in k.find_all('tr') if (tds := tr.find_all('td'))]
#             def normalize_date(date_str):
#                 for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
#                     try:
#                         return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
#                     except ValueError:
#                         continue
#                 return date_str
#
#             next_hearing_date = [{"next_hearing": normalize_date(date).replace('---',''), "stage": stage} for date, stage in zip(next_datas_test, next_stage_test)]
#         return {"next_hearing_date_list": next_hearing_date[::-1],'next_hearing_date':normalize_date(hear_datas).replace('----','')}