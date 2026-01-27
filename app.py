"""
演唱會爬蟲 - 後端 API
支援使用者註冊、登入、關注演唱會、售票提醒等功能
"""
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
from datetime import datetime, timedelta
from functools import wraps
import uuid

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost:19000", "http://192.168.0.24:19000", "http://127.0.0.1:19000"])

# 設定
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# 資料檔案路徑
USERS_FILE = 'data/users.json'
CONCERTS_FILE = 'data/concerts.json'
FOLLOWS_FILE = 'data/follows.json'
REMINDERS_FILE = 'data/reminders.json'

# 確保資料目錄存在
os.makedirs('data', exist_ok=True)

# 初始化資料檔案
def init_data_files():
    """初始化必要的 JSON 資料檔案"""
    for file_path, default_content in [
        (USERS_FILE, {}),
        (CONCERTS_FILE, []),
        (FOLLOWS_FILE, {}),
        (REMINDERS_FILE, {}),
    ]:
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(default_content, f, ensure_ascii=False, indent=2)

init_data_files()

# =====================
# 資料操作函式
# =====================

def load_json(file_path):
    """載入 JSON 檔案"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {} if 'users' in file_path or 'follows' in file_path or 'reminders' in file_path else []

def save_json(file_path, data):
    """儲存 JSON 檔案"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_concerts():
    """從爬蟲或本地 JSON 載入演唱會資料，忽略非列表的狀態檔"""

    def _read_if_valid(path):
        """只有在內容為列表或包含 concerts/data 鍵時才返回，避免讀到 cookie 狀態檔"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                if isinstance(data.get('concerts'), list):
                    return data['concerts']
                if isinstance(data.get('data'), list):
                    return data['data']
        except Exception:
            return None
        return None

    # 1) 先用 data/concerts.json（若有）
    concerts = _read_if_valid(CONCERTS_FILE)
    if concerts:
        return concerts

    # 2) 忽略 cookie 狀態檔（kktix_state.json），只在內容是演唱會列表時才使用
    concerts = _read_if_valid('kktix_state.json')
    if concerts:
        return concerts
    
    # 3) 尋找最新的「演唱會資訊彙整_*.json」
    json_files = [f for f in os.listdir('.') if f.startswith('演唱會資訊彙整_') and f.endswith('.json')]
    if json_files:
        latest_file = sorted(json_files)[-1]
        concerts = _read_if_valid(latest_file)
        if concerts:
            return concerts
    
    # 4) 模擬資料（用於測試）
    return [
        {
            "來源網站": "KKTIX",
            "演出藝人": "五月天",
            "演出時間": "2026-02-15",
            "演出地點": "台北小巨蛋",
            "網址": "https://kktix.com/events/abc123",
            "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "來源網站": "Indievox",
            "演出藝人": "Coldplay",
            "演出時間": "2026-03-20",
            "演出地點": "台北南港展覽館",
            "網址": "https://indievox.com/events/xyz789",
            "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
    ]

def generate_concert_id(concert):
    """根據演唱會資訊生成 ID"""
    key = f"{concert['演出藝人']}_{concert['演出時間']}_{concert['演出地點']}"
    return str(abs(hash(key)) % (10 ** 8))

# =====================
# 中間件
# =====================

def require_login(f):
    """要求登入的裝飾器 - 支援 session 或 X-User-Id header"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 優先使用 session
        if 'user_id' in session:
            return f(*args, **kwargs)
        
        # 如果沒有 session，檢查 header
        user_id = request.headers.get('X-User-Id')
        if user_id:
            # 臨時設置 session，讓後續代碼可以使用
            session['user_id'] = user_id
            return f(*args, **kwargs)
        
        return jsonify({'status': 'error', 'message': '未登入'}), 401
    return decorated_function

# =====================
# 認證 API
# =====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """使用者註冊"""
    data = request.json
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    # 驗證
    if not username or not email or not password:
        return jsonify({'status': 'error', 'message': '使用者名稱、信箱和密碼不能為空'}), 400
    
    if len(password) < 6:
        return jsonify({'status': 'error', 'message': '密碼至少需要 6 個字元'}), 400
    
    users = load_json(USERS_FILE)
    
    # 檢查使用者是否已存在
    if any(u['email'] == email for u in users.values()):
        return jsonify({'status': 'error', 'message': '信箱已被註冊'}), 400
    
    if any(u['username'] == username for u in users.values()):
        return jsonify({'status': 'error', 'message': '使用者名稱已被使用'}), 400
    
    # 建立使用者
    user_id = str(uuid.uuid4())
    users[user_id] = {
        'user_id': user_id,
        'username': username,
        'email': email,
        'password': generate_password_hash(password),
        'created_at': datetime.now().isoformat(),
        'preferences': {
            'genres': [],  # 喜歡的類型
            'venues': [],  # 喜歡的場地
            'artists': [],  # 喜歡的藝人
            'notification_enabled': True
        }
    }
    
    save_json(USERS_FILE, users)
    
    return jsonify({
        'status': 'success',
        'message': '註冊成功',
        'user_id': user_id
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    """使用者登入"""
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'status': 'error', 'message': '信箱和密碼不能為空'}), 400
    
    users = load_json(USERS_FILE)
    
    # 查找使用者
    user = next((u for u in users.values() if u['email'] == email), None)
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'status': 'error', 'message': '信箱或密碼錯誤'}), 401
    
    # 設定 session
    session['user_id'] = user['user_id']
    session['username'] = user['username']
    
    return jsonify({
        'status': 'success',
        'message': '登入成功',
        'user': {
            'user_id': user['user_id'],
            'username': user['username'],
            'email': user['email']
        }
    }), 200

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """使用者登出"""
    session.clear()
    return jsonify({'status': 'success', 'message': '登出成功'}), 200

@app.route('/api/auth/profile', methods=['GET'])
@require_login
def get_profile():
    """取得使用者資料"""
    users = load_json(USERS_FILE)
    user = users.get(session['user_id'])
    
    if not user:
        return jsonify({'status': 'error', 'message': '使用者不存在'}), 404
    
    return jsonify({
        'status': 'success',
        'user': {
            'user_id': user['user_id'],
            'username': user['username'],
            'email': user['email'],
            'preferences': user.get('preferences', {})
        }
    }), 200

@app.route('/api/auth/profile', methods=['PUT'])
@require_login
def update_profile():
    """更新使用者資料"""
    data = request.json
    users = load_json(USERS_FILE)
    user = users.get(session['user_id'])
    
    if not user:
        return jsonify({'status': 'error', 'message': '使用者不存在'}), 404
    
    # 更新偏好設定
    if 'preferences' in data:
        user['preferences'].update(data['preferences'])
    
    save_json(USERS_FILE, users)
    
    return jsonify({
        'status': 'success',
        'message': '資料已更新',
        'user': {
            'user_id': user['user_id'],
            'username': user['username'],
            'email': user['email'],
            'preferences': user.get('preferences', {})
        }
    }), 200

# =====================
# 演唱會 API
# =====================

@app.route('/api/concerts', methods=['GET'])
def get_concerts():
    """取得所有演唱會列表 - 優先返回真實網站爬取的資料"""
    concerts = load_concerts()
    
    if not concerts:
        return jsonify({
            'status': 'success',
            'total': 0,
            'concerts': [],
            'message': '暫無演唱會資料，請先執行爬蟲'
        }), 200
    
    # 添加 ID 欄位
    for concert in concerts:
        if 'id' not in concert:
            concert['id'] = generate_concert_id(concert)
    
    # 支援搜尋和過濾
    query = request.args.get('q', '').lower()
    venue = request.args.get('venue', '').lower()
    artist = request.args.get('artist', '').lower()
    
    filtered = concerts
    if query:
        filtered = [c for c in filtered if 
                   query in str(c.get('演出藝人', '')).lower() or 
                   query in str(c.get('演出地點', '')).lower()]
    if venue:
        filtered = [c for c in filtered if venue in str(c.get('演出地點', '')).lower()]
    if artist:
        filtered = [c for c in filtered if artist in str(c.get('演出藝人', '')).lower()]
    
    return jsonify({
        'status': 'success',
        'total': len(filtered),
        'concerts': filtered,
        'data_source': '真實網站'
    }), 200

@app.route('/api/concerts/<concert_id>', methods=['GET'])
def get_concert(concert_id):
    """取得單個演唱會詳細資訊"""
    concerts = load_concerts()
    
    for concert in concerts:
        if 'id' not in concert:
            concert['id'] = generate_concert_id(concert)
        if concert['id'] == concert_id:
            return jsonify({
                'status': 'success',
                'concert': concert
            }), 200
    
    return jsonify({'status': 'error', 'message': '演唱會不存在'}), 404

@app.route('/api/concerts/by-artist/list', methods=['GET'])
def get_concerts_by_artist():
    """取得按藝人分類的演唱會列表"""
    concerts = load_concerts()
    
    # 為每個演唱會添加ID
    for concert in concerts:
        if 'id' not in concert:
            concert['id'] = generate_concert_id(concert)
    
    # 按藝人名稱分類
    artist_concerts = {}
    for concert in concerts:
        artist = concert.get('演出藝人', '未知藝人').strip()
        if artist not in artist_concerts:
            artist_concerts[artist] = []
        artist_concerts[artist].append(concert)
    
    # 按藝人名稱排序
    sorted_artists = sorted(artist_concerts.keys())
    
    # 構建分類結果
    result = []
    for artist in sorted_artists:
        # 同一藝人的演唱會按日期排序
        concerts_by_artist = sorted(
            artist_concerts[artist],
            key=lambda x: x.get('演出時間', ''),
            reverse=True
        )
        result.append({
            'artist': artist,
            'concert_count': len(concerts_by_artist),
            'concerts': concerts_by_artist
        })
    
    return jsonify({
        'status': 'success',
        'total_artists': len(result),
        'artist_list': result
    }), 200

@app.route('/api/concerts/artists', methods=['GET'])
def get_artist_list():
    """取得所有藝人列表（用於搜尋和過濾）"""
    concerts = load_concerts()
    
    # 收集所有藝人
    artists = set()
    for concert in concerts:
        artist = concert.get('演出藝人', '').strip()
        if artist and artist != '未知藝人':
            artists.add(artist)
    
    # 按字母順序排序
    sorted_artists = sorted(list(artists))
    
    return jsonify({
        'status': 'success',
        'total': len(sorted_artists),
        'artists': sorted_artists
    }), 200

@app.route('/api/concerts/by-artist/<artist_name>', methods=['GET'])
def get_concerts_by_specific_artist(artist_name):
    """取得特定藝人的所有演唱會"""
    concerts = load_concerts()
    
    # 為每個演唱會添加ID
    for concert in concerts:
        if 'id' not in concert:
            concert['id'] = generate_concert_id(concert)
    
    # 過濾特定藝人的演唱會
    artist_concerts = [
        c for c in concerts 
        if c.get('演出藝人', '').lower() == artist_name.lower()
    ]
    
    # 按日期排序
    artist_concerts = sorted(
        artist_concerts,
        key=lambda x: x.get('演出時間', ''),
        reverse=True
    )
    
    return jsonify({
        'status': 'success',
        'artist': artist_name,
        'total': len(artist_concerts),
        'concerts': artist_concerts
    }), 200

# =====================
# 關注 API
# =====================

@app.route('/api/follows', methods=['GET'])
@require_login
def get_follows():
    """取得使用者的關注列表"""
    follows = load_json(FOLLOWS_FILE)
    user_follows = follows.get(session['user_id'], [])
    
    # 取得關注演唱會的詳細資訊
    concerts = load_concerts()
    followed_concerts = []
    
    for concert in concerts:
        concert_id = concert.get('id') or generate_concert_id(concert)
        if concert_id in user_follows:
            concert['id'] = concert_id
            concert['followed'] = True
            followed_concerts.append(concert)
    
    return jsonify({
        'status': 'success',
        'total': len(followed_concerts),
        'concerts': followed_concerts
    }), 200

@app.route('/api/follows/<concert_id>', methods=['POST'])
@require_login
def follow_concert(concert_id):
    """關注演唱會"""
    follows = load_json(FOLLOWS_FILE)
    
    if session['user_id'] not in follows:
        follows[session['user_id']] = []
    
    if concert_id not in follows[session['user_id']]:
        follows[session['user_id']].append(concert_id)
        save_json(FOLLOWS_FILE, follows)
    
    return jsonify({
        'status': 'success',
        'message': '已關注'
    }), 201

@app.route('/api/follows/<concert_id>', methods=['DELETE'])
@require_login
def unfollow_concert(concert_id):
    """取消關注演唱會"""
    follows = load_json(FOLLOWS_FILE)
    
    if session['user_id'] in follows and concert_id in follows[session['user_id']]:
        follows[session['user_id']].remove(concert_id)
        save_json(FOLLOWS_FILE, follows)
    
    return jsonify({
        'status': 'success',
        'message': '已取消關注'
    }), 200

@app.route('/api/follows/<concert_id>/check', methods=['GET'])
@require_login
def check_follow(concert_id):
    """檢查是否已關注"""
    follows = load_json(FOLLOWS_FILE)
    is_followed = concert_id in follows.get(session['user_id'], [])
    
    return jsonify({
        'status': 'success',
        'followed': is_followed
    }), 200

# =====================
# 提醒 API
# =====================

@app.route('/api/reminders', methods=['GET'])
@require_login
def get_reminders():
    """取得使用者的提醒設定"""
    reminders = load_json(REMINDERS_FILE)
    user_reminders = reminders.get(session['user_id'], {})
    
    return jsonify({
        'status': 'success',
        'reminders': user_reminders
    }), 200

@app.route('/api/reminders/<concert_id>', methods=['POST'])
@require_login
def set_reminder(concert_id):
    """為演唱會設定提醒"""
    data = request.json or {}
    reminder_type = data.get('type', 'on_sale')  # on_sale, one_day_before, etc.
    
    reminders = load_json(REMINDERS_FILE)
    
    if session['user_id'] not in reminders:
        reminders[session['user_id']] = {}
    
    reminders[session['user_id']][concert_id] = {
        'type': reminder_type,
        'enabled': True,
        'created_at': datetime.now().isoformat()
    }
    
    save_json(REMINDERS_FILE, reminders)
    
    return jsonify({
        'status': 'success',
        'message': '提醒已設定'
    }), 201

@app.route('/api/reminders/<concert_id>', methods=['DELETE'])
@require_login
def delete_reminder(concert_id):
    """刪除演唱會提醒"""
    reminders = load_json(REMINDERS_FILE)
    
    if session['user_id'] in reminders and concert_id in reminders[session['user_id']]:
        del reminders[session['user_id']][concert_id]
        save_json(REMINDERS_FILE, reminders)
    
    return jsonify({
        'status': 'success',
        'message': '提醒已刪除'
    }), 200

# =====================
# AI 搜索功能 - 使用 Gemini 直接生成演唱會資訊
# =====================

@app.route('/api/concerts/generate-all', methods=['POST'])
def generate_all_concerts_with_ai():
    """讓 AI 訪問真實網站，抓取並分類演唱會資訊"""
    try:
        import google.generativeai as genai
        
        GEMINI_API_KEY = "AIzaSyA-fcrKtbwsk_j7Xwf6IsQytoMeqU64HQI"
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 要抓取的真實網站列表
        websites = [
            {
                'name': 'iNDIEVOX',
                'url': 'https://www.indievox.com/activity/list',
                'description': '台灣獨立音樂廠商售票平台'
            },
            {
                'name': 'Accupass',
                'url': 'https://www.accupass.com/search?q=演唱會',
                'description': '台灣活動通票券販售平台'
            }
        ]
        
        all_concerts = []
        
        # 為每個網站抓取並分析
        for website in websites:
            try:
                print(f"正在訪問 {website['name']}...")
                resp = requests.get(website['url'], headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }, timeout=10)
                
                if resp.status_code != 200:
                    continue
                
                # 將 HTML 發送給 AI 分析
                html_content = resp.text[:10000]  # 只取前 10000 字元避免超長
                
                prompt = f"""
你是票券分析專家。請分析以下來自 {website['name']} 的 HTML，
提取所有演唱會/音樂會資訊。

返回 JSON 陣列，每筆包含：
{{"artist": "藝人名稱", "date": "日期時間", "venue": "地點", "price": "票價", "url": "連結"}}

只返回 JSON，不要其他文字。如果找不到資訊，返回 []

HTML 內容：
{html_content}
"""
                
                response = gemini_model.generate_content(prompt, stream=False)
                response_text = response.text.strip()
                
                # 清理 markdown
                if response_text.startswith('```'):
                    response_text = response_text.split('```')[1]
                    if response_text.startswith('json'):
                        response_text = response_text[4:]
                    response_text = response_text.split('```')[0].strip()
                
                # 解析並添加網站資訊
                try:
                    concerts = json.loads(response_text)
                    if isinstance(concerts, list):
                        for concert in concerts:
                            if concert.get('artist'):
                                concert['site'] = website['name']
                                all_concerts.append(concert)
                except:
                    pass
                    
            except Exception as e:
                print(f"  訪問 {website['name']} 失敗: {e}")
                continue
        
        # 轉換格式並分類
        valid_concerts = []
        for item in all_concerts:
            if item.get('artist'):
                valid_concerts.append({
                    '來源網站': item.get('site', '未知'),
                    '演出藝人': str(item.get('artist', '')).strip(),
                    '演出時間': str(item.get('date', '未公布')).strip(),
                    '演出地點': str(item.get('venue', '未公布')).strip(),
                    '票價': str(item.get('price', '')).strip(),
                    '網址': str(item.get('url', '')).strip(),
                    '爬取時間': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        
        # 保存到檔案
        os.makedirs('data', exist_ok=True)
        with open(CONCERTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(valid_concerts, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'status': 'success',
            'message': f'已從真實網站抓取並分類 {len(valid_concerts)} 筆演唱會資訊',
            'count': len(valid_concerts),
            'data_source': '真實網站',
            'concerts': valid_concerts[:10]
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'抓取失敗: {str(e)}'
        }), 500

@app.route('/api/concerts/search', methods=['POST'])
def search_concerts_with_ai():
    """使用 AI 搜索演唱會資訊
    
    請求 JSON:
    {
        "query": "五月天 2026",
        "limit": 10  // 可選，預設 10
    }
    """
    try:
        # 延遲導入，避免模組不存在時服務啟動失敗
        import google.generativeai as genai
        
        # 初始化 Gemini
        GEMINI_API_KEY = "AIzaSyA-fcrKtbwsk_j7Xwf6IsQytoMeqU64HQI"
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        limit = data.get('limit', 10)
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': '請輸入搜索關鍵字'
            }), 400
        
        # 調用 Gemini AI
        prompt = f"""
你是台灣演唱會資訊助手。請根據以下搜索條件，提供符合的演唱會資訊。

搜索條件: {query}
返回數量: 最多 {limit} 筆

請返回 JSON 格式，每筆包含：
- artist: 藝人名稱（必須）
- date: 演出日期時間，格式 "YYYY/MM/DD HH:MM"（如不確定返回 "待確認"）
- venue: 演出地點（如不確定返回 "待確認"）
- price: 票價範圍，例如 "600-3000"（可選）
- url: 購票連結（可選）

只返回 JSON 數組，不要其他文字。例如:
[
  {{"artist": "五月天", "date": "2026/02/15 19:30", "venue": "台北小巨蛋", "price": "1200-3500", "url": ""}},
  ...
]
"""
        
        response = gemini_model.generate_content(prompt)
        response_text = response.text.strip()
        
        # 清理 markdown 格式
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.split('```')[0]
        
        response_text = response_text.strip()
        
        # 解析 JSON
        try:
            concerts = json.loads(response_text)
        except json.JSONDecodeError:
            concerts = []
        
        # 驗證資料
        valid_concerts = []
        if isinstance(concerts, list):
            for item in concerts:
                if isinstance(item, dict) and item.get('artist'):
                    valid_concerts.append({
                        '來源網站': 'AI 搜索',
                        '演出藝人': item.get('artist', '').strip(),
                        '演出時間': item.get('date', '待確認').strip(),
                        '演出地點': item.get('venue', '待確認').strip(),
                        '票價': item.get('price', '').strip(),
                        '網址': item.get('url', '').strip(),
                        '爬取時間': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
        
        return jsonify({
            'status': 'success',
            'query': query,
            'count': len(valid_concerts),
            'concerts': valid_concerts
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'搜索失敗: {str(e)}'
        }), 500

# =====================
# 健康檢查
# =====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({
        'status': 'success',
        'message': 'API is running',
        'timestamp': datetime.now().isoformat()
    }), 200

# =====================
# 錯誤處理
# =====================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'status': 'error', 'message': '不存在'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'status': 'error', 'message': '伺服器內部錯誤'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
