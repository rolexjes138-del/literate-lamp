import os
import re
import time
import requests
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# UPDATED URL
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx1338AoeVB_xo8ZnuBeDbdOj1KPzxsIumRlORwQHK8tsk4FjDHQWTiYZVWeiFbFoHg/exec"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSrWe6jf6Uq0SKQjEawkO5NLLs03mZdjAAbpXtZVX6nSkXDtqlwmEIPD3uO_XN72pFWIVgTYMOHioI4/pub?output=csv"

def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(options=options)

def fetch_keywords():
    try:
        response = requests.get(CSV_URL, timeout=15)
        lines = response.text.splitlines()
        return [line.split(',')[0].strip().replace('"', '') for line in lines[1:] if line.strip()]
    except Exception as e:
        print(f">>> CSV Error: {e}")
        return []

def get_employee_size(driver, domain):
    try:
        # Check LinkedIn snippet for headcount
        search_url = f"https://www.google.com/search?q=site:linkedin.com/company/ {domain} \"employees\""
        driver.get(search_url)
        time.sleep(1.5)
        body = driver.find_element(By.TAG_NAME, "body").text
        match = re.search(r"(\d+[,|-]?\d*\+?\s?employees)", body)
        return match.group(1) if match else "1-50 (Est.)"
    except:
        return "N/A"

def sync_to_sheet(data):
    try:
        # allow_redirects=True is vital for Google Apps Script
        response = requests.get(SCRIPT_URL, params=data, allow_redirects=True, timeout=20)
        if "SUCCESS" in response.text.upper():
            print(f"      [OK] Sheet Updated: {data['domain']}")
        else:
            print(f"      [?] Sent, but Script Response: {response.text[:30]}")
    except Exception as e:
        print(f"      [!] Sync failed: {e}")

def run_bot():
    keywords = fetch_keywords()
    if not keywords:
        print("No keywords found.")
        return

    driver = init_driver()
    print(f">>> Loaded {len(keywords)} keywords. Starting search...")

    for kw in keywords:
        print(f"\n[!] TARGETING: {kw}")
        query = f'"{kw}" -IBM -Salesforce -site:wikipedia.org'
        driver.get(f"https://www.google.com/search?q={urllib.parse.quote(query)}&num=15")
        time.sleep(2)

        links = driver.find_elements(By.CSS_SELECTOR, "div.yuRUbf a")
        urls = [l.get_attribute("href") for l in links if l.get_attribute("href") and "google.com" not in l.get_attribute("href")]

        for url in urls:
            try:
                driver.get(url)
                time.sleep(3)
                domain = url.split('/')[2].replace('www.', '')
                
                # RELEVANCE CHECK
                body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                if kw.lower() not in body_text and "software" not in body_text:
                    print(f"      [Skip] {domain} - Low Relevance")
                    continue

                # SCRAPE COPYRIGHT
                copy_info = "N/A"
                if "©" in body_text:
                    idx = body_text.find("©")
                    copy_info = body_text[idx:idx+35].replace('\n', ' ')

                # GET SIZE
                size = get_employee_size(driver, domain)

                sync_to_sheet({
                    "keyword": kw,
                    "domain": domain,
                    "copyright": copy_info,
                    "size": size,
                    "activity": driver.title[:50]
                })

            except:
                continue

    driver.quit()
    print("\nDONE.")

if __name__ == "__main__":
    run_bot()