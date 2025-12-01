import random
import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime
from common_code import proxy_implement

prox_mood = proxy_implement.get_requests_proxy()

bench_ids = {"01": "JBP", "02": "IND", "03": "GWL"}

def safe_text(elem):
    return elem.text.strip() if elem else ""

def url_parsing(bench, case_type, case_no, case_year):
    try:
        bench_id = bench_ids.get(bench)
        if not bench_id:
            return {"status": f"Invalid bench code: {bench}"}
        sid_ran = str(random.randint(100000000, 999999999))
        main_url = f'https://mphc.gov.in/php/hc/casestatus/casestatus_pro.php?id={bench_id}&opt=1&lst_case={case_type}&txtno={case_no}&txtyear={case_year}&f=0.2222&sid={sid_ran}'
        headers = {'referer': 'https://mphc.gov.in/case-status', 'X-Requested-With': 'XMLHttpRequest'}

        response = requests.get(main_url, headers=headers, proxies=prox_mood)

        if response.status_code != 200:
            return {"status": f"HTTP Error: {response.status_code}"}

        soup = bs(response.text, 'html.parser')
        table = soup.select_one('table.newcss')
        if not table:
            return {"status": "No Record"}

        earlier_cour = table.find_next('table')
        listing = [k for k in earlier_cour.find_all_next('table') if 'Hearing Date' in str(k)] if earlier_cour else []
        judgedment_data = [k for k in earlier_cour.find_all_next('table') if 'Judgement/Orders' in str(k)] if earlier_cour else []
        documnents = [k for k in earlier_cour.find_all_next('table') if 'Document No.' in str(k)] if earlier_cour else []

        return scrape_data(table, earlier_cour, listing, judgedment_data,documnents)

    except Exception as e:
        return {"status": f"Error: {str(e)}"}

def scrape_data(html_content, earlier_cour, listing, judgedment_data,documnents):
    sol = dict()
    try:
        if not html_content:
            return {"error": "html_content is None"}

        caseno_el = next((k.find_next('td') for k in html_content.find_all('td') if 'Case No.' in str(k)), None)
        if caseno_el:
            caseno_text = safe_text(caseno_el)
            caseno_parts = caseno_text.split('Registered On')[0].split('(')[-1].split(')')
            if len(caseno_parts) >= 2:
                case_info = caseno_parts[1].split('/')
                sol['case_type'] = caseno_parts[0].strip()
                sol['case_no'] = case_info[0].strip()
                sol['case_year'] = case_info[1].strip()
                try:
                    filled_date = caseno_text.split('Registered On')[-1].strip()
                    filled_date = datetime.strptime(filled_date, "%d-%m-%Y")
                    sol['date_of_filing'] = filled_date.strftime("%Y-%m-%d")
                except:
                    sol['date_of_filing'] = ''
                # filled_date = caseno_text.split('Registered On')[-1].strip()
                # filled_date = datetime.strptime(filled_date.strip(), "%d-%m-%Y")
                # sol['date_of_filing'] = filled_date.strftime("%Y-%m-%d")

        sol['bench'] = safe_text(next((td.find_next('td') for td in html_content.find_all('td') if td.get_text(strip=True) == 'Bench'), None))

        peti_el = next((k.find_next('td') for k in html_content.find_all('td') if 'Petitioner(s)' in str(k)), None)
        sol['petitioner_name'] = [p.text.replace('\xa0', ' ').strip() for p in peti_el.find_all('p')] if peti_el else []

        resp_el = next((k.find_next('td') for k in html_content.find_all('td') if 'Respondent(s)' in str(k)), None)
        sol['respondent_name'] = [p.text.replace('\xa0', ' ').strip() for p in resp_el.find_all('p')] if resp_el else []

        pet_adv_el = next((k.find_next('td') for k in html_content.find_all('td') if 'Petitioner Advocate(s)' in str(k)), None)
        sol['petitioner_adv'] = [p.text.strip() for p in pet_adv_el.find_all('p')] if pet_adv_el else []

        resp_adv_el = next((k.find_next('td') for k in html_content.find_all('td') if 'Respondent. Advocate(s)' in str(k)), None)
        sol['respondent_adv'] = [p.text.strip() for p in resp_adv_el.find_all('p')] if resp_adv_el else []

        tenta_td = next((k.find_next('td') for k in html_content.find_all('td') if 'Tentative date' in str(k)), None)
        if tenta_td:
            font = tenta_td.find('font')
            if font:
                try:
                    date_obj = datetime.strptime(font.text.strip(), "%d-%m-%Y")
                    sol['Tentative_date'] = date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    sol['Tentative_date'] = None

        last_list_td = next((k.find_next('td') for k in html_content.find_all('td') if 'Last Listed On' in str(k)), None)
        last_font = None
        if last_list_td:
            last_font = last_list_td.find('font')
            if last_font:
                try:
                    last_list_date = datetime.strptime(last_font.text.strip(), "%d-%m-%Y")
                    sol['last_listed_on_date'] = last_list_date.strftime("%Y-%m-%d")
                except ValueError:
                    sol['last_listed_on_date'] = None

        judge_name = [k.find_next('td').text.strip() for k in html_content.find_all('td') if 'Last Listed On' in str(k)]
        if judge_name:
            judge_name = judge_name[0]
            if last_font:
                sol['judge_name'] = judge_name.replace(last_font.text, '').strip()

        last_order = next((k.find_next('td') for k in html_content.find_all('td') if 'Last Order' in str(k)), None)
        sol['last_order'] = last_order.text.strip() if last_order else ''

        status_el = next((k.find_next('td') for k in html_content.find_all('td') if 'Status' in str(k)), None)
        status_text = safe_text(status_el).lower()
        if 'pending' in status_text:
            sol['status'] = 'Pending'
        elif status_text:
            sol['status'] = 'Disposed'
            try:
                disposal_info = status_text.split('(')[-1].split(',')[0]
                disposal_date_str = disposal_info.split(':')[-1].strip().split()[0]
                disposal_date_obj = datetime.strptime(disposal_date_str, "%d-%m-%Y")
                sol['disposal_date'] = disposal_date_obj.strftime("%Y-%m-%d")
            except Exception:
                sol['disposal_date'] = None
        else:
            sol['status'] = 'Pending'

        district_el = None
        for k in html_content.find_all('td'):
            if k.get_text(strip=True) == "District":
                district_el = k.find_next('td')
                break

        sol['District'] = safe_text(district_el) if district_el else ""
        stage = next((k.find_next('td') for k in html_content.find_all('td') if 'Stage' in str(k)), None)
        if stage:
            sol['stage'] = str(stage).split('<br/>')[0].split('>')[-1].strip()

        underlines = next((k.find_next('td').text.strip().replace('|', '') for k in html_content.find_all('td') if 'U/Section' in str(k)), None)
        sol['under_section'] = underlines if underlines else ''

        act_header = html_content.find('td', string=lambda text: text and 'Act' in text)
        if act_header:
            act_td = act_header.find_next('td')
            act_list = list(act_td.stripped_strings)
            sol['act'] = act_list if act_list else ''

        classification_td = next((k.find_next('td') for k in html_content.find_all('td') if 'Category' in k.get_text()),None)
        sol['classification'] = [line.strip() for line in classification_td.get_text(separator='\n').split('\n') if line.strip()] if classification_td else []


        earli_dict = dict()
        if earlier_cour:
            casenoes = [k.find_next('td').text.strip() for k in earlier_cour.find_all('td') if 'Case No.' in str(k)]
            if casenoes:
                parts = casenoes[0].split('/')
                if len(parts) >= 3:
                    case_types = parts[0]
                    case_values = {'ARBITRATION APPEAL': 'AA', 'ADVISORY BOARD': 'AB', 'ARBITRATION CASE': 'AC',
                                   'ARBITRATION REVISION': 'AR',
                                   'CIVIL REVISION': 'CR', 'CIVIL SUIT': 'CS', 'DEATH REFERENCE': 'DR',
                                   'EXECUTION CASE': 'EC', 'ELECTION PETITION': 'EP', 'FIRST APPEAL': 'FA',
                                   'MISC. APPEAL': 'MA', 'MISC. PETITION': 'MP', 'ORIGINAL APPLICATION': 'OA',
                                   'OBJECTION CASE': 'OC', 'REVIEW CASE': 'RC',
                                   'REVIEW PETITION': 'RP', 'SECOND APPEAL': 'SA', 'TRANSFER APPLICATION': 'TA',
                                   'TAX REFERENCE': 'TR', 'WRIT APPEAL': 'WA', 'WRIT PETITION': 'WP',
                                   'WRIT PETITIONS': 'WP', 'WP(WRIT PETITIONS)': 'WP','CONT(+CONC) CONTEMPT CIVIL' : 'CONC'
                                   }

                    case_types = parts[0]

                    if case_types in case_values:
                        earli_dict['case_type'] = case_values[case_types]
                    else:
                        earli_dict['case_type'] = parts[0]
                    earli_dict['case_type_name'] = parts[0]
                    earli_dict['case_no'] = parts[1]
                    earli_dict['case_year'] = parts[2]

            judge_name = [k.find_next('td').text.strip() for k in earlier_cour.find_all('td') if 'Judge Name' in str(k)]
            if judge_name:
                earli_dict['judge_name'] = judge_name[0].replace("\\", '').strip()

            decision_date = [k.find_next('td').text.strip() for k in earlier_cour.find_all('td') if 'Decision Date' in str(k)]
            earli_dict['decision_date'] = decision_date[0] if decision_date else ''

        sol['earlier_court'] = earli_dict

        listing_result = []
        if listing:
            listing_data = listing[0].find_all('tr')[1:]
            for lis_data in listing_data:
                listing_da = dict()
                listing_date = lis_data.find('td')
                try:
                    listing_dates = datetime.strptime(listing_date.text.strip(), "%d-%m-%Y")
                    listing_da['Hearing_Date'] = listing_dates.strftime("%Y-%m-%d")
                except:
                    listing_da['Hearing_Date'] = listing_date.text.strip()

                coram = listing_date.find_next('td')
                listing_da['Coram'] = coram.text.strip()

                listing_purpose = coram.find_next('td')
                listing_da['Purpose'] = listing_purpose.get_text(separator=' ', strip=True)

                action = listing_purpose.find_next('td')
                listing_da['Action'] = action.text.strip()

                other = action.find_next('td')
                listing_da['Other'] = other.text.strip() if other else ''

                listing_result.append(listing_da)

        # judge_result = []
        # if judgedment_data:
        #     judge_order = judgedment_data[0].find_all('a')
        #     for jug_data in judge_order:
        #         judg_di = dict()
        #         pdf = jug_data['href']
        #         judg_di['pdf_link'] = 'https://mphc.gov.in' + str(pdf).replace('./upload','/upload')
        #         dates =  'https://mphc.gov.in' + str(pdf).replace('./upload','/upload')
        #         order_date = jug_data.text.replace('Dt.', 'Date -').strip()
        #         order_date = order_date.split('Order Date -')[1]
        #         if order_date:
        #             judg_di['order_date'] = 'Order Date - ' + str(order_date)
        #         else :
        #             date_se = dates.split('Order_')[-1].split('.pdf')[0]
        #             date_obj = datetime.strptime(date_se, "%d-%b-%Y")
        #             formatted_date = date_obj.strftime("%d-%m-%Y")
        #             judg_di['order_date'] = 'Order Date - ' + str(formatted_date)
        #
        #         judge_result.append(judg_di)
        #     sol['Judgement'] = judge_result
        # print(sol['Judgement'])

        judge_result = []
        if judgedment_data:
            judge_order = judgedment_data[0].find_all('a')
            for jug_data in judge_order:
                judg_di = dict()

                pdf = jug_data['href']
                judg_di['pdf_link'] = 'https://mphc.gov.in' + str(pdf).replace('./upload', '/upload')
                dates = 'https://mphc.gov.in' + str(pdf).replace('./upload', '/upload')
                order_date_text = jug_data.text.replace('Dt.', 'Date -').strip()
                if 'Order Date -' in order_date_text:
                    parts = order_date_text.split('Order Date -', 1)
                    order_date = parts[1].strip() if len(parts) > 1 else ''
                else:
                    order_date = ''
                if order_date:
                    judg_di['order_date'] = 'Order Date - ' + str(order_date)
                else:
                    try:
                        date_se = dates.split('Order_')[-1].split('.pdf')[0]
                        date_obj = datetime.strptime(date_se, "%d-%b-%Y")
                        formatted_date = date_obj.strftime("%d-%m-%Y")
                        judg_di['order_date'] = 'Order Date - ' + str(formatted_date)
                    except Exception:
                        judg_di['order_date'] = 'Order Date - '

                judge_result.append(judg_di)
            sol['Judgement'] = judge_result

        documnent_no = []
        if documnents:
            doc_datas = documnents[0].find_all('tr')[1:]
            for doc in doc_datas:
                doc_dict = dict()
                Document_No = doc.find('td')
                doc_dict['Document_No'] = Document_No.text

                doc_type = Document_No.find_next('td')
                doc_dict['Document_Type'] = doc_type.text if doc_type else ''
                filed_by = doc_type.find_next('td')
                doc_dict['Filed_By'] = filed_by.text if filed_by else ''
                filed_date = filed_by.find_next('td')
                doc_dict['Filing_Date'] = filed_date.text

                documnent_no.append(doc_dict)

        sol['other_hc_details'] = [{'documents_details': documnent_no,'listing_details':listing_result}]

        return sol

    except Exception as e:
        return {'error': str(e) + ' [scrape_data]'}
