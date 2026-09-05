from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import gzip
import io

# REPLACE THIS with a real sitemap URL from a store's robots.txt
SITEMAP_URL = "https://www.target.com/p/sitemap_001.xml.gz"

def extract_urls():
    print(f"[*] Downloading sitemap: {SITEMAP_URL}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        response = page.goto(SITEMAP_URL)
        
        if response.status != 200:
            print(f"[-] Failed. Status code: {response.status}")
            browser.close()
            return
            
        content = response.body()
        browser.close()
        
    if SITEMAP_URL.endswith('.gz'):
        content = gzip.GzipFile(fileobj=io.BytesIO(content)).read()
        
    soup = BeautifulSoup(content, 'xml')
    links = [loc.text for loc in soup.find_all('loc')]
    
    with open('product_urls.txt', 'w') as f:
        for link in links:
            f.write(link + '\n')
            
    print(f"[+] Success! Saved {len(links)} links to product_urls.txt")

if __name__ == "__main__":
    extract_urls()
