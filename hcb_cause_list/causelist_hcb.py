import os
from playwright.sync_api import sync_playwright, TimeoutError
from common_code import common_module as cm

def generate_causelist(bench_value, side_value, date):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        try:
            page.goto('https://bombayhighcourt.nic.in/index.php', timeout=30000)
            page.wait_for_selector('xpath=/html/body/div[4]/div/div/div[1]/ul/li[5]', timeout=10000)
            page.click('xpath=/html/body/div[4]/div/div/div[1]/ul/li[5]')
            page.wait_for_selector('xpath=/html/body/div[4]/div/div/div[1]/ul/li[5]/ul/li[1]/a', timeout=10000)
            page.click('xpath=/html/body/div[4]/div/div/div[1]/ul/li[5]/ul/li[1]/a', timeout=10000)

            page.select_option('select[name="m_juris"]', bench_value)
            page.select_option('select[name="m_sideflg"]', side_value)
            page.select_option('select[name="m_causedt"]', date)

            page.wait_for_selector('#captchaimg', timeout=15000)
            captcha_code = page.query_selector('#captchaimg').get_attribute('src').split('=')[-1]
            page.fill('#captcha_code', captcha_code)
            with page.expect_navigation(wait_until='load', timeout=20000):
                page.click('xpath=/html/body/div[3]/div/div[2]/table/tbody/tr[3]/td/form/div[8]/input')
            with page.expect_navigation(wait_until='load', timeout=20000):
                page.click('xpath=/html/body/div[3]/div/div[2]/table/tbody/tr[4]/td/form/table/tbody/tr[1]/td[2]/input')
            try:
                with page.expect_event("dialog", timeout=5000) as dialog_info:
                    pass
                dialog_info.value.accept()
            except TimeoutError:
                pass
            page.wait_for_load_state('networkidle', timeout=30000)

            bench_names = {'B': 'Bombay', 'N': 'Nagpur', 'A': 'Aurangabad'}
            values = bench_names.get(bench_value.upper(), bench_value)
            side_str = side_value.upper()
            filename = f"{values}_{side_str}_{date}.html"
            # filename = f"{values}_{date}.html"
            folder = cm.BASE_DIR_OUTPUTS + '/hcb_causelist'
            os.makedirs(folder, exist_ok=True)
            html_path = os.path.join(folder, filename)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(page.content())
            return html_path
        finally:
            browser.close()