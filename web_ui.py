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
    <title>Arbitrage Master | Terminal</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --bg-base: #000000;
            --bg-panel: #0a0a0a;
            --bg-hover: #171717;
            --border-color: #262626;
            --text-main: #ededed;
            --text-muted: #a1a1aa;
            --accent: #3b82f6;
            --success: #22c55e;
            --danger: #ef4444;
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-base);
            color: var(--text-main);
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        .app-container {
            display: flex;
            width: 100%;
            max-width: 1600px; 
            margin: 0 auto;
        }

        /* SIDEBAR */
        .sidebar {
            width: 260px;
            background-color: var(--bg-base);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            padding: 24px 16px;
            flex-shrink: 0;
        }
        
        .logo { font-size: 1.1rem; font-weight: 700; letter-spacing: 1px; margin-bottom: 32px; padding-left: 12px; }
        .logo i { color: var(--accent); margin-right: 8px; }
        
        .nav-link {
            display: flex;
            align-items: center;
            padding: 10px 12px;
            color: var(--text-muted);
            text-decoration: none;
            border-radius: 6px;
            font-size: 0.9rem;
            font-weight: 500;
            margin-bottom: 4px;
            transition: 0.2s ease;
            cursor: pointer;
        }
        .nav-link i { width: 24px; font-size: 1.1rem; }
        .nav-link:hover { background-color: var(--bg-hover); color: var(--text-main); }
        .nav-link.active { background-color: var(--bg-hover); color: var(--text-main); border: 1px solid var(--border-color); }
        .soon-badge { margin-left: auto; font-size: 0.65rem; background: var(--border-color); padding: 2px 6px; border-radius: 4px; text-transform: uppercase; letter-spacing: 1px; }

        /* MAIN CONTENT */
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 32px;
            overflow-y: auto;
            background-color: var(--bg-base);
        }

        .header { margin-bottom: 24px; }
        .header h2 { font-size: 1.5rem; font-weight: 600; }
        
        /* METRICS */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }
        .metric-card {
            background-color: var(--bg-panel);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
        }
        .metric-title { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); margin-bottom: 8px; font-weight: 600; }
        .metric-value { font-size: 2rem; font-weight: 700; }

        /* TABLE */
        .table-wrapper {
            background-color: var(--bg-panel);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            table-layout: fixed; 
            border-collapse: collapse;
            text-align: left;
        }
        
        th.col-status { width: 110px; }
        th.col-date { width: 100px; cursor: pointer; }
        th.col-date:hover { color: var(--text-main); }
        th.col-product { width: 280px; }
        th.col-cost { width: 90px; }
        th.col-amz { width: 90px; }
        th.col-profit { width: 90px; }
        th.col-actions { width: 155px; } /* Widened to fit both buttons perfectly */

        th, td {
            padding: 14px 16px;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.85rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis; 
        }
        
        th { color: var(--text-muted); font-weight: 500; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; background-color: var(--bg-panel); }
        tr:hover { background-color: var(--bg-hover); }

        /* BADGES */
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.5px; }
        .badge.winner { background: rgba(34, 197, 94, 0.1); color: var(--success); border: 1px solid rgba(34, 197, 94, 0.2); }
        .badge.not-found { background: rgba(239, 68, 68, 0.1); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.2); }
        .badge.default { background: var(--border-color); color: var(--text-muted); }

        .profit-pos { color: var(--success); font-weight: 600; }
        .profit-neg { color: var(--danger); font-weight: 600; }

        /* BUTTONS */
        .action-links { display: flex; gap: 6px; }
        .btn {
            text-decoration: none;
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 0.7rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            transition: 0.2s;
        }
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
        
        <!-- SIDEBAR -->
        <div class="sidebar">
            <div class="logo"><i class="fa-solid fa-bolt"></i> ARBMASTER</div>
            
            <a onclick="filterTableByStatus('ALL', this)" class="nav-link active" id="nav-dash"><i class="fa-solid fa-chart-line"></i> Dashboard</a>
            <a onclick="filterTableByStatus('WINNER', this)" class="nav-link" id="nav-win"><i class="fa-solid fa-trophy"></i> Winning Leads</a>
            
            <div style="margin-top: 32px; margin-bottom: 8px; padding-left: 12px; font-size: 0.7rem; color: var(--text-muted); font-weight: 600; letter-spacing: 1px;">ANALYTICS</div>
            <a onclick="alert('The Categories module is currently in development for V2!')" class="nav-link"><i class="fa-solid fa-boxes-stacked"></i> Categories <span class="soon-badge">Soon</span></a>
            <a onclick="alert('The Financial Market Intel module is currently in development for V2!')" class="nav-link"><i class="fa-solid fa-sack-dollar"></i> Finance <span class="soon-badge">Soon</span></a>
        </div>

        <!-- MAIN -->
        <div class="main-content">
            <div class="header">
                <h2 id="page-title">Lead Database</h2>
            </div>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-title">Total Scanned</div>
                    <div class="metric-value">{{ total_leads }}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">Categories</div>
                    <div class="metric-value" style="color: var(--accent);">{{ unique_cats }}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">Winning Leads</div>
                    <div class="metric-value" style="color: var(--success);">{{ winning_leads }}</div>
                </div>
            </div>

            <div class="table-wrapper">
                <table id="leadsTable">
                    <thead>
                        <tr>
                            <th class="col-status">Status</th>
                            <th class="col-date" onclick="sortData(1)">Date <i class="fa-solid fa-sort" style="margin-left: 4px;"></i></th>
                            <th class="col-product">Product</th>
                            <th class="col-cost">Buy Cost</th>
                            <th class="col-amz">Amz Price</th>
                            <th class="col-profit">Net Profit</th>
                            <th class="col-actions">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in data %}
                        <tr class="data-row">
                            <td>
                                {% if row['Lead Status'] == 'WINNING_LEAD' %}
                                    <span class="badge winner">WINNER</span>
                                {% elif row['Lead Status'] == 'NOT_FOUND' %}
                                    <span class="badge not-found">NOT FOUND</span>
                                {% else %}
                                    <span class="badge default">{{ row['Lead Status'] }}</span>
                                {% endif %}
                            </td>
                            <td style="color: var(--text-muted); font-family: monospace;">{{ row['Date Scanned'] }}</td>
                            <td>
                                <div style="font-weight: 500; overflow: hidden; text-overflow: ellipsis;" title="{{ row['Product Title'] }}">{{ row['Product Title'] }}</div>
                                <div style="font-size: 0.75rem; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; margin-top: 2px;" title="{{ row['Description'] }}">{{ row['Description'] }}</div>
                            </td>
                            <td>{{ row['Buy Cost'] }}</td>
                            <td style="color: var(--text-muted);">{{ row['Amz Price'] }}</td>
                            <td class="{% if '-' in str(row['Net Profit']) or row['Net Profit'] == 'N/A' %}profit-neg{% else %}profit-pos{% endif %}">
                                {{ row['Net Profit'] }}
                            </td>
                            <td>
                                <div class="action-links">
                                    <a href="{{ row['Clean Amz'] }}" target="_blank" class="btn btn-amz"><i class="fa-brands fa-amazon"></i> Amz</a>
                                    <a href="{{ row['Clean Source'] }}" target="_blank" class="btn btn-source"><i class="fa-solid fa-link"></i> Link</a>
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
        // SIDEBAR FILTER LOGIC
        function filterTableByStatus(status, element) {
            // Update UI
            document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
            element.classList.add('active');
            
            if(status === 'WINNER') {
                document.getElementById('page-title').innerText = "Winning Leads Database";
            } else {
                document.getElementById('page-title').innerText = "Lead Database";
            }

            // Filter Table
            const rows = document.querySelectorAll('.data-row');
            rows.forEach(row => {
                const badge = row.querySelector('.badge');
                if (!badge) return;
                
                if (status === 'ALL') {
                    row.style.display = ""; // Show all
                } else if (badge.innerText === status) {
                    row.style.display = ""; // Show matches
                } else {
                    row.style.display = "none"; // Hide non-matches
                }
            });
        }

        // SORTING LOGIC
        let sortAscending = false;
        function sortData(n) {
            const table = document.getElementById("leadsTable");
            let rows, switching, i, x, y, shouldSwitch;
            switching = true;
            sortAscending = !sortAscending;
            
            while (switching) {
                switching = false;
                rows = table.getElementsByTagName("TR");
                for (i = 1; i < (rows.length - 1); i++) {
                    shouldSwitch = false;
                    x = rows[i].getElementsByTagName("TD")[n];
                    y = rows[i + 1].getElementsByTagName("TD")[n];
                    if (sortAscending) {
                        if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) { shouldSwitch = true; break; }
                    } else {
                        if (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()) { shouldSwitch = true; break; }
                    }
                }
                if (shouldSwitch) {
                    rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                    switching = true;
                }
            }
        }
    </script>
</body>
</html>
"""

def extract_raw_url(url_string):
    """Safely extracts a clean URL if it was wrapped in HTML"""
    if pd.isna(url_string): return ""
    val = str(url_string).strip()
    if val.lower() in ['n/a', 'not found', 'none', 'nan', '']: return ""
    
    match = re.search(r'href=[\'"]?([^\'" >]+)', val)
    if match: return match.group(1)
    
    if not val.startswith('http'):
        val = 'https://' + val
    return val

@app.route('/')
def index():
    if os.path.exists(DB_PATH):
        try:
            df = pd.read_csv(DB_PATH)
            df = df.fillna('N/A')
            
            # Smart URL Engine
            for i, row in df.iterrows():
                
                # 1. Handle Source Links
                source_link = extract_raw_url(row.get('Source Link', ''))
                if source_link:
                    df.at[i, 'Clean Source'] = source_link
                else:
                    df.at[i, 'Clean Source'] = "#" # Fallback blank link
                
                # 2. Handle Amazon Links (Extract or Generate Search Query)
                amz_link = extract_raw_url(row.get('Amz Link', ''))
                if amz_link:
                    df.at[i, 'Clean Amz'] = amz_link
                else:
                    # If Amazon Link wasn't found, generate an automatic search link based on the product title!
                    title = str(row.get('Product Title', ''))
                    if title and title.lower() not in ['n/a', 'nan', 'none', '']:
                        clean_query = urllib.parse.quote(title[:50]) # Use first 50 chars of title
                        df.at[i, 'Clean Amz'] = f"https://www.amazon.com/s?k={clean_query}"
                    else:
                        df.at[i, 'Clean Amz'] = "https://www.amazon.com/"

            # Ensure newest first natively
            if 'Date Scanned' in df.columns:
                df = df.sort_values(by='Date Scanned', ascending=False)
                
            data = df.to_dict(orient='records')
            total_leads = len(df)
            unique_cats = df['Category'].nunique() if 'Category' in df.columns and len(df) > 0 else 0
            winning_leads = len(df[df['Lead Status'] == 'WINNING_LEAD']) if 'Lead Status' in df.columns else 0
        except Exception as e:
            print(f"Error loading DB: {e}")
            data, total_leads, unique_cats, winning_leads = [], 0, 0, 0
    else:
        data, total_leads, unique_cats, winning_leads = [], 0, 0, 0
        
    return render_template_string(HTML_TEMPLATE, data=data, total_leads=total_leads, unique_cats=unique_cats, winning_leads=winning_leads, str=str)

if __name__ == '__main__':
    print("\n[*] PRO Web UI is active! Open your browser and go to: http://127.0.0.1:5000\n")
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host='127.0.0.1', port=5000, debug=False)
