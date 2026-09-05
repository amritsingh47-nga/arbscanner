import csv
import io
import re

import pytesseract
from PIL import Image
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def run_scanner():
    with open("product_urls.txt", "r") as file:
        urls = [line.strip() for line in file if line.strip()]

    urls_to_check = urls[:10]
    print(f"[*] Loaded {len(urls)} links. Scanning...")

    with open("profitable_leads.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Product URL", "Detected Price"])

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False, args=["--disable-blink-features=AutomationControlled"]
            )

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

            # The new 2.0 Stealth API applies directly to the context
            stealth = Stealth()
            stealth.apply_stealth_sync(context)

            page = context.new_page()

            for url in urls_to_check:
                print(f"[>] Scanning: {url[:60]}...")
                try:
                    page.goto(url, timeout=20000)
                    page.wait_for_timeout(4000)

                    page.mouse.wheel(0, 500)
                    page.wait_for_timeout(1000)

                    screenshot_bytes = page.screenshot(full_page=True)
                    img = Image.open(io.BytesIO(screenshot_bytes))

                    text = pytesseract.image_to_string(img)

                    all_prices = re.findall(r"\$\s*(\d+\.\d{2})", text)
                    valid_prices = [float(p) for p in all_prices if float(p) > 0.00]

                    if valid_prices:
                        actual_price = valid_prices[0]
                        print(f"    [+] Price Found: ${actual_price}")
                        writer.writerow([url, f"${actual_price}"])
                    else:
                        print("    [-] No valid price detected.")

                except Exception:
                    print("    [-] Failed to load page.")

            browser.close()

    print("\n[+] Scan complete. Results saved to profitable_leads.csv")


if __name__ == "__main__":
    run_scanner()
