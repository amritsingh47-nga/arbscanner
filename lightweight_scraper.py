import csv
import json
import os
import re
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
DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "Database", "Deep_Data_Database.csv"
)
CACHE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "Database", "api_cache.json"
)

# ==========================================
# UNIVERSAL DATABASE LOGGER (20-COLUMN SMART PADDING)
# ==========================================
def log_universal_csv(row_data_list):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    file_exists = os.path.isfile(DB_PATH)
    with open(DB_PATH, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(
                [
                    "Lead Status", "Date Scanned", "Category", "Product Title", "Description",
                    "Weight", "BSR", "UPC", "Buy Cost", "Amz Price", "FBA Fee", "Net Profit",
                    "Margin %", "ROI %", "Break-Even", "Monthly Sales", "Reviews", "Rating",
                    "Amz Link", "Source Link",
                ]
            )
        writer.writerow(row_data_list)
        print("    [+] Scan complete. Data saved locally to Database/Deep_Data_Database.csv")

# ==========================================
# MARKET INTEL CALCULATORS
# ==========================================
def calculate_fba_fee(price, weight_str, category):
    try:
        # Dynamic Referral Fee (8% Electronics/Camera, 15% Standard)
        cat_lower = str(category).lower()
        ref_rate = 0.08 if any(x in cat_lower for x in ["electronic", "computer", "camera", "cell phone"]) else 0.15
        referral_fee = price * ref_rate

        # Parse Weight
        weight_val = 1.0
        match = re.search(r"(\d+(?:\.\d+)?)", str(weight_str))
        if match:
            weight_val = float(match.group(1))

        # Tiered Pick & Pack Fulfillment Fee
        if weight_val <= 0.5: fulfillment_fee = 3.15
        elif weight_val <= 1.0: fulfillment_fee = 3.78
        elif weight_val <= 2.0: fulfillment_fee = 4.75
        elif weight_val <= 3.0: fulfillment_fee = 5.69
        elif weight_val <= 20.0: fulfillment_fee = 5.69 + ((weight_val - 3.0) * 0.38)
        else: fulfillment_fee = 10.50

        return round(referral_fee + fulfillment_fee, 2)
    except Exception:
        return 5.50

def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache_data):
    with open(CACHE_PATH, "w") as f:
        json.dump(cache_data, f, indent=4)

def check_rapid_api(upc):
    if not RAPID_API_KEY:
        return 0.0, "N/A", 0, "N/A", "Unknown", "N/A"
    cache = load_cache()
    if upc in cache:
        c = cache[upc]
        return c["amazon_price"], c["amz_link"], c["reviews"], c["stars"], c["sales_vol"], c.get("bsr", "N/A")

    url = "https://real-time-amazon-data.p.rapidapi.com/search"
    querystring = {
        "query": upc,
        "page": "1",
        "country": "US",
        "sort_by": "RELEVANCE",
        "product_condition": "NEW",
    }
    headers = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": "real-time-amazon-data.p.rapidapi.com",
    }

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
                
                cache[upc] = {
                    "amazon_price": amazon_price,
                    "amz_link": amz_link,
                    "reviews": p.get("product_num_ratings", 0),
                    "stars": p.get("product_star_rating", "N/A"),
                    "sales_vol": p.get("sales_volume", "Unknown"),
                    "bsr": bsr,
                }
                save_cache(cache)
                return amazon_price, amz_link, p.get("product_num_ratings", 0), p.get("product_star_rating", "N/A"), p.get("sales_volume", "Unknown"), bsr
    except:
        pass
    return 0.0, "N/A", 0, "N/A", "Unknown", "N/A"

# ==========================================
# STEALTH WHOLESALE ENGINES
# ==========================================
def scrape_alibaba(html_code):
    soup = BeautifulSoup(html_code, "html.parser")
    raw_text = soup.get_text(separator=" ", strip=True)
    try:
        prices = re.findall(r"\$\s*\d+\.\d{2}", raw_text)
        price = prices[0].replace(" ", "") if prices else "N/A"
    except:
        price = "N/A"
    try:
        moqs = re.findall(r"(\d+)\s*(?:piece|set|pair|unit)s?", raw_text, re.IGNORECASE)
        moq = f"{moqs[0]} pieces" if moqs else "Check Page"
    except:
        moq = "Check Page"
    try:
        times = re.findall(r"(\d+(?:-\d+)?)\s*days", raw_text, re.IGNORECASE)
        lead_time = f"{times[0]} Days" if times else "Check Page"
    except:
        lead_time = "Check Page"
    return {"Buy Cost": price, "MOQ": moq, "Lead Time": lead_time}

def scrape_dhgate(html_code):
    try:
        prices = re.findall(r'property="og:price:amount"\s*content="([\d\.]+)"', html_code)
        if not prices:
            prices = re.findall(r'itemprop="price"\s*content="([\d\.]+)"', html_code)
        if not prices:
            prices = re.findall(r'"discountPrice"\s*:\s*"?([\d\.]+)"?', html_code)
        if not prices:
            prices = re.findall(r'"minPrice"\s*:\s*"?([\d\.]+)"?', html_code)
        if not prices:
            prices = re.findall(r"US\s*\$\s*([\d\.]+)", html_code)
        if not prices:
            prices = re.findall(r"\$\s*(\d+\.\d{2})", html_code)
        price = f"${prices[0]}" if prices else "N/A"
    except:
        price = "N/A"
    try:
        moqs = re.findall(r'"minOrder"\s*:\s*"?(\d+)"?', html_code)
        moq = f"{moqs[0]} pieces" if moqs else "Check Page"
    except:
        moq = "Check Page"
    return {"Buy Cost": price, "MOQ": moq, "Lead Time": "Check Page (DHGate Varies)"}

def scrape_made_in_china(html_code):
    try:
        prices = re.findall(r'"price"\s*:\s*"?([\d\.]+)"?', html_code)
        if not prices:
            prices = re.findall(r"(?:US\s*\$|\$)\s*([\d\.]+)", html_code, re.IGNORECASE)
        price = f"${prices[0]}" if prices else "N/A"
    except:
        price = "N/A"
    try:
        moqs = re.findall(r'"minOrderQuantity"\s*:\s*"?(\d+)"?', html_code)
        moq = f"{moqs[0]} pieces" if moqs else "Check Page"
    except:
        moq = "Check Page"
    return {"Buy Cost": price, "MOQ": moq, "Lead Time": "Check Page (MIC Varies)"}

def fetch_with_playwright(url):
    print("    [*] Booting Detached Chrome (Bypassing CDP Detection)...")
    profile_path = os.path.join(os.getcwd(), "bot_profile_hijack")

    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

    subprocess.Popen(
        [
            chrome_path,
            "--remote-debugging-port=9222",
            f"--user-data-dir={profile_path}",
            "--start-maximized",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()

            try:
                page.goto(url, wait_until="commit", timeout=60000)
            except:
                pass

            input("    [?] BROWSER OPEN: Handle security check if needed. Press ENTER once price is visible...")

            try:
                html = page.content()
            except Exception:
                print("    [!] Browser was closed before data could be extracted.")
                return ""

            browser.close()
            return html

        except Exception as e:
            print(f"    [!] Detached Browser Connection Failed: {e}")
            return ""

def fetch_with_curl(url):
    try:
        headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.google.com/",
        }
        response = requests.get(
            url, impersonate="chrome120", headers=headers, timeout=15
        )
        if response.status_code == 403:
            print("    [!] Cloudflare 403 Forbidden detected!")
            return "403_BLOCKED"
        return response.text
    except Exception as e:
        print(f"    [!] Network Error: {e}")
        return ""

def run_wholesale_scraper(url):
    print("    [*] Routing to Stealth Wholesale Engine...")

    if "alibaba.com" in url:
        result = {
            **scrape_alibaba(fetch_with_playwright(url)),
            "Supplier Type": "ALIBABA",
        }
    elif "dhgate.com" in url or "made-in-china.com" in url:
        html_code = fetch_with_curl(url)
        supplier = "DHGATE" if "dhgate.com" in url else "MADE_IN_CHINA"

        if html_code == "403_BLOCKED" or html_code == "":
            print("    [*] Triggering Browser Fallback...")
            html_raw = fetch_with_playwright(url)
            result = (
                {**scrape_dhgate(html_raw), "Supplier Type": supplier}
                if supplier == "DHGATE"
                else {**scrape_made_in_china(html_raw), "Supplier Type": supplier}
            )
        else:
            data = (
                scrape_dhgate(html_code)
                if supplier == "DHGATE"
                else scrape_made_in_china(html_code)
            )
            if data["Buy Cost"] == "N/A":
                print("    [*] Direct HTML parsed N/A. Triggering Browser Fallback...")
                html_raw = fetch_with_playwright(url)
                data = (
                    scrape_dhgate(html_raw)
                    if supplier == "DHGATE"
                    else scrape_made_in_china(html_raw)
                )
            result = {**data, "Supplier Type": supplier}
    else:
        result = {
            "Buy Cost": "N/A",
            "MOQ": "N/A",
            "Lead Time": "N/A",
            "Supplier Type": "UNKNOWN",
        }

    print(f"    [+] Buy Cost: {result['Buy Cost']} | MOQ: {result['MOQ']}")
    print(f"    [+] Lead Time: {result['Lead Time']} | Supplier: {result['Supplier Type']}")
    scan_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Wholesale Smart Padding (20-Columns)
    log_universal_csv([
        "WHOLESALE_LEAD", scan_time, result["Supplier Type"], "Wholesale Item", "N/A",
        "N/A", "N/A", "N/A", result["Buy Cost"], "N/A", "N/A", "N/A",
        "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", url,
    ])

    if result["Buy Cost"] != "N/A":
        try:
            buy = float(result["Buy Cost"].replace("$", "").replace(",", "").strip())
            sell = float(input("\n    [?] Target Retail Price (eBay/Amazon) $: "))
            ship = float(input("    [?] Estimated Shipping to Customer $: "))
            profit = sell - (buy + ship + ((sell * 0.1325) + 0.30))
            print(f"    [+] NET PROFIT: ${profit:.2f}")
        except:
            pass

# ==========================================
# RETAIL ENGINES (AMAZON / WALMART)
# ==========================================
def extract_upc_universally(html_code):
    soup = BeautifulSoup(html_code, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    for key in ["gtin13", "gtin12", "gtin", "gtin14", "upc", "isbn"]:
                        if item.get(key):
                            val = str(item[key]).strip()
                            if val.isdigit() and len(val) >= 10:
                                return val
        except:
            continue
    for p in [
        r'["\'](?:upc|gtin|gtin13|gtin12|barcode|ean|primary_barcode)["\']\s*[:=]\s*["\']?(\d{11,14})["\']?',
        r"upc=(\d{11,14})",
    ]:
        match = re.search(p, html_code, re.IGNORECASE)
        if match:
            return match.group(1)
    return "UNKNOWN"

def extract_deep_data(html_code):
    soup = BeautifulSoup(html_code, "html.parser")
    desc = "N/A"
    desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", property="og:description"
    )
    if desc_tag and desc_tag.get("content"):
        desc = desc_tag["content"].strip().replace("\n", " ")
        if len(desc) > 100:
            desc = desc[:97] + "..."
    category, weight = "N/A", "N/A"
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    if (
                        item.get("@type") == "BreadcrumbList"
                        and "itemListElement" in item
                    ):
                        cats = [
                            el.get("name", "")
                            for el in item["itemListElement"]
                            if isinstance(el, dict) and el.get("name")
                        ]
                        if cats:
                            category = " > ".join(cats)
                    if (
                        item.get("@type") == "Product"
                        and item.get("category")
                        and category == "N/A"
                    ):
                        category = str(item["category"])
                    if item.get("@type") == "Product" and "weight" in item:
                        w = item["weight"]
                        if isinstance(w, dict) and "value" in w:
                            weight = f"{w['value']} {w.get('unitText', 'lbs')}"
                        elif isinstance(w, str):
                            weight = w
        except:
            continue
    return desc, category, weight

def scrape_amazon(url):
    print("    [*] Routing to Stealth Amazon Engine...")
    try:
        headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        response = requests.get(
            url, impersonate="chrome120", headers=headers, timeout=15
        )
        soup = BeautifulSoup(response.text, "html.parser")
        title = (
            soup.find(id="productTitle").get_text(strip=True)
            if soup.find(id="productTitle")
            else "N/A"
        )
        price_whole = soup.find("span", {"class": "a-price-whole"})
        price_fraction = soup.find("span", {"class": "a-price-fraction"})
        price = (
            f"${price_whole.get_text(strip=True)}{price_fraction.get_text(strip=True)}"
            if price_whole and price_fraction
            else "N/A"
        )
        img_elem = soup.find(id="landingImage")
        img_url = img_elem["src"] if img_elem and "src" in img_elem.attrs else "N/A"

        print(f"    [+] Item: {title[:50]}...")
        print(f"    [+] Retail Price: {price}")

        if title != "N/A":
            clean_title = " ".join(title.split()[:5])
            encoded = urllib.parse.quote(clean_title)
            print("\n    --- Cross-Reference Links ---")
            print(f"    -> Alibaba: https://www.alibaba.com/trade/search?SearchText={encoded}")
            print(f"    -> DHGate:  https://www.dhgate.com/w/{encoded}.html")
            print(f"    -> Image:   {img_url}")

        scan_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        # Amazon Retail Smart Padding (20-Columns)
        log_universal_csv([
            "AMAZON_RETAIL", scan_time, "Amazon", title[:97], "N/A", "N/A", "N/A", "N/A",
            "N/A", price, "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", url, "N/A",
        ])
    except Exception as e:
        print(f"[!] Amazon Scrape Failed: {e}")

def legacy_retail_scanner(url):
    print("    [*] Routing to Legacy Retail Scanner (Rapid-API)...")
    subprocess.Popen(f'start chrome --new-window "{url}"', shell=True)
    time.sleep(1.5)
    pyautogui.hotkey("win", "up")
    time.sleep(3.5)

    width, height = pyautogui.size()
    pyautogui.click(width // 2, height // 2)
    time.sleep(0.5)

    screen = ImageGrab.grab()
    text = pytesseract.image_to_string(screen)
    all_prices = re.findall(r"\$\s*(\d+\.\d{2})", text)
    buy_cost = float(all_prices[0]) if all_prices else 0.0

    pyperclip.copy("")
    pyautogui.hotkey("ctrl", "u")
    time.sleep(2)

    html_code = ""
    for attempt in range(3):
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.5)
        html_code = pyperclip.paste()
        if (
            "<html" in html_code.lower()
            or "<body" in html_code.lower()
            or "{" in html_code
        ):
            break
        time.sleep(1)

    pyautogui.hotkey("ctrl", "w")
    time.sleep(0.5)

    soup = BeautifulSoup(html_code, "html.parser")
    title = (
        soup.title.string.strip()
        if soup.title and soup.title.string
        else (
            soup.find("meta", property="og:title")["content"].strip()
            if soup.find("meta", property="og:title")
            else "Unknown Item"
        )
    )

    if buy_cost == 0.0:
        for p_pat in [
            r'["\'](?:price|currentPrice|salePrice|priceAmount)["\']\s*[:=]\s*["\']?(\d+\.\d{2})["\']?'
        ]:
            p_match = re.search(p_pat, html_code)
            if p_match and float(p_match.group(1)) > 0:
                buy_cost = float(p_match.group(1))
                break

    upc = extract_upc_universally(html_code)
    desc, category, weight = extract_deep_data(html_code)
    scan_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"    [+] Category: {category} | Weight: {weight}")
    print(f"    [+] Item: {title[:50]}...")
    print(f"    [+] Buy Cost: ${buy_cost} | UPC: {upc}")

    if upc != "UNKNOWN" and buy_cost > 0:
        amz_price, amz_link, reviews, stars, sales_vol, bsr = check_rapid_api(upc)
        if amz_price > 0:
            fba_fee = calculate_fba_fee(amz_price, weight, category)
            net_profit = amz_price - buy_cost - fba_fee
            roi = (net_profit / buy_cost) * 100
            margin = (net_profit / amz_price) * 100
            break_even = (buy_cost + fba_fee)
            status = "WINNING_LEAD" if roi >= 30.0 and margin >= 15.0 else "FAIL"
            
            log_universal_csv([
                status, scan_time, category, title[:97], desc, weight, bsr, upc, 
                f"${buy_cost}", f"${amz_price}", f"${fba_fee:.2f}", f"${net_profit:.2f}", 
                f"{margin:.1f}%", f"{roi:.0f}%", f"${break_even:.2f}", sales_vol, 
                reviews, stars, amz_link, url
            ])
            print(f"    [+] Saved to CSV! Status: {status} | FBA Fee: ${fba_fee:.2f}")
        else:
            log_universal_csv([
                "NOT_FOUND", scan_time, category, title[:97], desc, weight, "N/A", upc, 
                f"${buy_cost}", "Not Found", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", 
                "N/A", "N/A", "N/A", url
            ])
            print("    [-] UPC not found on Amazon. Logged to CSV.")
    else:
        log_universal_csv([
            "MISSING_UPC", scan_time, category, title[:97], desc, weight, "N/A", upc, 
            f"${buy_cost}", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", 
            "N/A", "N/A", url
        ])
        print("    [-] Missing UPC. Logged to CSV.")

# ==========================================
# MASTER SMART ROUTER
# ==========================================
def route_url(url):
    if not url.startswith("http"):
        url = "https://" + url

    print(f"\n[>] Analyzing: {url[:70]}...")
    if any(
        domain in url for domain in ["alibaba.com", "dhgate.com", "made-in-china.com"]
    ):
        run_wholesale_scraper(url)
    elif "amazon.com" in url:
        scrape_amazon(url)
    else:
        legacy_retail_scanner(url)

# ==========================================
# MASTER CLI UI
# ==========================================
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

        if choice == "1":
            route_url(input("\n[>] Paste URL: ").strip())
        elif choice == "2":
            print(
                "\nRight-click to paste your URLs below. Press ENTER on an empty line when finished:"
            )
            new_urls = []
            while True:
                line = input()
                if not line.strip():
                    break
                new_urls.append(line.strip())
            if new_urls:
                with open("product_urls.txt", "w") as f:
                    f.writelines(u + "\n" for u in new_urls)
                print(
                    f"\n[*] Saved {len(new_urls)} URLs to product_urls.txt! Use Option 3 to bulk scan."
                )
        elif choice == "3":
            try:
                with open("product_urls.txt", "r") as file:
                    urls = [line.strip() for line in file if line.strip()]
            except FileNotFoundError:
                print(
                    "\n[!] No product_urls.txt found. Use Option 2 to add URLs first."
                )
                continue
            if not urls:
                continue
            print(f"\n[*] Starting Bulk Scanner for {len(urls)} items...")
            for url in urls:
                route_url(url)
        elif choice == "4":
            print("\n[*] Booting Web UI in the background...")
            try:
                subprocess.Popen(
                    [sys.executable, "web_ui.py"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print("    [+] Dashboard is LIVE! CTRL+Click here to open: http://127.0.0.1:5000\n")
            except Exception as e:
                print(f"[!] Failed to launch Web UI: {e}")
        elif choice == "5":
            print("\n[*] Exiting terminal. Run your Git commands now!")
            sys.exit(0)
        else:
            print("\n[!] Invalid command.")

if __name__ == "__main__":
    main_menu()
