import webbrowser
import time
from PIL import ImageGrab
import pytesseract
import re
import csv
import pyautogui

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def run_bulletproof_scanner():
    with open("product_urls.txt", "r") as file:
        urls = [line.strip() for line in file.readlines() if line.strip()]

    urls_to_check = urls[:5]
    print(f"[*] Loaded {len(urls)} links. Starting Bulletproof OCR Loop...")

    with open('profitable_leads.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Product URL', 'Detected Price'])

        for url in urls_to_check:
            print(f"\n[>] Opening link: {url[:60]}...")
            
            # Opens the link in your default, trusted Windows browser
            webbrowser.open(url)
            
            # Waits 8 seconds for the page and images to fully render
            time.sleep(8) 
            
            # Captures your primary monitor's pixels
            screen = ImageGrab.grab()
            text = pytesseract.image_to_string(screen)
            
            # Extracts prices and ignores $0.00 promos
            all_prices = re.findall(r'\$\s*(\d+\.\d{2})', text)
            valid_prices = [float(p) for p in all_prices if float(p) > 0.00]
            
            if valid_prices:
                price = valid_prices[0]
                print(f"    [+] Price Found: ${price}")
                writer.writerow([url, f"${price}"])
            else:
                print("    [-] Price not found on screen.")
                
            # Automatically presses Ctrl+W to close the browser tab
            pyautogui.hotkey('ctrl', 'w')
            time.sleep(1)

    print("\n[+] Scan complete. Check profitable_leads.csv!")

if __name__ == "__main__":
    run_bulletproof_scanner()
