import sys
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup as bs
from common_code.proxy_implement import get_playwright_proxy

def fill_form_fields(page, bench_code, partyname, case_year, pet_res, status):
    page.select_option("select#my_city", value=bench_code)
    time.sleep(3)
    page.select_option("select#plst_pet", value=pet_res)
    page.fill("input#pname", partyname)
    page.select_option("select#pyear", value=case_year)
    time.sleep(5)
    page.wait_for_function("""
        () => {
            const el = document.querySelector('#ppd');
            return el && el.options.length > 1 && !el.disabled && !el.readOnly;
        }
    """)

    page.select_option("select#ppd", value=status)
    time.sleep(1)
    page.click("input#bt2")
    time.sleep(45)

def extract_case_rows(table):
    rows = table.find_all('tr')
    case_map = {}
    current_sl = None

    for row in rows:
        cols = row.find_all('td')
        if not cols:
            continue

        first_col_text = cols[0].get_text(strip=True)
        if first_col_text.isdigit():
            current_sl = first_col_text
            case_parts = list(cols[1].stripped_strings)
            case_number_block = '<br>'.join(case_parts)
            category = cols[-2].get_text(strip=True)
            hearing_date = cols[-1].get_text(strip=True)
            party_type = cols[2].get_text(strip=True)
            party_names = ' '.join(cols[3].stripped_strings)

            case_map[current_sl] = {
                'sl': current_sl,
                'case_number': case_number_block,
                'category': category,
                'hearing_date': hearing_date,
                'party_info': [f"{party_type}: {party_names}"]
            }
        else:
            party_type = cols[0].get_text(strip=True)
            party_names = ' '.join(cols[1].stripped_strings)
            if current_sl and current_sl in case_map:
                case_map[current_sl]['party_info'].append(f"{party_type}: {party_names}")

    return [[
        data['sl'],
        data['case_number'],
        ' | '.join(data['party_info']),
        data['category'],
        data['hearing_date']
    ] for data in case_map.values()]

def generate_html_table(header, rows):
    html = '<html><head><meta charset="UTF-8"><title>MPHC Case Result</title></head><body>\n'
    html += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; font-family: Arial; width: 100%;">\n'
    html += '<thead style="background-color: #f2f2f2;"><tr>' + ''.join(f'<th>{col}</th>' for col in header) + '</tr></thead>\n'
    html += '<tbody>\n'
    for row in rows:
        html += '<tr>' + ''.join(f'<td>{col}</td>' for col in row) + '</tr>\n'
    html += '</tbody>\n</table>\n</body></html>'
    return html

def fetch_case_status(bench_code, partyname, case_year, pet_res, status):
    with sync_playwright() as p:
        proxyies = get_playwright_proxy()
        browser = p.chromium.launch(headless=True, proxy=proxyies)
        context = browser.new_context()
        page = context.new_page()

        try:
            print("Navigating to MPHC site...")
            response = page.goto("https://mphc.gov.in/case-status", timeout=60000)
            if not response or response.status >= 400:
                raise Exception(f"Page load failed with status {response.status if response else 'unknown'}")

            page.locator("xpath=//a[contains(text(),'Party Name')]").click()
            page.wait_for_selector("select#my_city", timeout=3000)

            fill_form_fields(page, bench_code, partyname, case_year, pet_res, status)

            html = bs(page.content(), 'html.parser')
            table = html.find('table', {'class': 'newcss'})
            if not table:
                raise Exception("No result table found on page.")

            header = ['SL', 'Case Number<br>District<br>Filing Date<br>Status',
                      'Party and Advocate details', 'Category', 'Next/Last Hearing Date']
            rows = extract_case_rows(table)
            return generate_html_table(header, rows)

        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            browser.close()

if __name__ == '__main__':
    if len(sys.argv) != 6:
        print("Usage: python3 hcmp_casestatus.py <bench_code> <partyname> <case_year> <pet_res> <status>", file=sys.stderr)
        sys.exit(1)

    bench_code = sys.argv[1]
    partyname = sys.argv[2]
    case_year = sys.argv[3]
    pet_res = sys.argv[4]
    status = sys.argv[5]

    html_result = fetch_case_status(bench_code, partyname, case_year, pet_res, status)
    print(html_result)
















# import sys
# sys.path.insert(0, '/var/www/mml_python_code')
# 
# import sys
# import time
# from playwright.sync_api import sync_playwright
# from bs4 import BeautifulSoup as bs
# from common_code.proxy_implement import get_playwright_proxy
# 
# def fill_form_fields(page, bench_code, partyname, case_year, pet_res, status):
#     page.select_option("select#my_city", value=bench_code)
#     time.sleep(3)
#     page.select_option("select#plst_pet", value=pet_res)
#     page.fill("input#pname", partyname)
#     page.select_option("select#pyear", value=case_year)
#     time.sleep(5)
#     page.wait_for_function("""
#         () => {
#             const el = document.querySelector('#ppd');
#             return el && el.options.length > 1 && !el.disabled && !el.readOnly;
#         }
#     """)
# 
#     page.select_option("select#ppd", value=status)
#     time.sleep(1)
#     page.click("input#bt2")
#     time.sleep(35)
# 
# def extract_case_rows(table):
#     rows = table.find_all('tr')
#     case_map = {}
#     current_sl = None
# 
#     for row in rows:
#         cols = row.find_all('td')
#         if not cols:
#             continue
# 
#         first_col_text = cols[0].get_text(strip=True)
#         if first_col_text.isdigit():
#             current_sl = first_col_text
#             case_parts = list(cols[1].stripped_strings)
#             case_number_block = '<br>'.join(case_parts)
#             category = cols[-2].get_text(strip=True)
#             hearing_date = cols[-1].get_text(strip=True)
#             party_type = cols[2].get_text(strip=True)
#             party_names = ' '.join(cols[3].stripped_strings)
# 
#             case_map[current_sl] = {
#                 'sl': current_sl,
#                 'case_number': case_number_block,
#                 'category': category,
#                 'hearing_date': hearing_date,
#                 'party_info': [f"{party_type}: {party_names}"]
#             }
#         else:
#             party_type = cols[0].get_text(strip=True)
#             party_names = ' '.join(cols[1].stripped_strings)
#             if current_sl and current_sl in case_map:
#                 case_map[current_sl]['party_info'].append(f"{party_type}: {party_names}")
# 
#     return [[
#         data['sl'],
#         data['case_number'],
#         ' | '.join(data['party_info']),
#         data['category'],
#         data['hearing_date']
#     ] for data in case_map.values()]
# 
# def generate_html_table(header, rows):
#     html = '<html><head><meta charset="UTF-8"><title>MPHC Case Result</title></head><body>\n'
#     html += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; font-family: Arial; width: 100%;">\n'
#     html += '<thead style="background-color: #f2f2f2;"><tr>' + ''.join(f'<th>{col}</th>' for col in header) + '</tr></thead>\n'
#     html += '<tbody>\n'
#     for row in rows:
#         html += '<tr>' + ''.join(f'<td>{col}</td>' for col in row) + '</tr>\n'
#     html += '</tbody>\n</table>\n</body></html>'
#     return html
# 
# def fetch_case_status(bench_code, partyname, case_year, pet_res, status):
#     with sync_playwright() as p:
#         proxyies = get_playwright_proxy()
#         browser = p.chromium.launch(headless=True, proxy=proxyies)
#         context = browser.new_context()
#         page = context.new_page()
# 
#         try:
#             print("Navigating to MPHC site...")
#             response = page.goto("https://mphc.gov.in/case-status", timeout=60000)
#             if not response or response.status >= 400:
#                 raise Exception(f"Page load failed with status {response.status if response else 'unknown'}")
# 
#             page.locator("xpath=//a[contains(text(),'Party Name')]").click()
#             page.wait_for_selector("select#my_city", timeout=3000)
# 
#             fill_form_fields(page, bench_code, partyname, case_year, pet_res, status)
# 
#             html = bs(page.content(), 'html.parser')
#             table = html.find('table', {'class': 'newcss'})
#             if not table:
#                 raise Exception("No result table found on page.")
# 
#             header = ['SL', 'Case Number<br>District<br>Filing Date<br>Status',
#                       'Party and Advocate details', 'Category', 'Next/Last Hearing Date']
#             rows = extract_case_rows(table)
#             return generate_html_table(header, rows)
# 
#         except Exception as e:
#             print(f"ERROR: {e}", file=sys.stderr)
#             sys.exit(1)
#         finally:
#             browser.close()
# 
# if __name__ == '__main__':
#     if len(sys.argv) != 6:
#         print("Usage: python3 hcmp_casestatus.py <bench_code> <partyname> <case_year> <pet_res> <status>", file=sys.stderr)
#         sys.exit(1)
# 
#     bench_code = sys.argv[1]
#     partyname = sys.argv[2]
#     case_year = sys.argv[3]
#     pet_res = sys.argv[4]
#     status = sys.argv[5]
# 
#     html_result = fetch_case_status(bench_code, partyname, case_year, pet_res, status)
#     print(html_result)
