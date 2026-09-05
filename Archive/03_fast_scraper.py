import requests
from bs4 import BeautifulSoup
import re
import csv

# To bypass Target/Walmart CAPTCHAs without a browser, you need a proxy API.
# Paste a free API key from a service like ScraperAPI.com here:
API_KEY = "6f8df2cfbb81e2b7a6b8a5fbd7033a25" 

def run_fast_scanner():
    with open("product_urls.txt", "r") as file:
        urls = [line.strip() for line in file.readlines() if line.strip()]
        
    print(f"[*] Loaded {len(urls)} links. Scanning WITHOUT a browser...")
    
    with open('profitable_leads.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Product URL', 'Detected Price'])
        
        for url in urls[:5]:
            print(f"[>] Hitting: {url[:60]}...")
            
            try:
                if API_KEY:
                    # The API handles the CAPTCHA and renders the JavaScript invisibly
                    target_url = f"http://api.scraperapi.com?api_key={API_KEY}&url={url}&render=true&country_code=us&premium=true"
                else:
                    # Direct Python request
                    target_url = url
                    
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                response = requests.get(target_url, headers=headers, timeout=60)
                
                if response.status_code != 200:
                    print(f"    [-] Blocked! Status code: {response.status_code}")
                    continue
                    
                # Parse the raw text code directly (No OCR, no screenshots)
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()
                
                all_prices = re.findall(r'\$\s*(\d+\.\d{2})', text)
                valid_prices = [float(p) for p in all_prices if float(p) > 0.00]
                
                if valid_prices:
                    print(f"    [+] Price Found: ${valid_prices[0]}")
                    writer.writerow([url, f"${valid_prices[0]}"])
                else:
                    print("    [-] Code downloaded, but price is hidden by JavaScript or CAPTCHA.")
                    
            except Exception as e:
                print(f"    [-] Connection failed.")
                
    print("\n[+] Scan complete.")

if __name__ == "__main__":
    run_fast_scanner()
