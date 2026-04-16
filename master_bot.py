import os
import re
import time
import requests
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# CONFIGURATION
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzCxQgZ8li2riSOU5iNOLK60uXZHUV39Mph-9Q-wwC-hngCHdju-Un6CSsdFI40HhZl/exec"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSrWe6jf6Uq0SKQjEawkO5NLLs03mZdjAAbpXtZVX6nSkXDtqlwmEIPD3uO_XN72pFWIVgTYMOHioI4/pub?gid=1780466987&single=true&output=csv"

def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)
    return driver

def fetch_keywords():
    print(">>> Fetching keywords from Google Sheets...")
    try:
        response = requests.get(CSV_URL)
        lines = response.text.splitlines()
        # Skip header and extract first column
        return [line.split(',')[0].strip().replace('"', '') for line in lines[1:] if line.strip()]
    except Exception as e:
        print(f"Error fetching CSV: {e}")
        return []

def get_employee_size(driver, domain):
    try:
        search_url = f"https://www.google.com/search?q=site:linkedin.com/company/ {domain} \"employees\""
        driver.get(search_url)
        time.sleep(2)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        # Regex to find headcount patterns
        match = re.search(r"(\d+[,|-]?\d*\+?\s?employees)", body_text)
        return match.group(1) if match else "1-50 (Est.)"
    except:
        return "1-50 (Est.)"

def sync_to_sheet(data):
    try:
        # Python's requests library automatically follows Google's 302 redirects
        response = requests.get(SCRIPT_URL, params=data, timeout=15)
        if response.status_code == 200:
            print(f"      [SUCCESS] Sheet Updated for {data['domain']}")
        else:
            print(f"      [FAILED] HTTP {response.status_code}")
    except Exception as e:
        print(f"      [ERROR] Syncing: {e}")

def run_bot():
    keywords = fetch_keywords()
    if not keywords:
        print("No keywords found. Exiting.")
        return

    driver = init_driver()

    for kw in keywords:
        print(f"\n[!] TARGETING: {kw}")
        # Niche Search: Hide giants
        query = f'"{kw}" -IBM -Salesforce -Oracle -Microsoft -site:wikipedia.org'
        driver.get(f"https://www.google.com/search?q={urllib.parse.quote(query)}&num=20")
        time.sleep(3)

        links = driver.find_elements(By.CSS_SELECTOR, "div.yuRUbf a")
        urls = [link.get_attribute("href") for link in links if link.get_attribute("href") and "google.com" not in link.get_attribute("href")]

        for url in urls:
            try:
                driver.get(url)
                time.sleep(4)
                
                domain = url.split('/')[2].replace('www.', '')
                title = driver.title.lower()
                body_text = driver.find_element(By.TAG_NAME, "body").text
                
                # STRICT MATCH FILTER
                if kw.lower() not in title and "platform" not in body_text.lower():
                    continue

                # SCRAPE COPYRIGHT
                copyright_info = "N/A"
                if "©" in body_text:
                    idx = body_text.find("©")
                    copyright_info = body_text[idx:idx+40].replace('\n', ' ')

                # GET EMPLOYEE SIZE
                emp_size = get_employee_size(driver, domain)

                print(f"  [FOUND] {domain} | Size: {emp_size}")
                
                sync_to_sheet({
                    "keyword": kw,
                    "domain": domain,
                    "copyright": copyright_info,
                    "size": emp_size
                })

            except Exception as e:
                print(f"  [SKIP] Error on {url}")
                continue

    driver.quit()

if __name__ == "__main__":
    run_bot()