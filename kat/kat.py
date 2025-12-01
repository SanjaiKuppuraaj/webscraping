import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime
import json
import base64
from datetime import datetime
import os
from common_code import common_module as cm
from flask import request

def convert_to_ymd(date_str: str) -> str:
    if not date_str or not any(ch.isdigit() for ch in date_str):
        return ""
    try:
        date_obj = datetime.strptime(date_str.strip(), "%d/%m/%Y")
        return date_obj.strftime("%Y-%m-%d")
    except Exception:
        return ""

def parse_case_information(case_info):
    sol = dict()
    try:
        table = case_info.find('table').find('tbody')
        status_text = table.find('td', {'class': 'text_animate'}).text.strip()
        sol['case_status'] = status_text.split("(")[0].strip()
        # sol['case_status']
        def extract_value(label):
            return next((td.find_next('td').text.strip() for td in table.find_all('td') if label in td.text), "")
        def extract_date(label):
            date_str = extract_value(label)
            try:
                return datetime.strptime(date_str, "%d/%m/%Y").strftime("%d-%m-%Y")
            except:
                return ""

        sol['case_filed_date'] = extract_date("Filling Date").strip()
        sol['case_last_action_date'] = extract_date("Hearing Date").strip()
        petitioner = extract_value("Name of the Petitioner").split('\n')[0].strip()
        sol['petitioner'] = [petitioner] if petitioner else ''
        respondent = extract_value("Name of the Respondent").split('\n')[0].strip()
        sol['respondent'] = [respondent] if respondent else ''
        sol['case_title'] = str(petitioner +' V/s '+ respondent).strip()
        sol['classification'] = extract_value("Category")
        # sol['bench'] = extract_value("Bench")

        advocates = [td.find_next('td').text.strip() for td in table.find_all('td') if 'Petitioner Advocate' in td.text]
        sol['pet_adv'] = advocates[1] if len(advocates) > 1 else advocates[0] if advocates else ""
        # sol['case_order'] = extract_value("Against Orders")

    except Exception as e:
        return({"result": "error", "message": "No Record Found."})
    return sol

def parse_hearing_dates(hearing_details):
    sol = dict()
    try:
        def extract_value(label):
            return next((td.find_next('td').text.strip() for td in hearing_details.find_all('td') if label in td.text), "")

        def extract_date(label):
            date_str = extract_value(label)
            try:
                return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
            except:
                return ""

        sol['last_hearing_date'] = extract_date('Last Hearing Date')
        sol['next_hearing_date'] = convert_to_ymd(extract_value('Next Hearing Date'))
        # sol['next_stage'] = extract_value('Next Stage')

        sol['next_hearing_date_list'] = []
        tables = hearing_details.find_all('table', {'class': 'table'})

        for table in tables:
            nested_table = table.find_next('table')
            if not nested_table:
                continue
            tbody = nested_table.find_all('tbody')
            for tb in tbody:
                rows = tb.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 5:
                        hearing = {
                            'hearing_date': convert_to_ymd(cells[0].text.strip()),
                            'bench' : cells[1].text.strip(),
                            'court_hall_no' : cells[2].text.strip(),
                            'order_passed' : cells[3].text.strip(),
                            'stage': cells[4].text.strip(),
                            'court_direction' : cells[5].text.replace('  ',' ').replace('\r','').replace('\n','').strip(),
                            'status' : cells[6].text.strip(),
                            'next_date' : convert_to_ymd(cells[7].text.strip())
                                }
                        sol['next_hearing_date_list'].append(hearing)

    except Exception as e:
       return ({"result": "error", "message": "No Record Found."})
    return sol

def parse_judgement_details(judgement, csrf_token, session):
    sol = dict()
    datas = judgement.find('tbody')
    if datas:
        datas = datas.find_all('tr')
        judg_details = []
        output_dir = os.path.join(cm.BASE_DIR_OUTPUTS, 'kat', 'downloads')
        os.makedirs(output_dir, exist_ok=True)

        for jud_data in datas:
            temp = {}
            pet_no = jud_data.find('td')
            # temp['petition_no'] = pet_no.text if pet_no else ''
            subject = pet_no.find_next('td')
            temp['judgement'] = subject.text if subject else ''
            pet_name = subject.find_next('td')
            # temp['petitioner_name'] = pet_name.text.strip() if pet_name else ''
            respo_name = pet_name.find_next('td')
            # temp['respondent_name'] = respo_name.text.strip() if respo_name else ''
            judgment_date = respo_name.find_next('td')
            temp['date_of_upload'] = judgment_date.text if judgment_date else ''

            # extract application id
            app_id = judgment_date.find_next('td').find('a')['onclick']
            app_id = str(app_id).split("('")[-1].replace("')", '').strip()

            # prepare POST to get pdf
            pdf_link = 'https://katservices.karnataka.gov.in/onlineservices/public/downloadJudgement'
            payload = {'_token': csrf_token, 'applicationid': app_id}
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': 'https://katservices.karnataka.gov.in/onlineservices/public/appstatusresult',
                'User-Agent': 'Mozilla/5.0'
            }
            pdf_resp = session.post(pdf_link, data=payload, headers=headers)

            text_data = pdf_resp.text.strip()

            if text_data:
                try:
                    pdf_bytes = base64.b64decode(text_data)
                    filename = f"{app_id.replace('/', '_')}.pdf"
                    filepath = os.path.join(output_dir, filename)
                    with open(filepath, "wb") as f:
                        f.write(pdf_bytes)

                    url_root = request.url_root
                    temp['link'] = f"{url_root}tribunal_kat_casestatus/download/{app_id.replace('/', '_')}"
                except Exception as e:
                    temp_url = f"{request.url_root}tribunal_kat_casestatus/download/{app_id.replace('/', '_')}"
                    temp['link'] = temp_url
                except Exception as e:
                    temp['link'] = ""
            else:
                temp['link'] = ""

            judg_details.append(temp)
        sol['judgement'] = judg_details
    return sol


def main(types,caseno,case_year):
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0','Referer': 'https://katservices.karnataka.gov.in/onlineservices/public/appstatus'}
    url = 'https://katservices.karnataka.gov.in/onlineservices/public/appstatusresult'

    try:
        res = session.get(url, headers=headers)
        soup = bs(res.text, 'html.parser')
        csrf_token = soup.find('meta', {'name': 'csrf-token'})['content']

        post_data = {
            '_token': csrf_token,
            'apptype': types,
            'appnum': caseno,
            'applyear': case_year,
            'captcha': '',
            'entered_captcha': ''
        }

        post_res = session.post(url, headers=headers, data=post_data)
        parsed = bs(post_res.text, 'html.parser')
        accordion = parsed.find('div', {'class': "accordion_container"})

        case_info_div = next((k.find_next('div', {'id': 'searchcontent'}) for k in accordion if 'Case Information' in str(k)), None)
        hearing_div = accordion.find('div', {'id': "searchcontent_1"})
        judgement = accordion.find('div', {'id': 'searchcontent_4'})

        case_data = parse_case_information(case_info_div) if case_info_div else {}
        hearing_data = parse_hearing_dates(hearing_div) if hearing_div else {}

        if judgement:
            judgement_data = parse_judgement_details(judgement, csrf_token, session)
        else:
            judgement_data = {}
        full_data = {**case_data, **hearing_data,**judgement_data}
        return {'result':full_data}
    except Exception as e:
        return {"result": "error", "message": f"An error occurred: {str(e)}"}


# if __name__ == '__main__':
#     result = main("REV.APL", "120", "2010")
#     print(json.dumps(result, indent=2))
















# import requests
# from bs4 import BeautifulSoup as bs
# from datetime import datetime
# import json
#
# from datetime import datetime
#
# def convert_to_ymd(date_str: str) -> str:
#     if not date_str or not any(ch.isdigit() for ch in date_str):
#         return ""
#     try:
#         date_obj = datetime.strptime(date_str.strip(), "%d/%m/%Y")
#         return date_obj.strftime("%Y-%m-%d")
#     except Exception:
#         return ""
#
#
# def parse_case_information(case_info):
#     sol = dict()
#     try:
#         table = case_info.find('table').find('tbody')
#         # sol['case_status'] = table.find('td', {'class': 'text_animate'}).text.strip()
#
#         status_text = table.find('td', {'class': 'text_animate'}).text.strip()
#         sol['case_status'] = status_text.split("(")[0].strip()
#
#         def extract_value(label):
#             return next((td.find_next('td').text.strip() for td in table.find_all('td') if label in td.text), "")
#         def extract_date(label):
#             date_str = extract_value(label)
#             try:
#                 return datetime.strptime(date_str, "%d/%m/%Y").strftime("%d-%m-%Y")
#             except:
#                 return ""
#
#         sol['case_filed_date'] = extract_date("Filling Date").strip()
#         sol['case_last_action_date'] = extract_date("Hearing Date").strip()
#         petitioner = extract_value("Name of the Petitioner").split('\n')[0].strip()
#         sol['petitioner'] = [petitioner] if petitioner else ''
#         respondent = extract_value("Name of the Respondent").split('\n')[0].strip()
#         sol['respondent'] = [respondent] if respondent else ''
#         sol['case_title'] = str(petitioner +' V/s '+ respondent).strip()
#         sol['classification'] = extract_value("Category")
#         # sol['bench'] = extract_value("Bench")
#
#         advocates = [td.find_next('td').text.strip() for td in table.find_all('td') if 'Petitioner Advocate' in td.text]
#         sol['pet_adv'] = [advocates[1]] if len(advocates) > 1 else advocates[0] if advocates else ""
#         # sol['case_order'] = extract_value("Against Orders")
#
#     except Exception as e:
#         return({"result": "error", "message": "No Record Found."})
#     return sol
#
# def parse_hearing_dates(hearing_details):
#     sol = dict()
#     try:
#         def extract_value(label):
#             return next((td.find_next('td').text.strip() for td in hearing_details.find_all('td') if label in td.text), "")
#
#         def extract_date(label):
#             date_str = extract_value(label)
#             try:
#                 return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
#             except:
#                 return ""
#
#         sol['last_hearing_date'] = extract_date('Last Hearing Date')
#         sol['next_hearing_date'] = convert_to_ymd(extract_value('Next Hearing Date'))
#         # sol['next_stage'] = extract_value('Next Stage')
#
#         sol['next_hearing_date_list'] = []
#         tables = hearing_details.find_all('table', {'class': 'table'})
#
#         for table in tables:
#             nested_table = table.find_next('table')
#             if not nested_table:
#                 continue
#             tbody = nested_table.find_all('tbody')
#             for tb in tbody:
#                 rows = tb.find_all('tr')
#                 for row in rows:
#                     cells = row.find_all('td')
#                     if len(cells) >= 5:
#                         hearing = {
#                             'hearing_date': convert_to_ymd(cells[0].text.strip()),
#                             'bench' : cells[1].text.strip(),
#                             'court_hall_no' : cells[2].text.strip(),
#                             'order_passed' : cells[3].text.strip(),
#                             'stage': cells[4].text.strip(),
#                             'court_direction' : cells[5].text.replace('  ',' ').replace('\r','').replace('\n','').strip(),
#                             'status' : cells[6].text.strip(),
#                             'next_date' : convert_to_ymd(cells[7].text.strip())
#                                 }
#                         sol['next_hearing_date_list'].append(hearing)
#
#     except Exception as e:
#        return ({"result": "error", "message": "No Record Found."})
#     return sol
#
# def main(types,caseno,case_year):
#     session = requests.Session()
#     headers = {'User-Agent': 'Mozilla/5.0','Referer': 'https://katservices.karnataka.gov.in/onlineservices/public/appstatus'}
#     url = 'https://katservices.karnataka.gov.in/onlineservices/public/appstatusresult'
#
#     try:
#         res = session.get(url, headers=headers)
#         soup = bs(res.text, 'html.parser')
#         csrf_token = soup.find('meta', {'name': 'csrf-token'})['content']
#
#         post_data = {
#             '_token': csrf_token,
#             'apptype': types,
#             'appnum': caseno,
#             'applyear': case_year,
#             'captcha': '',
#             'entered_captcha': ''
#         }
#
#         post_res = session.post(url, headers=headers, data=post_data)
#         parsed = bs(post_res.text, 'html.parser')
#         accordion = parsed.find('div', {'class': "accordion_container"})
#
#         case_info_div = next((k.find_next('div', {'id': 'searchcontent'}) for k in accordion if 'Case Information' in str(k)), None)
#         hearing_div = accordion.find('div', {'id': "searchcontent_1"})
#
#         case_data = parse_case_information(case_info_div) if case_info_div else {}
#         hearing_data = parse_hearing_dates(hearing_div) if hearing_div else {}
#
#         full_data = {**case_data, **hearing_data}
#         return {'result':full_data}
#     except Exception as e:
#         return ({"result": "error", "message": "No Record Found."})