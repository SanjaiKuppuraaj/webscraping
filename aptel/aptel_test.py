
import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime

BASE_URL = "https://www.aptel.gov.in/en/casestatusapi"
AJAX_URL = "https://www.aptel.gov.in/en/casestatusapi?ajax_form=1&_wrapper_format=drupal_ajax"


def scrape_case(case_type, case_no, case_year):
    session = requests.Session()
    main_url = 'https://www.aptel.gov.in/en/casestatusapi/tab2'
    resp = session.get(main_url)
    soup = bs(resp.text, 'html.parser')
    form_build_id = soup.find('input', {'name': 'form_build_id'})['value']

    case_type_option = {'APL': '1', 'OP': '4', 'EP': '5', 'RP': '6', 'CP': '7'}
    # print(case_type_option[case_type])
    if case_type not in case_type_option:
        raise Exception("Invalid case_type")

    payload = {
        'form_build_id': form_build_id,
        'form_id': 'case_order_casenowise_form',
        'case_type': case_type_option[case_type],
        'case_no': case_no,
        'diary_year': case_year,
        '_triggering_element_name': 'op',
        '_triggering_element_value': 'Submit',
        '_drupal_ajax': '1',
        'ajax_page_state[theme]': 'delhi_gov',
        'ajax_page_state[theme_token]': '',
        'ajax_page_state[libraries]': ''
    }
    ajax_link = 'https://www.aptel.gov.in/en/casestatusapi/tab2?ajax_form=1&_wrapper_format=drupal_ajax'
    response = session.post(ajax_link, data=payload)
    html_data = response.json()[2]['data']
    soup = bs(html_data, 'html.parser')
    table = soup.find("table", {'class': "table table-bordered table-striped"})
    if not table:
        print("No record found for this case.")
        return

    ci_no = table.find('a')['href'].split('/')[-1]
    print(f"CI No found: {ci_no}")
    return scrape_by_cino(ci_no)

def scrape_by_dfr(dfr_no, dfr_year):
    session = requests.Session()
    resp = session.get(BASE_URL)
    soup = bs(resp.text, 'html.parser')
    form_build_id = soup.find('input', {'name': 'form_build_id'})['value']

    payload = {
        'form_build_id': form_build_id,
        'form_id': 'Case_order_dfrnowise_form',
        'diary_no': dfr_no,
        'diary_year': dfr_year,
        '_triggering_element_name': 'op',
        '_triggering_element_value': 'Submit',
        '_drupal_ajax': '1',
        'ajax_page_state[theme]': 'delhi_gov',
        'ajax_page_state[theme_token]': '',
        'ajax_page_state[libraries]': ''
    }

    response = session.post(AJAX_URL, data=payload)
    html_data = response.json()[2]['data']
    soup = bs(html_data, 'html.parser')
    table = soup.find("table", {'class': "table table-bordered table-striped"})
    if not table:
        print("No record found for this DFR.")
        return

    ci_no = table.find('a')['href'].split('/')[-1]
    print(f"CI No found: {ci_no}")
    return scrape_by_cino(ci_no)


def scrape_by_cino(ci_no):
    """Scrape all details directly from CI number page"""
    ci_url = f"https://www.aptel.gov.in/en/caseapidetails/{ci_no}"
    response = requests.get(ci_url)
    if response.status_code != 200:
        print("Failed to fetch CI page.")
        return

    soup = bs(response.text, 'html.parser')
    data = extract_data_from_soup(soup, ci_url)
    print(data)
    return data


def extract_data_from_soup(soup, ci_url=''):
    sol = dict()
    table = soup.find('table', {'class': "table table-bordered table-striped"})
    if not table:
        return {}

    sol['cin'] = str(ci_url).split('/')[-1] if ci_url else ''

    # DFR No / Year
    dfr_no = [j for k in table.find_all('tr') if 'DFR No' in str(k) for j in k.find_all('td') if j][1].text.split('/')
    sol['dfr_no'] = dfr_no[0]
    sol['dfr_year'] = dfr_no[1]

    # Case Type / No / Year
    case_details = [j for k in table.find_all('tr') if 'Case Type/Case No' in str(k) for j in k.find_all('td') if j][1].text.split('/')
    case_type = case_details[0].split('-')
    sol['case_type'] = case_type[0] if case_type else ''
    sol['case_no'] = case_type[1] if len(case_type) > 1 else ''
    sol['case_year'] = case_details[1] if len(case_details) > 1 else ''

    # Filing Date
    raw_filing_date = [j for k in table.find_all('tr') if 'Date of Filing' in str(k) for j in k.find_all('td') if j][1].text.strip()
    sol['case_filed_date'] = datetime.strptime(raw_filing_date, "%d/%m/%Y").strftime("%Y-%m-%d")

    # Case Status
    sol['case_status'] = [j for k in table.find_all('tr') if 'Case Status' in str(k) for j in k.find_all('td') if j][-1].text.strip()

    # Next Court / Bench Nature / Listing Purpose / Date
    sol['next_court'] = [j for k in table.find_all('tr') if 'Next Court' in str(k) for j in k.find_all('td') if j][1].text.strip()
    sol['next_bench_nature'] = [j for k in table.find_all('tr') if 'Next Bench Nature' in str(k) for j in k.find_all('td') if j][1].text.strip()
    next_listing_date = [j for k in table.find_all('tr') if 'Next Listing Date' in str(k) for j in k.find_all('td') if j][1].text.strip()
    sol['next_listing_date'] = datetime.strptime(next_listing_date, "%d/%m/%Y").strftime("%Y-%m-%d")
    sol['next_listing_purpose'] = [j for k in table.find_all('tr') if 'Next Listing Purpose' in str(k) for j in k.find_all('td') if j][1].text.strip()

    # IA No
    sol['ia_no'] = [j for k in table.find_all('tr') if 'IA No' in str(k) for j in k.find_all('td') if j][1].text.strip()

    # Petitioner / Additional Petitioner / Advocates
    sol['petitioner'] = [j for k in table.find_all('tr') if 'Appellant/Petitioner Name' in str(k) for j in k.find_all('td') if j][1].text.strip()
    sol['petparty_name'] = [j for k in table.find_all('tr') if 'Additional Party(Pet.)' in str(k) for j in k.find_all('td') if j][1].text.strip()
    pet_adv = [j for k in table.find_all('tr') if 'Pet. Advocate Name' in str(k) for j in k.find_all('td') if j][1].text.strip()
    sol['pet_adv'] = [k.strip() for k in pet_adv.split(',') if k] if len(pet_adv) > 1 else []
    additional_adv = [j for k in table.find_all('tr') if 'Additional Advocate(Pet.)' in str(k) for j in k.find_all('td') if j][1]
    sol['petNameAdd'] = [k.strip() for k in str(additional_adv).replace('<td colspan="3">','').replace('</td>','').split('<br/>') if k.strip()]

    # Respondent / Additional Respondent / Advocates
    sol['respondent'] = [j for k in table.find_all('tr') if 'Respondent Name' in str(k) for j in k.find_all('td') if j][1].text.strip()
    sol['resparty_name'] = [j for k in table.find_all('tr') if 'Additional Party(Res.)' in str(k) for j in k.find_all('td') if j][1].text.strip()
    sol['res_adv'] = [j for k in table.find_all('tr') if 'Respondent Advocate' in str(k) for j in k.find_all('td') if j][1].text.strip()
    additional_res_adv = [j for k in table.find_all('tr') if 'Additional Advocate(Res.):' in str(k) for j in k.find_all('td') if j][1]
    sol['resNameAdd'] = [s.strip() for s in str(additional_res_adv).replace('<td colspan="3">','').replace('</td>','').split('<br/>') if s.strip()]

    # Title
    sol['title'] = sol['petitioner'] + " Vs " + sol['respondent']

    # Next Hearing Dates
    sol['next_hearing_date'] = {}
    bench_rows = [k.find_next('tr') for k in table.find_all('tr') if 'Bench No' in str(k)]
    for idx, bench_tr in enumerate(bench_rows):
        tds = bench_tr.find_all('td')
        sol['next_hearing_date'][str(idx)] = {
            "bench_no": tds[0].text.strip() if len(tds) > 0 else '',
            "next_hearing": tds[1].text.strip() if len(tds) > 1 else '',
            "purpose": tds[2].text.strip() if len(tds) > 2 else '',
            "stage": tds[3].text.strip() if len(tds) > 3 else '',
            "order_link": tds[4].find('a')['href'].strip() if len(tds) > 4 and tds[4].find('a') else ''
        }

    return sol


scrape_case("APL", "121", "2025")
# scrape_by_dfr("36", "2025")
# scrape_by_cino("100010000362025")
