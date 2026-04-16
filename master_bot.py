import os
import re
import time
import requests
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# UPDATED URLs
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxjB-5XWot5sDHqnVEHhzkoB1Q4aAoiI77TvZi7UxM8vR5Qigdq5iY5xo3SR4UYBM0O/exec"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSrWe6jf6Uq0SKQjEawkO5NLLs03mZdjAAbpXtZVX6nSkXDtqlwmEIPD3uO_XN72pFWIVgTYMOHioI4/pub?output=csv"

def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)
    return driver

def fetch_keywords():
    print(">>> Connecting to Google Sheet CSV...")
    try:
        response = requests.get(CSV_URL, timeout=15)
        lines = response.text.splitlines()
        # Clean lines and extract first column, skip header
        keywords = [line.split(',')[0].strip().replace('"', '') for line in lines[1:] if line.strip()]
        print(f">>> Found {len(keywords)} keywords.")
        return keywords
    except Exception as e:
        print(f">>> ERROR: Could not read CSV: {e}")
        return []

def get_employee_size(driver, domain):
    try:
        search_url = f"https://www.google.com/search?q=site:linkedin.com/company/ {domain} \"employees\""
        driver.get(search_url)
        time.sleep(2)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        match = re.search(r"(\d+[,|-]?\d*\+?\s?employees)", body_text)
        return match.group(1) if match else "1-50 (Est.)"
    except:
        return "1-50 (Est.)"

def sync_to_sheet(data):
    try:
        # We use a session to handle cookies and redirects automatically
        session = requests.Session()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        # Google Apps Script requires following redirects (302) to reach the execution engine
        response = session.get(SCRIPT_URL, params=data, headers=headers, allow_redirects=True, timeout=25)
        
        if response.status_code == 200:
            print(f"      >>> [SUCCESS] Sheet Updated for {data['domain']}")
        else:
            print(f"      >>> [FAILED] HTTP Error {response.status_code}")
    except Exception as e:
        print(f"      >>> [SYNC ERROR]: {e}")

def run_bot():
    keywords = fetch_keywords()
    if not keywords: return

    driver = init_driver()

    for kw in keywords:
        print(f"\n[!] SEARCHING: {kw}")
        # Search strategy: Exclude major platforms to find niche competitors
        query = f'"{kw}" -IBM -Salesforce -Oracle -Microsoft -site:wikipedia.org -site:youtube.com'
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
                
                # RELEVANCE CHECK: Ensure domain is niche-related
                if kw.lower() not in title and kw.lower() not in body_text:
                    continue

                # SCRAPE COPYRIGHT (Verified existence)
                copyright_info = "N/A"
                if "©" in body_text:
                    idx = body_text.find("©")
                    copyright_info = body_text[idx:idx+40].replace('\n', ' ')

                # GET HEADCOUNT
                emp_size = get_employee_size(driver, domain)

                print(f"  Found: {domain} | Employees: {emp_size}")
                
                sync_to_sheet({
                    "keyword": kw,
                    "domain": domain,
                    "copyright": copyright_info,
                    "size": emp_size
                })

            except Exception:
                continue

    driver.quit()
    print("\n>>> All keywords processed.")

if __name__ == "__main__":
    run_bot()