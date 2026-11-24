import time
from playwright.sync_api import sync_playwright

def handle_google_captcha(page, max_wait=180):
    """
    Detects the Google reCAPTCHA / 'I'm not a robot' page.
    Pauses execution and waits for the user to solve it manually.
    """
    start = time.time()

    while time.time() - start < max_wait:
        # Detect common Google CAPTCHA elements
        captcha_iframe = page.locator("iframe[title*='reCAPTCHA'], iframe[title='reCAPTCHA']")
        checkbox = page.locator("span#recaptcha-anchor, div.recaptcha-checkbox-border")
        challenge_text = page.locator("text=I'm not a robot, text=Verify you are human")

        if captcha_iframe.count() > 0 or checkbox.count() > 0 or challenge_text.count() > 0:
            print("Google CAPTCHA detected. Please solve the 'I'm not a robot' challenge manually...")
            time.sleep(10)
            continue

        # If challenge is gone and search box is ready, continue
        if page.locator('textarea[name="q"], input[name="q"]').count() > 0:
            return

        time.sleep(2)

    raise TimeoutError("CAPTCHA was not resolved within the timeout period.")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    try:
        # 1) Open Google
        page.goto("https://www.google.com", wait_until="domcontentloaded")
        time.sleep(10)

        # Handle consent popup if present
        consent_btn = page.locator("button:has-text('Accept all')")
        if consent_btn.count() > 0:
            consent_btn.first.click()
            time.sleep(2)

        # 2) Handle CAPTCHA / 'I'm not a robot'
        handle_google_captcha(page)

        # 3) Verify page title contains "Google"
        assert "Google" in page.title(), f"Unexpected title: {page.title()}"

        # 4) Type "Playwright Automation" into the search box
        search_box = page.locator('textarea[name="q"], input[name="q"]').first
        search_box.fill("Playwright Automation")

        # 5) Press Enter
        search_box.press("Enter")
        time.sleep(10)

        # 6) Wait for results page to load
        page.wait_for_selector("h3", timeout=20000)

        # 7) Verify page title now contains "Playwright Automation"
        assert "Playwright Automation" in page.title(), f"Unexpected search title: {page.title()}"

        # 8) Verify at least one result is visible
        result_titles = page.locator("h3").all_inner_texts()
        assert len(result_titles) > 0, "No search results found."

        # 9) Display first 10 results
        first_10 = result_titles[:10]
        print("First 10 search result titles:")
        for i, title in enumerate(first_10, 1):
            print(f"{i}. {title}")

        # 10) Click the 2nd result
        result_links = page.locator("h3 a")
        assert result_links.count() >= 2, "Less than 2 search results available."

        result_links.nth(1).click()
        time.sleep(10)
        page.wait_for_load_state("domcontentloaded")

        print("Opened second result page.")
        print("Current page title:", page.title())

    finally:
        # 11) Close browser
        browser.close()