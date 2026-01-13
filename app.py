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
REVIEWS_FILE = 'data/reviews.json'

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
        (REVIEWS_FILE, {}),
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
    """取得所有演唱會列表"""
    concerts = load_concerts()
    
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
        filtered = [c for c in filtered if query in c['演出藝人'].lower() or query in c['演出地點'].lower()]
    if venue:
        filtered = [c for c in filtered if venue in c['演出地點'].lower()]
    if artist:
        filtered = [c for c in filtered if artist in c['演出藝人'].lower()]
    
    return jsonify({
        'status': 'success',
        'total': len(filtered),
        'concerts': filtered
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
# 評價 API
# =====================

@app.route('/api/reviews/<concert_id>', methods=['GET'])
def get_reviews(concert_id):
    """取得演唱會的所有評價"""
    reviews = load_json(REVIEWS_FILE)
    concert_reviews = reviews.get(concert_id, {})
    review_list = []
    
    for review_id, review_data in concert_reviews.items():
        review_list.append({
            'id': review_id,
            **review_data
        })
    
    # 按評分和時間排序（高分優先）
    review_list.sort(key=lambda x: (-x.get('rating', 0), x.get('created_at', '')), reverse=True)
    
    # 計算平均評分
    avg_rating = 0
    if review_list:
        avg_rating = sum(r.get('rating', 0) for r in review_list) / len(review_list)
    
    return jsonify({
        'status': 'success',
        'concert_id': concert_id,
        'avg_rating': round(avg_rating, 1),
        'total_reviews': len(review_list),
        'reviews': review_list
    }), 200

@app.route('/api/reviews/<concert_id>', methods=['POST'])
def add_review(concert_id):
    """新增評價"""
    # 從 session 或 header 獲取 user_id
    user_id = session.get('user_id') or request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'status': 'error', 'message': '未登入'}), 401
    
    data = request.json or {}
    rating = data.get('rating', 0)
    comment = data.get('comment', '').strip()
    
    # 驗證
    if not (1 <= rating <= 5):
        return jsonify({'status': 'error', 'message': '評分必須在 1-5 之間'}), 400
    
    if len(comment) > 500:
        return jsonify({'status': 'error', 'message': '評論不能超過 500 個字元'}), 400
    
    users = load_json(USERS_FILE)
    user = users.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': '使用者不存在'}), 404
    
    reviews = load_json(REVIEWS_FILE)
    
    if concert_id not in reviews:
        reviews[concert_id] = {}
    
    review_id = str(uuid.uuid4())
    reviews[concert_id][review_id] = {
        'user_id': user_id,
        'username': user['username'],
        'rating': rating,
        'comment': comment,
        'created_at': datetime.now().isoformat()
    }
    
    save_json(REVIEWS_FILE, reviews)
    
    return jsonify({
        'status': 'success',
        'message': '評價已新增',
        'review': {
            'id': review_id,
            **reviews[concert_id][review_id]
        }
    }), 201

@app.route('/api/reviews/<concert_id>/<review_id>', methods=['DELETE'])
@require_login
def delete_review(concert_id, review_id):
    """刪除評價（僅限評論者本人）"""
    reviews = load_json(REVIEWS_FILE)
    
    if concert_id not in reviews or review_id not in reviews[concert_id]:
        return jsonify({'status': 'error', 'message': '評價不存在'}), 404
    
    review = reviews[concert_id][review_id]
    if review['user_id'] != session['user_id']:
        return jsonify({'status': 'error', 'message': '只能刪除自己的評價'}), 403
    
    del reviews[concert_id][review_id]
    save_json(REVIEWS_FILE, reviews)
    
    return jsonify({
        'status': 'success',
        'message': '評價已刪除'
    }), 200

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
