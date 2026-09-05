from flask import Flask, render_template_string, jsonify
import pandas as pd
import urllib.parse
import os
import re
import json

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Database', 'Deep_Data_Database.csv')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arbitrage Master | Terminal</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <style>
        :root { --bg-base: #000000; --bg-panel: #0a0a0a; --bg-hover: #171717; --border-color: #262626; --text-main: #ededed; --text-muted: #a1a1aa; --accent: #3b82f6; --success: #22c55e; --danger: #ef4444; --warning: #eab308; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background-color: var(--bg-base); color: var(--text-main); display: flex; height: 100vh; overflow: hidden; }
        .app-container { display: flex; width: 100%; max-width: 1600px; margin: 0 auto; }
        .sidebar { width: 260px; background-color: var(--bg-base); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; padding: 24px 16px; flex-shrink: 0; }
        .logo { font-size: 1.1rem; font-weight: 700; letter-spacing: 1px; margin-bottom: 32px; padding-left: 12px; }
        .logo i { color: var(--accent); margin-right: 8px; }
        .nav-link { display: flex; align-items: center; padding: 10px 12px; color: var(--text-muted); text-decoration: none; border-radius: 6px; font-size: 0.9rem; font-weight: 500; margin-bottom: 4px; transition: 0.2s ease; cursor: pointer; }
        .nav-link i { width: 24px; font-size: 1.1rem; }
        .nav-link:hover, .nav-link.active { background-color: var(--bg-hover); color: var(--text-main); }
        .nav-link.active { border: 1px solid var(--border-color); }
        .main-wrapper { flex: 1; display: flex; flex-direction: column; padding: 32px; overflow-y: auto; background-color: var(--bg-base); }
        .header { margin-bottom: 24px; display: flex; align-items: center; justify-content: space-between; }
        .header h2 { font-size: 1.5rem; font-weight: 600; }
        .live-status { font-size: 0.75rem; color: var(--success); font-weight: 600; display: flex; align-items: center; gap: 6px; }
        .live-dot { width: 8px; height: 8px; background: var(--success); border-radius: 50%; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
        .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
        .metric-card { background-color: var(--bg-panel); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; }
        .metric-title { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); margin-bottom: 8px; font-weight: 600; }
        .metric-value { font-size: 2rem; font-weight: 700; }
        
        .table-wrapper { background-color: var(--bg-panel); border: 1px solid var(--border-color); border-radius: 12px; overflow-x: auto; }
        table { width: 100%; table-layout: fixed; border-collapse: collapse; text-align: left; }
        th.col-status { width: 100px; } th.col-date { width: 90px; cursor: pointer; } 
        th.col-product { width: 210px; } th.col-bsr { width: 90px; } 
        th.col-cost, th.col-fba, th.col-amz { width: 80px; } th.col-profit { width: 90px; } th.col-risk { width: 110px; } th.col-actions { width: 100px; }
        th, td { padding: 14px 12px; border-bottom: 1px solid var(--border-color); font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        th { color: var(--text-muted); font-weight: 500; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.5px; background-color: var(--bg-panel); }
        tr:hover { background-color: var(--bg-hover); }
        
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.65rem; font-weight: 600; letter-spacing: 0.5px; display: inline-block; }
        .badge.winner { background: rgba(34, 197, 94, 0.1); color: var(--success); border: 1px solid rgba(34, 197, 94, 0.2); }
        .badge.not-found { background: rgba(239, 68, 68, 0.1); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.2); }
        .badge.warning { background: rgba(234, 179, 8, 0.1); color: var(--warning); border: 1px solid rgba(234, 179, 8, 0.2); }
        .badge.default { background: var(--border-color); color: var(--text-muted); }
        
        .profit-pos { color: var(--success); font-weight: 600; }
        .profit-neg { color: var(--danger); font-weight: 600; }
        .action-links { display: flex; gap: 6px; }
        .btn { text-decoration: none; padding: 6px 10px; border-radius: 6px; font-size: 0.7rem; font-weight: 600; display: inline-flex; align-items: center; transition: 0.2s; }
        .btn i { margin-right: 4px; font-size: 0.8rem; }
        .btn-amz { background-color: rgba(255, 153, 0, 0.1); color: #ff9900; border: 1px solid rgba(255, 153, 0, 0.2); }
        .btn-amz:hover { background-color: rgba(255, 153, 0, 0.2); }
        .btn-source { background-color: var(--border-color); color: var(--text-main); }
        .btn-source:hover { background-color: #3f3f46; }
        
        .chart-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 24px; }
        .chart-container { background: var(--bg-panel); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; }
        .chart-title { color: var(--text-muted); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 16px; letter-spacing: 0.5px; }
    </style>
</head>
<body>
    <div class="app-container">
        <div class="sidebar">
            <div class="logo"><i class="fa-solid fa-bolt"></i> ARBMASTER</div>
            <a onclick="switchTab('ALL', this)" class="nav-link active"><i class="fa-solid fa-chart-line"></i> Dashboard</a>
            <a onclick="switchTab('WINNER', this)" class="nav-link"><i class="fa-solid fa-trophy"></i> Winning Leads</a>
            <div style="margin-top: 32px; margin-bottom: 8px; padding-left: 12px; font-size: 0.7rem; color: var(--text-muted); font-weight: 600; letter-spacing: 1px;">ANALYTICS</div>
            <a onclick="switchTab('finance', this)" class="nav-link"><i class="fa-solid fa-sack-dollar"></i> Finance</a>
        </div>
        
        <div class="main-wrapper">
            <div id="dashboard-view">
                <div class="header">
                    <h2 id="page-title">Market Intel Database</h2>
                    <div class="live-status"><div class="live-dot"></div> LIVE SYNC</div>
                </div>
                <div class="metrics-grid">
                    <div class="metric-card"><div class="metric-title">Total Scanned</div><div class="metric-value" id="val-total">0</div></div>
                    <div class="metric-card"><div class="metric-title">Categories</div><div class="metric-value" id="val-cats" style="color: var(--accent);">0</div></div>
                    <div class="metric-card"><div class="metric-title">Winning Leads</div><div class="metric-value" id="val-wins" style="color: var(--success);">0</div></div>
                </div>
                <div class="table-wrapper">
                    <table id="leadsTable">
                        <thead>
                            <tr>
                                <th class="col-status">Status</th><th class="col-date">Date</th>
                                <th class="col-product">Product</th><th class="col-bsr">BSR / Est.</th><th class="col-cost">Buy</th><th class="col-fba">FBA</th><th class="col-amz">Amz</th>
                                <th class="col-profit">Profit/ROI</th><th class="col-risk">Macro Risk</th><th class="col-actions">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="table-body"></tbody>
                    </table>
                </div>
            </div>

            <div id="finance-view" style="display: none;">
                <div class="header"><h2>Financial & Revenue Analytics</h2></div>
                <div class="metrics-grid">
                    <div class="metric-card"><div class="metric-title">Est. Monthly Revenue</div><div class="metric-value" id="kpi-rev" style="color: var(--success);">$0.00</div></div>
                    <div class="metric-card"><div class="metric-title">Average Profit Margin</div><div class="metric-value" id="kpi-margin" style="color: var(--accent);">0%</div></div>
                    <div class="metric-card"><div class="metric-title">Total Winning Products</div><div class="metric-value" id="kpi-wins">0</div></div>
                </div>
                <div class="chart-grid">
                    <div class="chart-container"><div class="chart-title">Top Products by Revenue</div><div id="revenue-chart"></div></div>
                    <div class="chart-container"><div class="chart-title">Categories Breakdown</div><div id="category-chart"></div></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentTab = 'ALL';
        let previousDataHash = "";

        async function pollData() {
            try {
                const res = await fetch('/api/data');
                const result = await res.json();
                if (result.hash !== previousDataHash) {
                    previousDataHash = result.hash;
                    updateUI(result);
                }
            } catch (e) { console.error("Poll Error:", e); }
        }

        function updateUI(res) {
            document.getElementById('val-total').innerText = res.total;
            document.getElementById('val-cats').innerText = res.cats;
            document.getElementById('val-wins').innerText = res.wins;

            const tbody = document.getElementById('table-body');
            tbody.innerHTML = '';

            res.data.forEach(r => {
                let badgeClass = 'default', badgeText = r['Lead Status'];
                if (r['Lead Status'] === 'WINNING_LEAD') { badgeClass = 'winner'; badgeText = 'WINNER'; }
                else if (r['Lead Status'].includes('NOT_FOUND') || r['Lead Status'].includes('MISSING')) { badgeClass = 'not-found'; badgeText = 'NO MATCH'; }

                let isNeg = (r['Net Profit'] || '').toString().includes('-') || r['Net Profit'] === 'N/A';
                
                // Macro Risk Badge Logic
                let volClass = (r['Volatility'] === 'STABLE') ? 'winner' : (r['Volatility'] === 'HIGH VOLATILITY' ? 'not-found' : 'default');
                let ipClass = (r['IP Risk'] === 'SAFE') ? 'winner' : (r['IP Risk'] === 'TOXIC (IP RISK)' ? 'not-found' : 'default');
                let amzClass = (r['AMZ Presence'] === 'ROTATING') ? 'winner' : (r['AMZ Presence'] === 'AMZ DOMINANT' ? 'not-found' : 'default');
                
                const tr = document.createElement('tr');
                tr.className = 'data-row';
                tr.innerHTML = `
                    <td><span class="badge ${badgeClass}">${badgeText}</span></td>
                    <td style="color: var(--text-muted); font-family: monospace;">${r['Date Scanned'] || ''}</td>
                    <td>
                        <div style="font-weight: 500; overflow: hidden; text-overflow: ellipsis;" title="${r['Product Title']}">${r['Product Title']}</div>
                        <div style="font-size: 0.7rem; color: var(--accent); overflow: hidden; text-overflow: ellipsis; margin-top: 2px;">${r['Category'] || 'N/A'}</div>
                    </td>
                    <td>
                        <div style="font-family: monospace; color: var(--text-muted);">${r['BSR'] || 'N/A'}</div>
                        <div style="font-size: 0.65rem; font-weight: 600; color: var(--accent); margin-top: 2px;">${r['Monthly Sales'] || 'N/A'}</div>
                    </td>
                    <td>${r['Buy Cost'] || ''}</td>
                    <td style="color: var(--danger);">${r['FBA Fee'] || 'N/A'}</td>
                    <td style="color: var(--text-muted);">${r['Amz Price'] || ''}</td>
                    <td class="${isNeg ? 'profit-neg' : 'profit-pos'}">
                        <div>${r['Net Profit'] || ''}</div>
                        <div style="font-size: 0.65rem; font-weight: normal; margin-top: 2px;">ROI: ${r['ROI %'] || 'N/A'}</div>
                    </td>
                    <td>
                        <div style="margin-bottom: 4px;"><span class="badge ${volClass}" style="font-size: 0.55rem; width: 100%;">Vol: ${r['Volatility'] || 'PENDING'}</span></div>
                        <div style="margin-bottom: 4px;"><span class="badge ${ipClass}" style="font-size: 0.55rem; width: 100%;">IP: ${r['IP Risk'] || 'PENDING'}</span></div>
                        <div><span class="badge ${amzClass}" style="font-size: 0.55rem; width: 100%;">Amz: ${r['AMZ Presence'] || 'PENDING'}</span></div>
                    </td>
                    <td>
                        <div class="action-links">
                            <a href="${r['Clean Amz']}" target="_blank" class="btn btn-amz"><i class="fa-brands fa-amazon"></i></a>
                            <a href="${r['Clean Source']}" target="_blank" class="btn btn-source"><i class="fa-solid fa-link"></i></a>
                        </div>
                    </td>
                `;
                
                if (currentTab !== 'ALL' && badgeText !== 'WINNER') {
                    tr.style.display = 'none';
                }
                tbody.appendChild(tr);
            });
        }

        function switchTab(tab, el) {
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            el.classList.add('active');
            currentTab = tab;
            
            if(tab === 'finance') {
                document.getElementById('dashboard-view').style.display = 'none';
                document.getElementById('finance-view').style.display = 'block';
            } else {
                document.getElementById('dashboard-view').style.display = 'block';
                document.getElementById('finance-view').style.display = 'none';
                document.getElementById('page-title').innerText = tab === 'WINNER' ? "Winning Leads" : "Market Intel Database";
                pollData();
            }
        }

        setInterval(pollData, 3000);
        pollData();
    </script>
</body>
</html>
"""

def clean_url(url):
    if pd.isna(url) or str(url).strip().lower() in ['n/a', 'nan', 'none', '']: return ""
    match = re.search(r'href=[\'"]?([^\'" >]+)', str(url))
    return match.group(1) if match else (url if str(url).startswith('http') else f"https://{url}")

def build_amz_link(row):
    link = clean_url(row.get('Amz Link', ''))
    if link: return link
    title = str(row.get('Product Title', '')).strip()
    return f"https://www.amazon.com/s?k={urllib.parse.quote(title[:50])}" if title and title.lower() != 'n/a' else "https://www.amazon.com/"

def process_db():
    if not os.path.exists(DB_PATH): 
        return [], 0, 0, 0, "empty"
    try:
        df = pd.read_csv(DB_PATH).fillna('N/A')
        df['Clean Source'] = df.get('Source Link', '').apply(lambda x: clean_url(x) or "#")
        df['Clean Amz'] = df.apply(build_amz_link, axis=1)
        if 'Date Scanned' in df.columns: df = df.sort_values(by='Date Scanned', ascending=False)
        
        data_dict = df.to_dict(orient='records')
        total = len(df)
        cats = df['Category'].nunique() if 'Category' in df.columns else 0
        wins = len(df[df['Lead Status'] == 'WINNING_LEAD']) if 'Lead Status' in df.columns else 0
        data_hash = str(total) + "_" + str(wins)
        
        return data_dict, total, cats, wins, data_hash
    except:
        return [], 0, 0, 0, "error"

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    data, total, cats, wins, data_hash = process_db()
    return jsonify({'data': data, 'total': total, 'cats': cats, 'wins': wins, 'hash': data_hash})

if __name__ == '__main__':
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app.run(host='127.0.0.1', port=5000, debug=False)
