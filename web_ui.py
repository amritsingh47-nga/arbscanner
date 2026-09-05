from flask import Flask, render_template_string
import pandas as pd
import urllib.parse
import os
import re

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Database', 'Deep_Data_Database.csv')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arbitrage Master | Market Intel</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root { --bg-base: #000000; --bg-panel: #0a0a0a; --bg-hover: #171717; --border-color: #262626; --text-main: #ededed; --text-muted: #a1a1aa; --accent: #3b82f6; --success: #22c55e; --danger: #ef4444; }
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
        .soon-badge { margin-left: auto; font-size: 0.65rem; background: var(--border-color); padding: 2px 6px; border-radius: 4px; text-transform: uppercase; letter-spacing: 1px; }
        .main-content { flex: 1; display: flex; flex-direction: column; padding: 32px; overflow-y: auto; background-color: var(--bg-base); }
        .header { margin-bottom: 24px; }
        .header h2 { font-size: 1.5rem; font-weight: 600; }
        .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
        .metric-card { background-color: var(--bg-panel); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; }
        .metric-title { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); margin-bottom: 8px; font-weight: 600; }
        .metric-value { font-size: 2rem; font-weight: 700; }
        .table-wrapper { background-color: var(--bg-panel); border: 1px solid var(--border-color); border-radius: 12px; overflow-x: auto; }
        table { width: 100%; table-layout: fixed; border-collapse: collapse; text-align: left; }
        th.col-status { width: 100px; } th.col-date { width: 90px; cursor: pointer; } 
        th.col-product { width: 240px; } th.col-bsr { width: 80px; } 
        th.col-cost, th.col-fba, th.col-amz { width: 80px; } th.col-profit { width: 110px; } th.col-actions { width: 100px; }
        th, td { padding: 14px 12px; border-bottom: 1px solid var(--border-color); font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        th { color: var(--text-muted); font-weight: 500; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.5px; background-color: var(--bg-panel); }
        tr:hover { background-color: var(--bg-hover); }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.65rem; font-weight: 600; letter-spacing: 0.5px; }
        .badge.winner { background: rgba(34, 197, 94, 0.1); color: var(--success); border: 1px solid rgba(34, 197, 94, 0.2); }
        .badge.not-found { background: rgba(239, 68, 68, 0.1); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.2); }
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
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg-base); }
        ::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #3f3f46; }
    </style>
</head>
<body>
    <div class="app-container">
        <div class="sidebar">
            <div class="logo"><i class="fa-solid fa-bolt"></i> ARBMASTER</div>
            <a onclick="filterTable('ALL', this)" class="nav-link active"><i class="fa-solid fa-chart-line"></i> Dashboard</a>
            <a onclick="filterTable('WINNER', this)" class="nav-link"><i class="fa-solid fa-trophy"></i> Winning Leads</a>
            <div style="margin-top: 32px; margin-bottom: 8px; padding-left: 12px; font-size: 0.7rem; color: var(--text-muted); font-weight: 600; letter-spacing: 1px;">ANALYTICS</div>
            <a class="nav-link"><i class="fa-solid fa-boxes-stacked"></i> Categories <span class="soon-badge">Soon</span></a>
            <a class="nav-link"><i class="fa-solid fa-sack-dollar"></i> Finance <span class="soon-badge">Soon</span></a>
        </div>
        <div class="main-content">
            <div class="header"><h2 id="page-title">Market Intel Database</h2></div>
            <div class="metrics-grid">
                <div class="metric-card"><div class="metric-title">Total Scanned</div><div class="metric-value">{{ total }}</div></div>
                <div class="metric-card"><div class="metric-title">Categories</div><div class="metric-value" style="color: var(--accent);">{{ cats }}</div></div>
                <div class="metric-card"><div class="metric-title">Winning Leads</div><div class="metric-value" style="color: var(--success);">{{ wins }}</div></div>
            </div>
            <div class="table-wrapper">
                <table id="leadsTable">
                    <thead>
                        <tr>
                            <th class="col-status">Status</th><th class="col-date" onclick="sortData(1)">Date <i class="fa-solid fa-sort"></i></th>
                            <th class="col-product">Product</th><th class="col-bsr">BSR</th><th class="col-cost">Buy</th><th class="col-fba">FBA Fee</th><th class="col-amz">Amz</th>
                            <th class="col-profit">Profit / ROI</th><th class="col-actions">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for r in data %}
                        <tr class="data-row">
                            <td>
                                {% if r['Lead Status'] == 'WINNING_LEAD' %}<span class="badge winner">WINNER</span>
                                {% elif r['Lead Status'] == 'NOT_FOUND' %}<span class="badge not-found">NOT FOUND</span>
                                {% else %}<span class="badge default">{{ r['Lead Status'] }}</span>{% endif %}
                            </td>
                            <td style="color: var(--text-muted); font-family: monospace;">{{ r['Date Scanned'] }}</td>
                            <td>
                                <div style="font-weight: 500; overflow: hidden; text-overflow: ellipsis;" title="{{ r['Product Title'] }}">{{ r['Product Title'] }}</div>
                                <div style="font-size: 0.7rem; color: var(--accent); overflow: hidden; text-overflow: ellipsis; margin-top: 2px;">{{ r.get('Category', 'N/A') }}</div>
                            </td>
                            <td style="font-family: monospace; color: var(--text-muted);">{{ r.get('BSR', 'N/A') }}</td>
                            <td>{{ r['Buy Cost'] }}</td>
                            <td style="color: var(--danger);">{{ r.get('FBA Fee', 'N/A') }}</td>
                            <td style="color: var(--text-muted);">{{ r['Amz Price'] }}</td>
                            <td class="{% if '-' in r['Net Profit']|string or r['Net Profit'] == 'N/A' %}profit-neg{% else %}profit-pos{% endif %}">
                                <div>{{ r['Net Profit'] }}</div>
                                <div style="font-size: 0.65rem; font-weight: normal; margin-top: 2px;">ROI: {{ r.get('ROI %', 'N/A') }}</div>
                            </td>
                            <td>
                                <div class="action-links">
                                    <a href="{{ r['Clean Amz'] }}" target="_blank" class="btn btn-amz" title="Amazon"><i class="fa-brands fa-amazon"></i></a>
                                    <a href="{{ r['Clean Source'] }}" target="_blank" class="btn btn-source" title="Source"><i class="fa-solid fa-link"></i></a>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <script>
        function filterTable(status, el) {
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            el.classList.add('active');
            document.getElementById('page-title').innerText = status === 'WINNER' ? "Winning Leads" : "Market Intel Database";
            document.querySelectorAll('.data-row').forEach(row => {
                const badge = row.querySelector('.badge');
                row.style.display = (status === 'ALL' || (badge && badge.innerText === status)) ? "" : "none";
            });
        }
        let sortAsc = false;
        function sortData(n) {
            const table = document.getElementById("leadsTable");
            let rows, switching = true, i, x, y, shouldSwitch;
            sortAsc = !sortAsc;
            while (switching) {
                switching = false;
                rows = table.getElementsByTagName("TR");
                for (i = 1; i < (rows.length - 1); i++) {
                    shouldSwitch = false;
                    x = rows[i].getElementsByTagName("TD")[n];
                    y = rows[i + 1].getElementsByTagName("TD")[n];
                    if (sortAsc ? (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) : (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase())) {
                        shouldSwitch = true; break;
                    }
                }
                if (shouldSwitch) { rows[i].parentNode.insertBefore(rows[i + 1], rows[i]); switching = true; }
            }
        }
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

@app.route('/')
def index():
    if not os.path.exists(DB_PATH): return render_template_string(HTML_TEMPLATE, data=[], total=0, cats=0, wins=0)
    try:
        df = pd.read_csv(DB_PATH).fillna('N/A')
        df['Clean Source'] = df.get('Source Link', '').apply(lambda x: clean_url(x) or "#")
        df['Clean Amz'] = df.apply(build_amz_link, axis=1)
        if 'Date Scanned' in df.columns: df = df.sort_values(by='Date Scanned', ascending=False)
        return render_template_string(HTML_TEMPLATE, data=df.to_dict(orient='records'), total=len(df), 
                                      cats=df['Category'].nunique() if 'Category' in df.columns else 0, 
                                      wins=len(df[df['Lead Status'] == 'WINNING_LEAD']) if 'Lead Status' in df.columns else 0)
    except Exception as e: 
        print(f"Error loading CSV: {e}")
        return render_template_string(HTML_TEMPLATE, data=[], total=0, cats=0, wins=0)

if __name__ == '__main__':
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app.run(host='127.0.0.1', port=5000, debug=False)
