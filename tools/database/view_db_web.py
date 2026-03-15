"""
簡易資料庫網頁查看器
啟動後在瀏覽器開啟 http://localhost:5555
"""
from flask import Flask, render_template_string, request
import sqlite3
import json

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>演唱會資料庫查看器</title>
    <style>
        body {
            font-family: 'Microsoft JhengHei', Arial, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            margin: 0 0 10px 0;
            color: #666;
            font-size: 14px;
        }
        .stat-card .number {
            font-size: 32px;
            font-weight: bold;
            color: #007bff;
        }
        table {
            width: 100%;
            background: white;
            border-collapse: collapse;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
        }
        th {
            background: #007bff;
            color: white;
            padding: 12px;
            text-align: left;
            position: sticky;
            top: 0;
        }
        td {
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .search-box {
            margin: 20px 0;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        input[type="text"] {
            width: 100%;
            padding: 10px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 4px;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #007bff;
        }
        .filter-buttons {
            margin: 10px 0;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .filter-btn {
            padding: 8px 16px;
            border: 2px solid #007bff;
            background: white;
            color: #007bff;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .filter-btn:hover, .filter-btn.active {
            background: #007bff;
            color: white;
        }
        a {
            color: #007bff;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <h1>🎵 演唱會資料庫查看器</h1>
    
    <div class="stats">
        <div class="stat-card">
            <h3>總活動數</h3>
            <div class="number">{{ total_count }}</div>
        </div>
        {% for source, count in sources[:5] %}
        <div class="stat-card">
            <h3>{{ source }}</h3>
            <div class="number">{{ count }}</div>
        </div>
        {% endfor %}
    </div>

    <div class="search-box">
        <input type="text" id="searchInput" placeholder="🔍 搜尋藝人、地點、時間..." onkeyup="filterTable()">
        <div class="filter-buttons">
            <button class="filter-btn active" onclick="filterBySource('all')">全部</button>
            {% for source, count in sources %}
            <button class="filter-btn" onclick="filterBySource('{{ source }}')">{{ source }}</button>
            {% endfor %}
        </div>
    </div>

    <table id="eventsTable">
        <thead>
            <tr>
                <th>藝人</th>
                <th>時間</th>
                <th>地點</th>
                <th>來源</th>
                <th>連結</th>
            </tr>
        </thead>
        <tbody>
            {% for event in events %}
            <tr data-source="{{ event[3] }}">
                <td>{{ event[0] or '未知' }}</td>
                <td>{{ event[1] or '未公布' }}</td>
                <td>{{ event[2] or '未公布' }}</td>
                <td><span class="badge">{{ event[3] or 'Unknown' }}</span></td>
                <td>
                    {% if event[4] %}
                    <a href="{{ event[4] }}" target="_blank">查看活動 →</a>
                    {% else %}
                    -
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <script>
        let currentSource = 'all';
        
        function filterTable() {
            const input = document.getElementById('searchInput');
            const filter = input.value.toLowerCase();
            const table = document.getElementById('eventsTable');
            const rows = table.getElementsByTagName('tr');

            for (let i = 1; i < rows.length; i++) {
                const row = rows[i];
                const source = row.getAttribute('data-source');
                
                // 檢查來源過濾
                if (currentSource !== 'all' && source !== currentSource) {
                    row.style.display = 'none';
                    continue;
                }
                
                // 檢查搜尋關鍵字
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            }
        }

        function filterBySource(source) {
            currentSource = source;
            
            // 更新按鈕樣式
            const buttons = document.querySelectorAll('.filter-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            filterTable();
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    conn = sqlite3.connect('data/concerts.db')
    cursor = conn.cursor()
    
    # 總數
    cursor.execute("SELECT COUNT(*) FROM events")
    total_count = cursor.fetchone()[0]
    
    # 各來源統計
    cursor.execute("""
        SELECT source, COUNT(*) as cnt 
        FROM events 
        GROUP BY source 
        ORDER BY cnt DESC
    """)
    sources = cursor.fetchall()
    
    # 所有活動
    cursor.execute("""
        SELECT artist, event_time, venue, source, url
        FROM events 
        ORDER BY id DESC
        LIMIT 500
    """)
    events = cursor.fetchall()
    
    conn.close()
    
    return render_template_string(
        HTML_TEMPLATE, 
        total_count=total_count,
        sources=sources,
        events=events
    )

if __name__ == '__main__':
    print("=" * 60)
    print("🎵 演唱會資料庫查看器")
    print("=" * 60)
    print("\n請在瀏覽器開啟: http://localhost:5555")
    print("\n按 Ctrl+C 停止伺服器\n")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5555, debug=False)
