ArbMaster | Market Intel V2 🚀
A professional-grade, custom Arbitrage SaaS and market intelligence engine designed to integrate stealth wholesale scraping (Alibaba, DHGate, Made-In-China) with an Amazon-based retail valuation and analytics platform.

⚡ Core Features
Universal Master CLI & Smart Router: Instantly routes single URLs or bulk text files (product_urls.txt) to the appropriate stealth scraper or retail cross-reference engine.

Stealth Wholesale Scrapers: Bypasses bot detection and Cloudflare blocks (403 Forbidden) using a detached Chrome debugging bridge via Playwright and curl_cffi impersonation to extract buy costs, MOQs, and lead times.

Retail Intelligence & FBA Fee Engine: Automatically extracts UPCs, weights, and categories via a hybrid OCR/HTML parser. Dynamically calculates Amazon FBA fees (tiered pick & pack fulfillment + category-specific referral rates), net profit, ROI, margins, and break-even thresholds.

Free True Sales Velocity Math: Converts Best Sellers Rank (BSR) into estimated monthly unit volume using a logarithmic power-law curve. Divides market volume by active competitors to calculate your True Personal Sales Share.

Advanced Macro Risk Analyzer: Incorporates historical metrics to flag high price volatility (Bollinger band standard deviation), IP complaint risks (sudden seller drop-offs), and Amazon Buy Box dominance.

Real-Time Sync Web UI: A dark-mode, "Pro Max" aesthetic dashboard built with Flask, custom Tailwind styling, and ApexCharts. Features a 3-second live-polling background sync, dynamic filtering for winning leads, and financial revenue graphs.

Universal 23-Column Database: Centralizes all scan outputs into a standardized CSV schema (Database/Deep_Data_Database.csv) equipped with automated column padding for mixed wholesale and retail data feeds.

🛠️ Tech Stack
Backend: Python, Flask, Pandas

Scraping & Automation: Playwright, curl_cffi, BeautifulSoup, PyAutoGUI, Pytesseract OCR

Frontend: HTML5, custom Tailwind/CSS styling, ApexCharts JavaScript library

Data Storage: Structured CSV Database & JSON local caching for API optimization

📁 Project Structure
Plaintext
Arbitrage_Scanner/
│
├── Database/
│   ├── Deep_Data_Database.csv    # Central 23-column source of truth
│   └── api_cache.json            # Local API response cache
│
├── bot_profile_hijack/           # Persistent Chrome session profile for stealth bypass
│
├── lightweight_scraper.py        # Master CLI and scraping core engine
├── web_ui.py                     # Flask server and live-polling dashboard
├── product_urls.txt              # Queue for bulk scanning workflows
└── venv/                         # Python Virtual Environment
🚀 Quick Start & Installation
Clone or Open the Project Directory:
Ensure you are in the project folder with your active virtual environment (venv) enabled.

Run the Master CLI:
Launch the interactive control menu:

PowerShell
python lightweight_scraper.py
Launch the Web Dashboard:

Select Option 4 from the CLI menu, or run the web server directly:

PowerShell
python web_ui.py
Open your browser and navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000) to view real-time sync analytics, metrics cards, and financial charts.
