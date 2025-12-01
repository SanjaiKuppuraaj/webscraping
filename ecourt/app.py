from flask import Flask, Blueprint,request, jsonify
import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime
import json
from common_code import common_module as cm

ecourt_blueprint = Blueprint('ecourt', __name__)

LOG_FILE =cm.BASE_DIR_LOGS + '/'+datetime.now().strftime('%Y-%m-%d')+ '/ecourt_log.txt'

def log_status(cino, status):
    with open(LOG_FILE, 'a') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - CINO: {cino} - Status: {status}\n")

def convert_date(date_str):
    for fmt in ("%d-%m-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str

@ecourt_blueprint.route('', methods=['GET'])
def get_ecourt_data():
    cino = request.args.get('cino')
    typeof = request.args.get('typeof')
    if not cino:
        return jsonify({"status": "error", "message": "No Record Found."}), 400

    url = 'https://indore.dcourts.gov.in/wp-admin/admin-ajax.php'
    headers = {'Accept': 'application/json, text/javascript, */*; q=0.01','Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8','Origin': 'https://indore.dcourts.gov.in','Referer': 'https://indore.dcourts.gov.in/case-status-search-by-petitioner-respondent/','User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)', 'X-Requested-With': 'XMLHttpRequest'}
    data = {'cino': cino, 'action': 'get_cnr_details', 'es_ajax_request': '1'}

    try:
        response = requests.post(url, headers=headers, data=data, timeout=30)
        soups = bs(response.json()['data'], 'html.parser')
    except Exception as e:
        return jsonify({"status": "error", "message": f"No Record Found. {e}"}), 500

    sol = dict()
    try:
        sol['court_name'] = soups.find('div', {'class': 'text-center'}).text

        casetypes = soups.find('div', {'class': 'distTableContent'}).find('table').find('caption').find_next('tbody')
        casetypes = [k.text for k in casetypes.find_all('td') if k]
        sol['type_name'] = str(casetypes[0]).split('.')[0].split('-')[0].strip()
        fil = casetypes[1].split('/')
        sol['fil_no'] = fil[0]
        sol['fil_year'] = fil[1]
        sol['date_of_filing'] = convert_date(casetypes[2])
        reg = casetypes[3].split('/')
        sol['reg_no'] = reg[0]
        sol['reg_year'] = reg[1]
        sol['dt_regis'] = convert_date(casetypes[4])
        sol['cino'] = casetypes[5]

        estnum = list(casetypes[5])
        sol['est_code'] = ''.join(estnum[0:6])

        status = [k for k in soups.find_all('caption') if 'Case Status' in str(k)]
        titles = [th for k in status if k for th in k.find_next('thead').find_all('th')]
        content = [td for k in status for td in k.find_next('tbody').find_all('td')]
        datas = ''
        for x, y in zip(titles, content):
            datas = str(datas) + str(x) + str(y)
        datas = bs(datas, 'html.parser')

        date_first_list = [k.find_next('td') for k in datas.find_all('th') if 'First Hearing Date' in str(k)][0]
        sol['date_first_list'] = convert_date(date_first_list.text)

        date_next_list = [k.find_next('td') for k in datas.find_all('th') if 'Decision Date' in str(k) or 'Next Hearing Date' in str(k)][0]
        sol['date_next_list'] = convert_date(date_next_list.text)

        case_status = [k.find_next('td') for k in datas.find_all('th') if 'Case Status' in str(k)][0]
        case_status = case_status.text
        if case_status:
            sol['archive'] = 'N' if 'Pending' in case_status else 'Y'
        else:
            sol['archive'] = ''

        purpose_name = [k.find_next('td') for k in datas.find_all('th') if 'Stage of Case' in str(k) if k]
        if purpose_name:
            sol['purpose_name'] = purpose_name[0].text if purpose_name else ''
        else:
            sol['purpose_name'] = ''

        disp_name = [k.find_next('td') for k in datas.find_all('th') if 'Nature of Disposal' in str(k) if k]
        if disp_name:
            sol['disp_name'] = disp_name[0].text.split('-')[-1].strip()
        else:
            sol['disp_name'] = ''

        desgnames = [k.find_next('td') for k in datas.find_all('th') if 'Court Number and Judge' in str(k)][0]
        desgnames = desgnames.text.split('-') if desgnames else ''
        sol['court_no'] = desgnames[0]
        sol['courtno'] = desgnames[0]
        sol['desgname'] = '-'.join(desgnames[1:]) if desgnames else ''

        sol['petNameAdd'] = ' '.join(soups.find('div', {'class': "Petitioner"}).find('li').text.split())

        sol['pet_name'] = soups.find('div', {'class': "Petitioner"}).find('p').text.replace('1) ', '').strip()
        sol['petparty_name'] = soups.find('div', {'class': "Petitioner"}).find('p').text.replace('1) ', '').strip()

        advo_names = soups.find('div', {'class': "Petitioner"}).find('li')
        advo_na = advo_names.find('p').decompose()
        sol['pet_adv'] = advo_names.text.strip().split('-')[-1].strip()

        sol['resNameAdd'] = soups.find('div', {'class': 'respondent'}).find('li').text.strip().replace('\r\n',  ' ').strip() if soups.find('div', {'class': 'respondent'}).find('li') else ''

        sol['res_name'] = soups.find('div', {'class': 'respondent'}).find('p').text.replace('1)', '').strip()
        sol['resparty_name'] = soups.find('div', {'class': 'respondent'}).find('p').text.replace('1)', '').strip()

        res_adv = soups.find('div', {'class': 'respondent'}).find('li')
        res_p = res_adv.find('p').decompose()
        res_adv = res_adv.text.strip()
        if res_adv:
            sol['res_adv'] = res_adv.split('-')[1].strip()
        else:
            sol['res_adv'] = ''

        act = soups.find_all('table', {'class': 'data-table-1'})
        for k in act:
            if str(k).__contains__('Acts'):
                captions = k.find('caption').decompose() if k.find('caption') else ''
                sol['act'] = str(k).replace('\t', '').replace('\n', '').replace('\r', '')
                print(sol['act'])

            if str(k).__contains__('Case History'):
                captions = k.find('caption').decompose() if k.find('caption') else ''
                sol['historyOfCaseHearing'] = str(k).replace('\t', '').replace('\n', '').replace('\r', '')
                date_last_list = k.find_all('tr')[-1].find('a').text.strip()
                if date_last_list:
                    sol['date_last_list'] = convert_date(date_last_list)
                else:
                    sol['date_last_list'] = ''

                if typeof == 'business':
                    bussiness = k.find_all('tr')[-1].find('a')['data-case']
                    payloads = {'fields': bussiness, 'action': 'get_business', 'es_ajax_request': '1'}
                    headers = {'content-type': 'application/x-www-form-urlencoded; charset=UTF-8','user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'}
                    response = requests.post(url, data=payloads, headers=headers)
                    response = bs(response.json()['data'], 'html.parser')
                    response_data = response.find('tbody').find_all('td')
                    sol['business'] = str(response_data[0].get_text(strip=True)).replace('\r\n', ' ')
                    sol['business_purpose'] = str(response_data[1].text).strip()
                    sol['business_hearing_date'] = str(response_data[2].text).strip()

            if str(k).__contains__('Orders'):
                captions = k.find('caption').decompose() if k.find('caption') else ''
                sol['interimOrder'] = str(k).replace('\t', '').replace('\n', '').replace('\r', '')

                orders = k.find('tbody').find_all('tr')
                order_details = []
                for orders_data in orders:
                    orders_sol = dict()
                    orders_sol['sno'] = orders_data.find('td').text
                    orders_sol['order_date'] = orders_data.find('td').find_next('td').text
                    orders_sol['order_link'] = orders_data.find('a')['href']
                    order_details.append(orders_sol)
                sol['order_details'] = order_details


            else:
                sol['interimOrder'] = ''

            if str(k).__contains__('Process Details'):
                captions = k.find('caption').decompose() if k.find('caption') else ''
                sol['processes'] = str(k).replace('\t', '').replace('\n', '').replace('\r', '')
            else:
                sol['processes'] = ''

            if str(k).__contains__('IA Status'):
                captions = k.find('caption').decompose() if k.find('caption') else ''
                iafiling = str(k).replace('\t', '').replace('\n', '').replace('\r', '')
                if iafiling:
                    sol['iaFiling'] = iafiling
                else:
                    sol['iaFiling'] = ''

            if str(k).__contains__('Case Transfer Details within Establishment'):
                captions = k.find('caption').decompose() if k.find('caption') else ''
                transfer = str(k).replace('\t', '').replace('\n', '').replace('\r', '')
                if transfer:
                    sol['transfer'] = transfer
                else:
                    sol['transfer'] = ''

        str_error = soups.find('div', {'class': 'Petitioner'}).find_all('li')
        if str_error and len(str_error) > 1:
            sol['str_error'] = ' '.join(tag.get_text(strip=True) for tag in str_error[1:])
        else:
            sol['str_error'] = ''

        str_error1 = soups.find('div', {'class': 'respondent'}).find_all('li')
        if str_error1 and len(str_error1) > 1:
            sol['str_error1'] = ' '.join(i.get_text(strip=True) for i in str_error1[1:])
        else:
            sol['str_error1'] = ''

        fir_details = [k.find_next('tbody').find_all('td') for k in soups.find_all('caption') if 'FIR Details' in str(k) if k]
        for fir in fir_details:
            fir = [k.text for k in fir if k]
            sol['fir_details'] = str(fir[1] + ' ' + fir[0] + ' ' + fir[-1]).strip()

        subordinateCourtInfoStr = [k.find_next('tbody').find_all('td') for k in soups.find_all('caption') if 'Subordinate Court Information' in str(k) if k]
        for subord in subordinateCourtInfoStr:
            sub_datas = [k.text for k in subord if k]
            if sub_datas:
                sol['subordinateCourtInfoStr'] = str(convert_date(sub_datas[2]) + ' ' + sub_datas[0] + ' ' + sub_datas[1]).strip()
            else:
                sol['subordinateCourtInfoStr'] = ''

        sol['regcase_type'] = ''
        sol['date_of_decision'] = ''
        sol['disp_nature'] = ''
        sol['purpose_next'] = ''
        sol['lpet_name'] = ''
        sol['lpet_adv'] = ''
        sol['lres_name'] = ''
        sol['lres_adv'] = ''
        sol['res_legal_heir'] = ''
        sol['pet_legal_heir'] = ''
        sol['hide_pet_name'] = ''
        sol['hide_res_name'] = ''
        sol['pet_status'] = ''
        sol['res_status'] = ''
        sol['under_act1'] = ''
        sol['under_act2'] = ''
        sol['under_act3'] = ''
        sol['under_act4'] = ''
        sol['under_sec1'] = ''
        sol['under_sec2'] = ''
        sol['under_sec3'] = ''
        sol['under_sec4'] = ''
        sol['fir_no'] = ''
        sol['police_st_code'] = ''
        sol['fir_year'] = ''
        sol['lower_court_code'] = ''
        sol['lower_court'] = ''
        sol['lower_court_dec_dt'] = ''
        sol['case_no'] = ''
        sol['goshwara_no'] = ''
        sol['transfer_est'] = ''
        sol['main_matter_cino'] = ''
        sol['main_matter_cino'] = ''
        sol['main_case_no'] = ''
        sol['time_slot'] = ''
        sol['purpose_prev'] = ''
        sol['lpurpose_name'] = ''
        sol['ltype_name'] = ''
        # sol['fir_details'] = ''
        sol['subordinateCourtInfoStr'] = ''
        sol['finalOrder'] = ''
        sol['ldesgname'] = ''
        sol['desgcode'] = ''
        sol['judcode'] = ''
        sol['jcode'] = ''
        sol['lcourt_name'] = ''
        sol['version'] = ''
        sol['state_code'] = ''
        sol['district_code'] = ''
        sol['state_name'] = ''
        sol['lstate_name'] = ''
        sol['district_name'] = ''
        sol['ldistrict_name'] = ''
        sol['transfer_est_flag'] = ''
        sol['transfer_est_name'] = ''
        sol['transfer_est_date'] = ''
        sol['writinfo'] = ''
        sol['complex_code'] = ''
        sol['court_code'] = ''
        sol['sub_matter'] = ''
        sol['main_matter'] = ''
        sol['link_cases'] = ''
        sol['hide_partyname_est'] = ''

        filename = cm.BASE_DIR_OUTPUTS+'/ecourt/' + f'{cino}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(sol, f, ensure_ascii=False, indent=2)
            log_status(cino, 'Completed')
        return jsonify(sol)

    except Exception as e:
        log_status(cino, f'Error {e}')
        return jsonify({"status": "error", "message": f"No Record Found.{e}"}), 500
