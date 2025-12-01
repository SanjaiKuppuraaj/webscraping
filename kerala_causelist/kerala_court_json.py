import json
import time
from playwright.sync_api import sync_playwright

def scrape_district_courts():
    data = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled",
                  "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"], )

        page = browser.new_page()
        page.goto("https://filing.keralacourts.in/causeList", timeout=120000)
        page.wait_for_load_state("networkidle")

        page.wait_for_selector("div.mantine-Select-root", timeout=60000)

        page.locator("input[class*='mantine-Select-input']").nth(0).click(force=True)
        time.sleep(1)
        districts = page.evaluate("""
            Array.from(document.querySelectorAll('div[role="option"]'))
                .map(e => e.innerText.trim())
                .filter(t => t.length > 0)
        """)
        print(f"Found {len(districts)} districts")

        for district in districts:
            print(f"\nDistrict: {district}")
            page.locator("input[class*='mantine-Select-input']").nth(0).click(force=True)
            page.locator(f"div[role='option']:has-text('{district}')").first.click(force=True)
            time.sleep(2)

            court_input = page.locator("input[class*='mantine-Select-input']").nth(1)
            court_input.click(force=True)
            time.sleep(1)

            courts = page.evaluate("""
                Array.from(document.querySelectorAll('div[role="option"]'))
                    .map(e => ({
                        name: e.innerText.trim(),
                        value: e.getAttribute("value") || e.getAttribute("id") || e.getAttribute("data-value")
                    }))
                    .filter(c => c.name.length > 0)
            """)

            courts = [c for c in courts if c["name"] not in {d.upper() for d in districts}]

            data[district] = courts
            print(f"  → Found {len(courts)} courts")

            page.keyboard.press("Escape")
            time.sleep(1)

        browser.close()

    with open("kerala_courts.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print("\nSaved → kerala_courts.json")

    return data

if __name__ == "__main__":
    scrape_district_courts()
