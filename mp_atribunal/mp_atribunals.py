import sys
sys.path.insert(0, '/var/www/mml_python_code')
import time
import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime
from common_code import common_module as cm

class mp_atribunal:
    def __init__(self, case_number):
        self.case_number = case_number
        self.url = 'https://atribunal.mp.gov.in/Causestatus/ajaxPaginationData/0'
        self.headers = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
        self.session = requests.Session()
        if cm.USE_PROXY:
            proxy_url = cm.get_proxy()
            self.session.proxies.update({"http": proxy_url, "https": proxy_url})

    def get_case_data(self, retries=5, delay=3):
        form_datas = {'page': 0, 'flag': 12, 'from_date': '', 'to_date': '', 'search_text': self.case_number}
        for attempt in range(retries):
            try:
                response = self.session.post(self.url, data=form_datas, headers=self.headers,proxies=self.session.proxies,verify=False)
                response.raise_for_status()
                soups = bs(response.text, 'html.parser')
                datas = soups.find('tbody').find_all('td')

                if not datas or len(datas) < 9:
                    return {"error": "No Record Found."}
                sol_datas = dict()
                casenumbers = str(self.case_number).split('-')[0]
                sol_datas['case_type'] = casenumbers if casenumbers else ''
                try:
                    sol_datas['case_filed_date'] = datetime.strptime(datas[4].text.strip(), '%d-%m-%Y').strftime('%Y-%m-%d')
                except ValueError:
                    sol_datas['case_filed_date'] = datas[4].text.strip()
                sol_datas['filing_no'] = datas[1].text.strip()
                sol_datas['casetype_name'] = datas[2].text.strip()
                sol_datas['casestatus_connected'] = datas[3].text.strip().replace('\u200d', '')

                if sol_datas['casestatus_connected'] == 'अवार्ड':
                    sol_datas['case_status'] = 'Disposed'
                else :
                    sol_datas['case_status'] = 'Pending'

                try:
                    sol_datas['next_hearing_date'] = datetime.strptime(datas[5].text.strip(), '%d-%m-%Y').strftime( '%Y-%m-%d')
                except ValueError:
                    sol_datas['next_hearing_date'] = datas[5].text.strip()
                sol_datas['petitioner'] = datas[6].text.strip()
                respondent = str(datas[7].text.strip()).split(',')
                respondent = [k.strip() for k in respondent if k]
                respondent = list(set(respondent)) if respondent else ''
                sol_datas['respondent'] = respondent if respondent else ''
                petitioner_adv = datas[8].text.strip().split(',')
                petitioner_adv = [k.strip() for k in petitioner_adv if k]
                petitioner_adv = list(set(petitioner_adv))
                sol_datas['petitioner_adv'] = petitioner_adv if petitioner_adv else ''
                sol_datas['case_title'] = sol_datas['petitioner'] + ' V/s ' + datas[7].text.strip()
                return {'results': sol_datas}

            except (requests.exceptions.RequestException, ValueError) as e:
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
                else:
                    return {"error": f"Error fetching case data: {str(e)}"}











# import sys
# sys.path.insert(0, '/var/www/mml_python_code')
# import time
# import requests
# from bs4 import BeautifulSoup as bs
# from datetime import datetime
# from common_code import common_module as cm
#
# class mp_atribunal:
#     def __init__(self, case_number):
#         self.case_number = case_number
#         self.url = 'https://atribunal.mp.gov.in/Causestatus/ajaxPaginationData/0'
#         self.headers = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
#         self.session = requests.Session()
#         if cm.USE_PROXY:
#             proxy_url = cm.get_proxy()
#             self.session.proxies.update({"http": proxy_url, "https": proxy_url})
#
#     def get_case_data(self, retries=5, delay=3):
#         form_datas = {'page': 0, 'flag': 12, 'from_date': '', 'to_date': '', 'search_text': self.case_number}
#         for attempt in range(retries):
#             try:
#                 response = self.session.post(self.url, data=form_datas, headers=self.headers,proxies=self.session.proxies,verify=False)
#                 response.raise_for_status()
#                 soups = bs(response.text, 'html.parser')
#                 datas = soups.find('tbody').find_all('td')
#
#                 if not datas or len(datas) < 9:
#                     return {"error": "No Record Found."}
#                 sol_datas = dict()
#                 casenumbers = str(self.case_number).split('-')[0]
#                 sol_datas['case_type'] = casenumbers if casenumbers else ''
#                 try:
#                     sol_datas['case_filed_date'] = datetime.strptime(datas[4].text.strip(), '%d-%m-%Y').strftime('%Y-%m-%d')
#                 except ValueError:
#                     sol_datas['case_filed_date'] = datas[4].text.strip()
#                 sol_datas['filing_no'] = datas[1].text.strip()
#                 sol_datas['casetype_name'] = datas[2].text.strip()
#                 sol_datas['casestatus_connected'] = datas[3].text.strip().replace('\u200d', '')
#                 if sol_datas['casestatus_connected'] == 'अवार्ड':
#                     sol_datas['case_status'] = 'Disposed'
#                 else:
#                     sol_datas['case_status'] = 'Pending'
#                 try:
#                     sol_datas['next_hearing_date'] = datetime.strptime(datas[5].text.strip(), '%d-%m-%Y').strftime( '%Y-%m-%d')
#                 except ValueError:
#                     sol_datas['next_hearing_date'] = datas[5].text.strip()
#                 sol_datas['petitioner'] = datas[6].text.strip()
#                 respondent = str(datas[7].text.strip()).split(',')
#                 respondent = [k.strip() for k in respondent if k]
#                 respondent = list(set(respondent)) if respondent else ''
#                 sol_datas['respondent'] = respondent if respondent else ''
#                 petitioner_adv = datas[8].text.strip().split(',')
#                 petitioner_adv = [k.strip() for k in petitioner_adv if k]
#                 petitioner_adv = list(set(petitioner_adv))
#                 sol_datas['petitioner_adv'] = petitioner_adv if petitioner_adv else ''
#                 sol_datas['case_title'] = sol_datas['petitioner'] + ' V/s ' + datas[7].text.strip()
#                 return {'results': sol_datas}
#
#             except (requests.exceptions.RequestException, ValueError) as e:
#                 if attempt < retries - 1:
#                     time.sleep(delay)
#                     continue
#                 else:
#                     return {"error": f"Error fetching case data: {str(e)}"}
