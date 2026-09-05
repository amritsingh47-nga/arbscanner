import csv
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

import pyautogui
import pyperclip
import pytesseract
import requests
from bs4 import BeautifulSoup
from PIL import ImageGrab

# ==========================================
RAPID_API_KEY = "306f464a25msh1c2d55c969f874bp1c3029jsn8c5151e838a4"
# ==========================================

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "Database", "Deep_Data_Database.csv"
)
CACHE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "Database", "api_cache.json"
)


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


def evaluate_lead(roi, margin, stars, sales_vol, weight_str):
    try:
        if roi < 30.0 or margin < 15.0:
            return "FAIL"
        if stars != "N/A" and float(stars) < 4.0:
            return "FAIL"

        weight_val = 999.0
        w_match = re.search(r"(\d+(?:\.\d+)?)", str(weight_str))
        if w_match:
            weight_val = float(w_match.group(1))
        if weight_val > 3.0 and weight_str != "N/A":
            return "FAIL"

        sales_num = 0
        sv_str = str(sales_vol).upper()
        if "K" in sv_str:
            k_match = re.search(r"(\d+(?:\.\d+)?)K", sv_str)
            if k_match:
                sales_num = int(float(k_match.group(1)) * 1000)
        else:
            s_match = re.search(r"(\d+)", sv_str)
            if s_match:
                sales_num = int(s_match.group(1))

        if sales_num < 50 and sales_vol != "Unknown":
            return "FAIL"
        return "WINNING_LEAD"
    except:
        return "MANUAL_CHECK"


def check_rapid_api(upc):
    if not RAPID_API_KEY:
        return 0.0, 0.0, "N/A", 0, "N/A", "Unknown"

    cache = load_cache()
    if upc in cache:
        print("    [*] Retrieved Amazon data from local cache (0 API tokens used).")
        c = cache[upc]
        return (
            c["amazon_price"],
            c["net_payout"],
            c["amz_link"],
            c["reviews"],
            c["stars"],
            c["sales_vol"],
        )

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
        if (
            "data" in data
            and "products" in data["data"]
            and len(data["data"]["products"]) > 0
        ):
            product = data["data"]["products"][0]
            price_str = product.get("product_price", "")
            amz_link = product.get(
                "product_url", f"https://www.amazon.com/dp/{product.get('asin', '')}"
            )
            reviews = product.get("product_num_ratings", 0)
            stars = product.get("product_star_rating", "N/A")
            sales_vol = product.get("sales_volume", "Unknown")

            if price_str:
                amazon_price = float(price_str.replace("$", "").replace(",", ""))
                net_payout = amazon_price - (amazon_price * 0.15) - 5.50
                cache[upc] = {
                    "amazon_price": amazon_price,
                    "net_payout": net_payout,
                    "amz_link": amz_link,
                    "reviews": reviews,
                    "stars": stars,
                    "sales_vol": sales_vol,
                }
                save_cache(cache)
                return amazon_price, net_payout, amz_link, reviews, stars, sales_vol
    except:
        pass
    return 0.0, 0.0, "N/A", 0, "N/A", "Unknown"


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


def run_profit_scanner():
    try:
        with open("product_urls.txt", "r") as file:
            urls = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        return

    if not urls:
        return
    print(f"\n[*] Starting Local High-Speed Scanner for {len(urls)} items...")

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    file_exists = os.path.isfile(DB_PATH)

    with open(DB_PATH, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(
                [
                    "Lead Status",
                    "Date Scanned",
                    "Category",
                    "Product Title",
                    "Description",
                    "Weight",
                    "UPC",
                    "Buy Cost",
                    "Amz Price",
                    "Net Profit",
                    "Margin %",
                    "ROI %",
                    "Break-Even",
                    "Monthly Sales",
                    "Reviews",
                    "Rating",
                    "Amz Link",
                    "Source Link",
                ]
            )

        for url in urls:
            print(f"\n[>] Analyzing: {url[:50]}...")
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
                amz_price, payout, amz_link, reviews, stars, sales_vol = (
                    check_rapid_api(upc)
                )
                if amz_price > 0:
                    net_profit = payout - buy_cost
                    roi = (net_profit / buy_cost) * 100
                    margin = (net_profit / amz_price) * 100
                    break_even = (buy_cost + 5.50) / 0.85
                    status = evaluate_lead(roi, margin, stars, sales_vol, weight)

                    writer.writerow(
                        [
                            status,
                            scan_time,
                            category,
                            title,
                            desc,
                            weight,
                            upc,
                            f"${buy_cost}",
                            f"${amz_price}",
                            f"${net_profit:.2f}",
                            f"{margin:.1f}%",
                            f"{roi:.0f}%",
                            f"${break_even:.2f}",
                            sales_vol,
                            reviews,
                            stars,
                            amz_link,
                            url,
                        ]
                    )
                    print(f"    [+] Saved to CSV! Status: {status}")
                else:
                    writer.writerow(
                        [
                            "NOT_FOUND",
                            scan_time,
                            category,
                            title,
                            desc,
                            weight,
                            upc,
                            f"${buy_cost}",
                            "Not Found",
                            "N/A",
                            "N/A",
                            "N/A",
                            "N/A",
                            "N/A",
                            "N/A",
                            "N/A",
                            "N/A",
                            url,
                        ]
                    )
                    print("    [-] UPC not found on Amazon. Logged to CSV.")
            else:
                writer.writerow(
                    [
                        "MISSING_UPC",
                        scan_time,
                        category,
                        title,
                        desc,
                        weight,
                        upc,
                        f"${buy_cost}",
                        "N/A",
                        "N/A",
                        "N/A",
                        "N/A",
                        "N/A",
                        "N/A",
                        "N/A",
                        "N/A",
                        "N/A",
                        url,
                    ]
                )
                print("    [-] Missing UPC. Logged to CSV.")

            pyautogui.hotkey("ctrl", "w")
            time.sleep(0.5)

    print("\n[+] Scan complete. Data saved locally in: Database/Deep_Data_Database.csv")


if __name__ == "__main__":
    while True:
        print("\n" + "=" * 50)
        print("    LOCAL ARBITRAGE SCANNER (RAPID-API)")
        print("=" * 50)
        print("1. Paste a single URL to scan instantly")
        print("2. Paste multiple URLs (creates a new list)")
        print("3. Run bulk scan on existing saved links")
        print("4. Exit")

        choice = input("\nEnter your choice (1-4): ").strip()
        if choice == "1":
            with open("product_urls.txt", "w") as f:
                f.write(input("\nRight-click to paste your URL here: ").strip() + "\n")
            run_profit_scanner()
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
                run_profit_scanner()
        elif choice == "3":
            run_profit_scanner()
        elif choice == "4":
            sys.exit()
