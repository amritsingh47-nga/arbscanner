import csv
import json
import re
import subprocess
import sys
import time

import pyautogui
import pyperclip
import pytesseract
from PIL import ImageGrab

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def simulate_amazon_api(upc):
    amazon_price = 39.99
    referral_fee = amazon_price * 0.15
    fba_fee = 5.50
    return amazon_price, (amazon_price - referral_fee - fba_fee)


def extract_upc_from_html(html_code):
    json_blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html_code, re.DOTALL
    )
    for block in json_blocks:
        try:
            data = json.loads(block)
            if isinstance(data, dict):
                for key in ["gtin13", "gtin12", "gtin", "upc"]:
                    if data.get(key):
                        return str(data[key])
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        for key in ["gtin13", "gtin12", "gtin", "upc"]:
                            if item.get(key):
                                return str(item[key])
        except Exception:
            continue

    patterns = [
        r'"gtin13"\s*:\s*"?(\d{11,14})"?',
        r'"gtin"\s*:\s*"?(\d{11,14})"?',
        r'"upc"\s*:\s*"?(\d{11,14})"?',
        r'"wupc"\s*:\s*"?(\d{11,14})"?',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_code)
        if match:
            return match.group(1)

    return "UNKNOWN"


def run_profit_scanner():
    try:
        with open("product_urls.txt", "r") as file:
            urls = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print("\n[-] No URLs found. Please add links first.")
        return

    if not urls:
        print("\n[-] The URL list is empty.")
        return

    print(f"\n[*] Starting Scanner for {len(urls)} items...")

    with open("profitable_leads.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                "Product Title",
                "Product URL",
                "UPC",
                "Buy Cost",
                "Amazon Price",
                "Net Profit",
                "ROI %",
            ]
        )

        for url in urls:
            print(f"\n[>] Analyzing: {url[:50]}...")

            subprocess.Popen(f'start chrome --new-window "{url}"', shell=True)
            time.sleep(2)

            pyautogui.hotkey("win", "up")
            time.sleep(5)

            width, height = pyautogui.size()
            pyautogui.click(width // 2, height // 2)
            time.sleep(1)

            screen = ImageGrab.grab()
            text = pytesseract.image_to_string(screen)
            all_prices = re.findall(r"\$\s*(\d+\.\d{2})", text)
            valid_ocr_prices = [float(p) for p in all_prices if float(p) > 0.00]
            buy_cost = valid_ocr_prices[0] if valid_ocr_prices else 0.0

            pyautogui.hotkey("ctrl", "u")
            time.sleep(2)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.hotkey("ctrl", "c")
            time.sleep(1)
            pyautogui.hotkey("ctrl", "w")
            time.sleep(1)

            html_code = pyperclip.paste()

            title_match = re.search(r"<title>(.*?)</title>", html_code, re.IGNORECASE)
            title = (
                title_match.group(1).replace(" - Walmart.com", "").strip()
                if title_match
                else "Unknown Item"
            )

            if buy_cost == 0.0:
                price_patterns = [
                    r'"price"\s*:\s*"?(\d+\.\d{2})"?',
                    r'"currentPrice"\s*:\s*"?(\d+\.\d{2})"?',
                    r'"priceAmount"\s*:\s*"?(\d+\.\d{2})"?',
                ]
                for p_pat in price_patterns:
                    p_match = re.search(p_pat, html_code)
                    if p_match and float(p_match.group(1)) > 0:
                        buy_cost = float(p_match.group(1))
                        break

            upc = extract_upc_from_html(html_code)

            print(f"    [+] Item: {title[:40]}...")
            print(f"    [+] Buy Cost: ${buy_cost} | UPC: {upc}")

            if upc != "UNKNOWN" and buy_cost > 0:
                amz_price, payout = simulate_amazon_api(upc)
                net_profit = payout - buy_cost
                roi = (net_profit / buy_cost) * 100

                print(
                    f"    [+] Amazon Price: ${amz_price} | Net Profit: ${net_profit:.2f} (ROI: {roi:.0f}%)"
                )
                writer.writerow(
                    [
                        title,
                        url,
                        upc,
                        f"${buy_cost}",
                        f"${amz_price}",
                        f"${net_profit:.2f}",
                        f"{roi:.0f}%",
                    ]
                )
            else:
                print(
                    "    [-] Missing UPC. Saved Title to CSV for manual Amazon search."
                )
                writer.writerow([title, url, upc, f"${buy_cost}", "N/A", "N/A", "N/A"])

            pyautogui.hotkey("ctrl", "w")
            time.sleep(1)

    print("\n[+] Scan complete. Check profitable_leads.csv!")


if __name__ == "__main__":
    while True:
        print("\n" + "=" * 45)
        print("    ARBITRAGE SCANNER - MAIN MENU")
        print("=" * 45)
        print("1. Paste a single URL to scan instantly")
        print("2. Paste multiple URLs (creates a new list)")
        print("3. Run bulk scan on existing saved links")
        print("4. Exit")

        choice = input("\nEnter your choice (1-4): ").strip()

        if choice == "1":
            new_url = input("\nRight-click to paste your URL here: ").strip()
            with open("product_urls.txt", "w") as f:
                f.write(new_url + "\n")
            run_profit_scanner()

        elif choice == "2":
            print("\nRight-click to paste your URLs below.")
            print("Press ENTER on an empty line when finished:")
            new_urls = []
            while True:
                line = input()
                if not line.strip():
                    break
                new_urls.append(line.strip())

            if new_urls:
                with open("product_urls.txt", "w") as f:
                    f.writelines(u + "\n" for u in new_urls)
                print(f"[*] Saved {len(new_urls)} links!")
                run_profit_scanner()

        elif choice == "3":
            run_profit_scanner()

        elif choice == "4":
            print("Exiting...")
            sys.exit()

        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")
