import csv
import json
import os
import re
import math
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime

import pyautogui
import pyperclip
import pytesseract
from bs4 import BeautifulSoup
from curl_cffi import requests
from PIL import ImageGrab
from playwright.sync_api import sync_playwright

# ==========================================
# MASTER CONFIGURATIONS
# ==========================================
RAPID_API_KEY = "306f464a25msh1c2d55c969f874bp1c3029jsn8c5151e838a4"
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Database", "Deep_Data_Database.csv")
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Database", "api_cache.json")

def log_universal_csv(row_data_list):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    file_exists = os.path.isfile(DB_PATH)
    with open(DB_PATH, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow([
                "Lead Status", "Date Scanned", "Category", "Product Title", "Description",
                "Weight", "BSR", "UPC", "Buy Cost", "Amz Price", "FBA Fee", "Net Profit",
                "Margin %", "ROI %", "Break-Even", "Monthly Sales", "Reviews", "Rating",
                "Amz Link", "Source Link", "Volatility", "IP Risk", "AMZ Presence"
            ])
        writer.writerow(row_data_list)
        print("    [+] Scan complete. Data saved locally to Database/Deep_Data_Database.csv")

# ==========================================
# ADVANCED MARKET ANALYZER (HISTORICAL MACRO)
# ==========================================
def calculate_bollinger_volatility(price_history):
    """Calculates standard deviation to detect violent price swings."""
    if not price_history or len(price_history) < 2: return "UNKNOWN"
    mean_price = sum(price_history) / len(price_history)
    variance = sum((p - mean_price) ** 2 for p in price_history) / len(price_history)
    std_dev = math.sqrt(variance)
    
    # If the standard deviation is > 15% of the average price, the bands are too wide.
    if (std_dev / mean_price) > 0.15: return "HIGH VOLATILITY"
    return "STABLE"

def detect_ip_complaint_risk(seller_history):
    """Detects sudden seller drop-offs indicating brand enforcement."""
    if not seller_history or len(seller_history) < 2: return "SAFE"
    max_sellers = max(seller_history)
    current_sellers = seller_history[-1]
    
    # If listing had 8+ sellers and drops to 1-2 overnight, it's a toxic IP risk.
    if max_sellers >= 8 and current_sellers <= 2: return "TOXIC (IP RISK)"
    return "SAFE"

def analyze_amz_presence(amz_in_stock_days, total_days=90):
    """Checks if Amazon dominates the Buy Box."""
    if (amz_in_stock_days / total_days) > 0.90: return "AMZ DOMINANT"
    return "ROTATING"

def calculate_90_day_ema(data_points, period=90):
    """Calculates Exponential Moving Average for BSR or Price."""
    if not data_points: return 0.0
    k = 2 / (period + 1)
    ema = data_points[0]
    for price in data_points[1:]:
        ema = (price * k) + (ema * (1 - k))
    return round(ema, 2)

# ==========================================
# MARKET INTEL & FREE VELOCITY MATH
# ==========================================
def extract_bsr(html_code):
    match = re.search(r'#([0-9,]+)\s+in\s+([A-Za-z\s&]+)(?:\s+\(|<)', html_code)
    if match: return f"#{match.group(1)} in {match.group(2).strip()}"
    return "N/A"

def estimate_monthly_sales(bsr_string, category):
    try:
        if bsr_string == "N/A": return "Unknown"
        bsr_str = str(bsr_string).replace(',', '').replace('#', '')
        
        if 'best seller' in bsr_str.lower() or bsr_str == '1': bsr_val = 1
        else:
            m = re.search(r'(\d+)', bsr_str)
            if not m: return "Unknown"
            bsr_val = int(m.group(1))

        cat_lower = str(category).lower() + str(bsr_string).lower()
        if any(x in cat_lower for x in ["health", "household", "home", "kitchen", "toy"]): max_sales = 45000
        elif any(x in cat_lower for x in ["beauty", "electronic", "pet", "cell phone"]): max_sales = 30000
        elif any(x in cat_lower for x in ["office", "tool", "patio", "garden", "sports"]): max_sales = 15000
        else: max_sales = 10000

        if bsr_val <= 0: return "Unknown"
        sales = int(max_sales * math.pow(bsr_val, -0.55))
        return str(sales) if sales > 0 else "0"
    except Exception:
        return "Unknown"

def calculate_true_velocity(total_sales_str, seller_count=3):
    try:
        s_match = re.search(r'(\d+)', str(total_sales_str).replace(',', ''))
        if not s_match: return "Unknown", 0
        total_units = int(s_match.group(1))
        your_share = math.ceil(total_units / (seller_count + 1))
        return f"{your_share}/mo (Your Share)", your_share
    except Exception:
        return "Unknown", 0

def calculate_fba_fee(price, weight_str, category):
    try:
        cat_lower = str(category).lower()
        ref_rate = 0.08 if any(x in cat_lower for x in ["electronic", "computer", "camera", "cell phone"]) else 0.15
        weight_val = 1.0
        match = re.search(r"(\d+(?:\.\d+)?)", str(weight_str))
        if match: weight_val = float(match.group(1))
        
        if weight_val <= 0.5: fulfillment_fee = 3.15
        elif weight_val <= 1.0: fulfillment_fee = 3.78
        elif weight_val <= 2.0: fulfillment_fee = 4.75
        elif weight_val <= 3.0: fulfillment_fee = 5.69
        elif weight_val <= 20.0: fulfillment_fee = 5.69 + ((weight_val - 3.0) * 0.38)
        else: fulfillment_fee = 10.50
        return round((price * ref_rate) + fulfillment_fee, 2)
    except Exception: return 5.50

def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_cache(cache_data):
    with open(CACHE_PATH, "w") as f: json.dump(cache_data, f, indent=4)

def check_rapid_api(upc):
    if not RAPID_API_KEY: return 0.0, "N/A", 0, "N/A", "Unknown", "N/A", 3
    cache = load_cache()
    if upc in cache:
        c = cache[upc]
        return c["amazon_price"], c["amz_link"], c["reviews"], c["stars"], c["sales_vol"], c.get("bsr", "N/A"), c.get("sellers", 3)

    url = "https://real-time-amazon-data.p.rapidapi.com/search"
    querystring = {"query": upc, "page": "1", "country": "US", "sort_by": "RELEVANCE", "product_condition": "NEW"}
    headers = {"X-RapidAPI-Key": RAPID_API_KEY, "X-RapidAPI-Host": "real-time-amazon-data.p.rapidapi.com"}
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        data = response.json()
        if "data" in data and "products" in data["data"] and len(data["data"]["products"]) > 0:
            p = data["data"]["products"][0]
            price_str = p.get("product_price", "")
            if price_str:
                amazon_price = float(price_str.replace("$", "").replace(",", ""))
                amz_link = p.get("product_url", f"https://www.amazon.com/dp/{p.get('asin', '')}")
                bsr = "#1 Best Seller" if p.get("best_seller") else "N/A"
                sellers = p.get("num_sellers", 3)
                
                cache[upc] = {
                    "amazon_price": amazon_price, "amz_link": amz_link, "reviews": p.get("product_num_ratings", 0),
                    "stars": p.get("product_star_rating", "N/A"), "sales_vol": p.get("sales_volume", "Unknown"), 
                    "bsr": bsr, "sellers": sellers
                }
                save_cache(cache)
                return amazon_price, amz_link, p.get("product_num_ratings", 0), p.get("product_star_rating", "N/A"), p.get("sales_volume", "Unknown"), bsr, sellers
    except: pass
    return 0.0, "N/A", 0, "N/A", "Unknown", "N/A", 3

# ==========================================
# FULLY AUTOMATED DETACHED BROWSER
# ==========================================
def fetch_with_playwright(url):
    print("    [*] Booting Detached Chrome Engine...")
    profile_path = os.path.join(os.getcwd(), "bot_profile_hijack")
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path): chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

    subprocess.Popen([chrome_path, "--remote-debugging-port=9222", f"--user-data-dir={profile_path}", "--start-maximized"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            try: page.goto(url, wait_until="commit", timeout=30000)
            except: pass
            
            time.sleep(3.5)
            try: html = page.content()
            except Exception: html = ""
            
            try:
                page.close()
                browser.close()
            except Exception: pass
            return html
        except Exception: return ""

def scrape_alibaba(html_code):
    soup = BeautifulSoup(html_code, "html.parser")
    raw_text = soup.get_text(separator=" ", strip=True)
    try: prices = re.findall(r"\$\s*\d+\.\d{2}", raw_text); price = prices[0].replace(" ", "") if prices else "N/A"
    except: price = "N/A"
    try: moqs = re.findall(r"(\d+)\s*(?:piece|set|pair|unit)s?", raw_text, re.IGNORECASE); moq = f"{moqs[0]} pieces" if moqs else "Check Page"
    except: moq = "Check Page"
    try: times = re.findall(r"(\d+(?:-\d+)?)\s*days", raw_text, re.IGNORECASE); lead_time = f"{times[0]} Days" if times else "Check Page"
    except: lead_time = "Check Page"
    return {"Buy Cost": price, "MOQ": moq, "Lead Time": lead_time}

def scrape_dhgate(html_code):
    try:
        prices = re.findall(r'property="og:price:amount"\s*content="([\d\.]+)"', html_code)
        if not prices: prices = re.findall(r'itemprop="price"\s*content="([\d\.]+)"', html_code)
        if not prices: prices = re.findall(r'"discountPrice"\s*:\s*"?([\d\.]+)"?', html_code)
        if not prices: prices = re.findall(r'"minPrice"\s*:\s*"?([\d\.]+)"?', html_code)
        if not prices: prices = re.findall(r"US\s*\$\s*([\d\.]+)", html_code)
        if not prices: prices = re.findall(r"\$\s*(\d+\.\d{2})", html_code)
        price = f"${prices[0]}" if prices else "N/A"
    except: price = "N/A"
    try: moqs = re.findall(r'"minOrder"\s*:\s*"?(\d+)"?', html_code); moq = f"{moqs[0]} pieces" if moqs else "Check Page"
    except: moq = "Check Page"
    return {"Buy Cost": price, "MOQ": moq, "Lead Time": "Check Page (DHGate Varies)"}

def scrape_made_in_china(html_code):
    try:
        prices = re.findall(r'"price"\s*:\s*"?([\d\.]+)"?', html_code)
        if not prices: prices = re.findall(r"(?:US\s*\$|\$)\s*([\d\.]+)", html_code, re.IGNORECASE)
        price = f"${prices[0]}" if prices else "N/A"
    except: price = "N/A"
    try: moqs = re.findall(r'"minOrderQuantity"\s*:\s*"?(\d+)"?', html_code); moq = f"{moqs[0]} pieces" if moqs else "Check Page"
    except: moq = "Check Page"
    return {"Buy Cost": price, "MOQ": moq, "Lead Time": "Check Page (MIC Varies)"}

def fetch_with_curl(url):
    try:
        headers = {"Accept-Language": "en-US,en;q=0.9", "User-Agent": "Mozilla/5.0", "Referer": "https://www.google.com/"}
        response = requests.get(url, impersonate="chrome120", headers=headers, timeout=15)
        if response.status_code == 403: return "403_BLOCKED"
        return response.text
    except Exception: return ""

def run_wholesale_scraper(url):
    print("    [*] Routing to Stealth Wholesale Engine...")
    if "alibaba.com" in url:
        result = {**scrape_alibaba(fetch_with_playwright(url)), "Supplier Type": "ALIBABA"}
    elif "dhgate.com" in url or "made-in-china.com" in url:
        html_code = fetch_with_curl(url)
        supplier = "DHGATE" if "dhgate.com" in url else "MADE_IN_CHINA"
        if html_code == "403_BLOCKED" or html_code == "":
            html_raw = fetch_with_playwright(url)
            result = ({**scrape_dhgate(html_raw), "Supplier Type": supplier} if supplier == "DHGATE" else {**scrape_made_in_china(html_raw), "Supplier Type": supplier})
        else:
            data = scrape_dhgate(html_code) if supplier == "DHGATE" else scrape_made_in_china(html_code)
            if data["Buy Cost"] == "N/A":
                html_raw = fetch_with_playwright(url)
                data = scrape_dhgate(html_raw) if supplier == "DHGATE" else scrape_made_in_china(html_raw)
            result = {**data, "Supplier Type": supplier}
    else: result = {"Buy Cost": "N/A", "MOQ": "N/A", "Lead Time": "N/A", "Supplier Type": "UNKNOWN"}

    print(f"    [+] Buy Cost: {result['Buy Cost']} | MOQ: {result['MOQ']}")
    scan_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    log_universal_csv(["WHOLESALE_LEAD", scan_time, result["Supplier Type"], "Wholesale Item", "N/A", "N/A", "N/A", "N/A", result["Buy Cost"], "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", url, "N/A", "N/A", "N/A"])

# ==========================================
# RETAIL ENGINES (AMAZON / WALMART)
# ==========================================
def extract_upc_universally(html_code):
    for p in [r'["\'](?:upc|gtin|gtin13|gtin12|barcode|ean|primary_barcode)["\']\s*[:=]\s*["\']?(\d{11,14})["\']?', r"upc=(\d{11,14})"]:
        match = re.search(p, html_code, re.IGNORECASE)
        if match: return match.group(1)
    return "UNKNOWN"

def extract_deep_data(html_code):
    soup = BeautifulSoup(html_code, "html.parser")
    desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
    desc = desc_tag["content"].strip().replace("\n", " ")[:97] + "..." if desc_tag and desc_tag.get("content") else "N/A"
    category, weight = "N/A", "N/A"
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    if item.get("@type") == "BreadcrumbList" and "itemListElement" in item:
                        cats = [el.get("name", "") for el in item["itemListElement"] if isinstance(el, dict) and el.get("name")]
                        if cats: category = " > ".join(cats)
                    if item.get("@type") == "Product" and "weight" in item:
                        w = item["weight"]
                        weight = f"{w['value']} {w.get('unitText', 'lbs')}" if isinstance(w, dict) and "value" in w else str(w)
        except: continue
    return desc, category, weight

def scrape_amazon(url):
    print("    [*] Routing to Stealth Amazon Engine...")
    try:
        headers = {"Accept-Language": "en-US,en;q=0.9", "User-Agent": "Mozilla/5.0"}
        response = requests.get(url, impersonate="chrome120", headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.find(id="productTitle").get_text(strip=True) if soup.find(id="productTitle") else "N/A"
        price_whole = soup.find("span", {"class": "a-price-whole"})
        price_fraction = soup.find("span", {"class": "a-price-fraction"})
        price = f"${price_whole.get_text(strip=True)}{price_fraction.get_text(strip=True)}" if price_whole and price_fraction else "N/A"
        
        bsr_html = extract_bsr(response.text)
        desc, category, weight = extract_deep_data(response.text)
        total_sales = estimate_monthly_sales(bsr_html, category)
        true_sales_str, _ = calculate_true_velocity(total_sales, seller_count=3)

        print(f"    [+] Item: {title[:50]}...")
        print(f"    [+] Price: {price} | Market Vol: {total_sales}/mo | {true_sales_str}")

        scan_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        log_universal_csv(["AMAZON_RETAIL", scan_time, category, title[:97], desc, weight, bsr_html, "N/A", "N/A", price, "N/A", "N/A", "N/A", "N/A", "N/A", true_sales_str, "N/A", "N/A", url, "N/A", "N/A", "N/A", "N/A"])
    except Exception as e: print(f"[!] Amazon Scrape Failed: {e}")

def legacy_retail_scanner(url):
    print("    [*] Routing to Legacy Retail Scanner (Rapid-API)...")
    subprocess.Popen(f'start chrome --new-window "{url}"', shell=True)
    time.sleep(1.5); pyautogui.hotkey("win", "up"); time.sleep(3.5)
    width, height = pyautogui.size(); pyautogui.click(width // 2, height // 2); time.sleep(0.5)

    screen = ImageGrab.grab()
    text = pytesseract.image_to_string(screen)
    all_prices = re.findall(r"\$\s*(\d+\.\d{2})", text)
    buy_cost = float(all_prices[0]) if all_prices else 0.0

    pyperclip.copy(""); pyautogui.hotkey("ctrl", "u"); time.sleep(2)
    html_code = ""
    for _ in range(3):
        pyautogui.hotkey("ctrl", "a"); time.sleep(0.2); pyautogui.hotkey("ctrl", "c"); time.sleep(0.5)
        html_code = pyperclip.paste()
        if "<html" in html_code.lower() or "{" in html_code: break
        time.sleep(1)
    pyautogui.hotkey("ctrl", "w"); time.sleep(0.5)

    soup = BeautifulSoup(html_code, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else "Unknown Item"
    if buy_cost == 0.0:
        for p_pat in [r'["\'](?:price|currentPrice|salePrice|priceAmount)["\']\s*[:=]\s*["\']?(\d+\.\d{2})["\']?']:
            p_match = re.search(p_pat, html_code)
            if p_match and float(p_match.group(1)) > 0: buy_cost = float(p_match.group(1)); break

    upc = extract_upc_universally(html_code)
    desc, category, weight = extract_deep_data(html_code)
    scan_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"    [+] Category: {category} | Weight: {weight}")
    print(f"    [+] Item: {title[:50]}...")
    print(f"    [+] Buy Cost: ${buy_cost} | UPC: {upc}")

    if upc != "UNKNOWN" and buy_cost > 0:
        amz_price, amz_link, reviews, stars, raw_sales_vol, api_bsr, sellers = check_rapid_api(upc)
        if amz_price > 0:
            fba_fee = calculate_fba_fee(amz_price, weight, category)
            net_profit = amz_price - buy_cost - fba_fee
            roi = (net_profit / buy_cost) * 100
            margin = (net_profit / amz_price) * 100
            break_even = (buy_cost + fba_fee)
            
            final_bsr = api_bsr
            total_sales = raw_sales_vol if (raw_sales_vol != "Unknown" and raw_sales_vol != "N/A") else estimate_monthly_sales(final_bsr, category)
            true_sales_str, your_units = calculate_true_velocity(total_sales, seller_count=sellers)

            # Historical Mock Execution (Defaults until API is connected)
            volatility_status = "PENDING 90-DAY" 
            ip_risk_status = "PENDING 90-DAY"
            amz_presence = "PENDING 90-DAY"

            status = "WINNING_LEAD" if (roi >= 30.0 and margin >= 15.0 and your_units >= 10) else "FAIL"
                
            log_universal_csv([status, scan_time, category, title[:97], desc, weight, final_bsr, upc, f"${buy_cost}", f"${amz_price}", f"${fba_fee:.2f}", f"${net_profit:.2f}", f"{margin:.1f}%", f"{roi:.0f}%", f"${break_even:.2f}", true_sales_str, reviews, stars, amz_link, url, volatility_status, ip_risk_status, amz_presence])
            print(f"    [+] Saved to CSV! Status: {status} | FBA Fee: ${fba_fee:.2f} | Share: {true_sales_str}")
        else:
            log_universal_csv(["NOT_FOUND", scan_time, category, title[:97], desc, weight, "N/A", upc, f"${buy_cost}", "Not Found", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", url, "N/A", "N/A", "N/A"])
    else:
        log_universal_csv(["MISSING_UPC", scan_time, category, title[:97], desc, weight, "N/A", upc, f"${buy_cost}", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", url, "N/A", "N/A", "N/A"])

def route_url(url):
    if not url.startswith("http"): url = "https://" + url
    print(f"\n[>] Analyzing: {url[:70]}...")
    if any(domain in url for domain in ["alibaba.com", "dhgate.com", "made-in-china.com"]): run_wholesale_scraper(url)
    elif "amazon.com" in url: scrape_amazon(url)
    else: legacy_retail_scanner(url)

def main_menu():
    while True:
        print("\n" + "=" * 50)
        print("    ARBITRAGE MASTER SCANNER (MARKET INTEL V2)")
        print("=" * 50)
        print("1. Paste a single URL to scan instantly")
        print("2. Paste multiple URLs (creates a new list)")
        print("3. Run bulk scan on existing saved links")
        print("4. Launch Web Browser UI")
        print("5. Exit")
        choice = input("\nEnter your choice (1-5): ").strip()

        if choice == "1": route_url(input("\n[>] Paste URL: ").strip())
        elif choice == "2":
            print("\nRight-click to paste your URLs below. Press ENTER on an empty line when finished:")
            new_urls = []
            while True:
                line = input()
                if not line.strip(): break
                new_urls.append(line.strip())
            if new_urls:
                with open("product_urls.txt", "w") as f: f.writelines(u + "\n" for u in new_urls)
                print(f"\n[*] Saved {len(new_urls)} URLs to product_urls.txt! Use Option 3 to bulk scan.")
        elif choice == "3":
            try:
                with open("product_urls.txt", "r") as file: urls = [line.strip() for line in file if line.strip()]
            except: 
                print("\n[!] No product_urls.txt found. Use Option 2 to add URLs first.")
                continue
            if not urls: continue
            for url in urls: route_url(url)
        elif choice == "4":
            print("\n[*] Booting Web UI in the background...")
            try:
                subprocess.Popen([sys.executable, "web_ui.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("    [+] Dashboard is LIVE! CTRL+Click here to open: http://127.0.0.1:5000\n")
            except Exception as e: print(f"[!] Failed to launch Web UI: {e}")
        elif choice == "5": sys.exit(0)

if __name__ == "__main__":
    main_menu()
