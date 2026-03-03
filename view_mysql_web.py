"""
MySQL 資料庫網頁查看器
啟動後在瀏覽器開啟 http://localhost:5556
"""
from flask import Flask, render_template_string, request
import mysql.connector
from mysql.connector import Error
import sys

app = Flask(__name__)

# MySQL 連接設定（請修改這些參數）
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',  # 請在啟動時輸入
    'database': 'concerts',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MySQL 演唱會資料庫查看器</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Microsoft JhengHei', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .db-info {
            background: rgba(255,255,255,0.95);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .db-info strong { color: #667eea; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: rgba(255,255,255,0.95);
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-card h3 {
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }
        .stat-card .number {
            font-size: 36px;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .search-box {
            background: rgba(255,255,255,0.95);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        input[type="text"] {
            width: 100%;
            padding: 12px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 8px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        .filter-buttons {
            margin-top: 15px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .filter-btn {
            padding: 10px 20px;
            border: 2px solid #667eea;
            background: white;
            color: #667eea;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 500;
        }
        .filter-btn:hover, .filter-btn.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-color: transparent;
        }
        .table-container {
            background: rgba(255,255,255,0.95);
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
        }
        td {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }
        tbody tr:hover {
            background: #f8f9fa;
        }
        .badge {
            display: inline-block;
            padding: 5px 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 15px;
            font-size: 12px;
            font-weight: 500;
        }
        a {
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 MySQL 演唱會資料庫查看器</h1>
        
        <div class="db-info">
            <strong>📊 資料庫:</strong> {{ db_name }} | 
            <strong>🖥️  伺服器:</strong> {{ db_host }}:{{ db_port }}
        </div>
        
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
                <button class="filter-btn active" onclick="filterBySource('all')">全部顯示</button>
                {% for source, count in sources %}
                <button class="filter-btn" onclick="filterBySource('{{ source }}')">{{ source }} ({{ count }})</button>
                {% endfor %}
            </div>
        </div>

        <div class="table-container">
            <table id="eventsTable">
                <thead>
                    <tr>
                        <th>🎤 藝人</th>
                        <th>📅 時間</th>
                        <th>📍 地點</th>
                        <th>🎫 來源</th>
                        <th>🔗 連結</th>
                    </tr>
                </thead>
                <tbody>
                    {% for event in events %}
                    <tr data-source="{{ event[3] }}">
                        <td><strong>{{ event[0] or '未知' }}</strong></td>
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
        </div>
    </div>

    <script>
        let currentSource = 'all';
        
        function filterTable() {
            const input = document.getElementById('searchInput');
            const filter = input.value.toLowerCase();
            const table = document.getElementById('eventsTable');
            const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');

            for (let i = 0; i < rows.length; i++) {
                const row = rows[i];
                const source = row.getAttribute('data-source');
                
                if (currentSource !== 'all' && source !== currentSource) {
                    row.style.display = 'none';
                    continue;
                }
                
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            }
        }

        function filterBySource(source) {
            currentSource = source;
            
            const buttons = document.querySelectorAll('.filter-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            filterTable();
        }
    </script>
</body>
</html>
"""

def get_db_connection():
    """建立資料庫連接"""
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except Error as e:
        print(f"❌ 無法連接到 MySQL: {e}")
        sys.exit(1)

@app.route('/')
def index():
    try:
        conn = get_db_connection()
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
        
        # 所有活動（最新 500 筆）
        cursor.execute("""
            SELECT artist, event_time, venue, source, url
            FROM events 
            ORDER BY id DESC
            LIMIT 500
        """)
        events = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template_string(
            HTML_TEMPLATE,
            db_name=MYSQL_CONFIG['database'],
            db_host=MYSQL_CONFIG['host'],
            db_port=MYSQL_CONFIG['port'],
            total_count=total_count,
            sources=sources,
            events=events
        )
    except Error as e:
        return f"<h1>資料庫錯誤</h1><p>{e}</p>", 500

if __name__ == '__main__':
    import getpass
    
    print("=" * 60)
    print("🎵 MySQL 演唱會資料庫網頁查看器")
    print("=" * 60)
    
    # 輸入連接資訊
    print("\n請輸入 MySQL 連接資訊：")
    MYSQL_CONFIG['host'] = input(f"主機 (Enter={MYSQL_CONFIG['host']}): ").strip() or MYSQL_CONFIG['host']
    port_input = input(f"埠號 (Enter={MYSQL_CONFIG['port']}): ").strip()
    if port_input:
        MYSQL_CONFIG['port'] = int(port_input)
    MYSQL_CONFIG['user'] = input(f"使用者 (Enter={MYSQL_CONFIG['user']}): ").strip() or MYSQL_CONFIG['user']
    MYSQL_CONFIG['password'] = getpass.getpass("密碼: ")
    
    # 測試連接
    print(f"\n🔗 測試連接 {MYSQL_CONFIG['user']}@{MYSQL_CONFIG['host']}...")
    try:
        test_conn = get_db_connection()
        test_conn.close()
        print("✅ 連接成功！\n")
    except:
        print("❌ 連接失敗，請檢查設定\n")
        sys.exit(1)
    
    print("=" * 60)
    print("\n💻 網頁查看器啟動中...")
    print("\n🌐 請在瀏覽器開啟: http://localhost:5556")
    print("\n⌨️  按 Ctrl+C 停止伺服器\n")
    print("=" * 60)
    
    try:
        app.run(host='0.0.0.0', port=5556, debug=False)
    except KeyboardInterrupt:
        print("\n\n👋 伺服器已停止")
