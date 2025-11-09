import os
import json
import requests
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from dotenv import load_dotenv
from datetime import datetime, timedelta

# --- Firebase Setup ---
import firebase_admin
from firebase_admin import credentials, firestore, auth

# Загрузка переменных окружения
load_dotenv() 

try:
    FIREBASE_CREDENTIALS_JSON = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if FIREBASE_CREDENTIALS_JSON:
        cred = credentials.Certificate(json.loads(FIREBASE_CREDENTIALS_JSON))
    else:
        cred = credentials.Certificate("path/to/your/serviceAccountKey.json")

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception:
    db = None 

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "A_SUPER_SECRET_KEY_FALLBACK_2025")

# --- PLACEHOLDERS (Обновленные заглушки) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")

MODULES_DATA = [
    {'id': 'm1', 'title': 'Модуль 1: Базовая Аутентификация', 
     'description': 'Демонстрация входа, выхода и защиты маршрутов. Длинное описание, чтобы проверить перенос текста.', 
     'author': 'Иван Смирнов', 'rating': 4.7, 'downloads': 1500,
     'commands': ['.login - Вход в систему', '.logout - Выход из системы', '.help - Помощь по командам']},
    {'id': 'm2', 'title': 'Модуль 2: Сбор Обратной Связи', 
     'description': 'Простая форма для предложений новых функций.', 
     'author': 'Петр Козлов', 'rating': 4.2, 'downloads': 800,
     'commands': ['.feedback - Отправить отзыв', '.suggest - Предложить идею']},
    {'id': 'm3', 'title': 'Модуль 3: Панель Администратора', 
     'description': 'Ограниченный доступ для управления контентом и просмотра предложений.', 
     'author': 'Администратор', 'rating': 4.9, 'downloads': 3000,
     'commands': ['.admin - Открыть панель', '.modlist - Список на модерации']},
]

CREATORS_DATA = [
    {'id': 'c1', 'username': '@esqueeare', 'modules_count': 5, 'reviews_rating': 4.8, 'avatar_url': '/static/user_avatar.png'},
    {'id': 'c2', 'username': '@Coder_Guy', 'modules_count': 3, 'reviews_rating': 4.5, 'avatar_url': '/static/user_avatar.png'},
    {'id': 'c3', 'username': '@Pixel_Dev', 'modules_count': 10, 'reviews_rating': 4.9, 'avatar_url': '/static/user_avatar.png'},
]
# ----------------------------------------------------------------------


# --- Decorators and Auth Logic (Оставлены для поддержки токенов) ---
def get_user_data(uid):
    """Получает данные пользователя из Firestore, включая роль и ник."""
    if not db: 
        # Заглушка для теста
        return {'uid': uid, 'telegram_username': 'Test User', 'role': 'admin', 'modules_count': 5, 'high_rating': 4.7, 'id_tg': 'N/A'}
    try:
        user_doc = db.collection('Users').document(uid).get()
        data = user_doc.to_dict() if user_doc.exists else {}
        data['uid'] = uid
        # Добавляем заглушки для полноты
        data['modules_count'] = data.get('modules_count', 5)
        data['high_rating'] = data.get('high_rating', 4.7)
        data['id_tg'] = data.get('id_tg', 'N/A')
        return data
    except Exception:
        return None

def get_auth_status():
    """Возвращает статус авторизации и данные пользователя для шаблонов."""
    logged_in = False
    is_admin = False
    user_data = None
    try:
        if 'token' in session:
            decoded_token = auth.verify_id_token(session['token'])
            uid = decoded_token['uid']
            user_data = get_user_data(uid)
            logged_in = True
            if user_data and user_data.get('role') == 'admin':
                is_admin = True
    except Exception:
        session.pop('token', None) 
    return logged_in, is_admin, user_data

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'token' not in session:
            return redirect(url_for('login_route')) 
        try:
            auth.verify_id_token(session['token'])
            return f(*args, **kwargs)
        except Exception:
            session.pop('token', None)
            return redirect(url_for('login_route'))
    return decorated_function

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        uid = auth.verify_id_token(session['token'])['uid']
        user_data = get_user_data(uid)
        if user_data and user_data.get('role') == 'admin':
            return f(*args, **kwargs)
        
        logged_in, is_admin, _ = get_auth_status()
        return render_template('error.html', 
                               title="Доступ Запрещен", 
                               message="У вас нет прав администратора.",
                               logged_in=logged_in, 
                               is_admin=is_admin), 403
    return decorated_function

# ----------------------------------------------------------------------

# --- CORE WEBSITE ROUTES (HTML) ---

@app.route('/')
def home():
    """Главная страница."""
    logged_in, is_admin, _ = get_auth_status()
    return render_template('home.html', 
                           title="Heroku Modules", 
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/modules')
def modules_list():
    """Список всех модулей."""
    logged_in, is_admin, _ = get_auth_status()
    return render_template('index.html', 
                           title="Каталог Модулей", 
                           modules=MODULES_DATA,
                           total_modules=len(MODULES_DATA),
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/module/<module_id>')
def module_detail(module_id):
    """Страница деталей модуля (Новая страница)."""
    logged_in, is_admin, _ = get_auth_status()
    module = next((m for m in MODULES_DATA if m['id'] == module_id), None)
    
    if module is None:
        # TODO: Создать шаблон error.html
        return "Модуль не найден", 404
        
    return render_template('module_detail.html', 
                           title=module['title'],
                           module=module,
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/creators')
def creators_list():
    """Список создателей (Новая страница)."""
    logged_in, is_admin, _ = get_auth_status()
    return render_template('creators.html', 
                           title="Список Создателей", 
                           creators=CREATORS_DATA,
                           total_creators=len(CREATORS_DATA),
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/submit', methods=['GET'])
@login_required
def submit_module_form():
    """Форма для подачи модуля."""
    logged_in, is_admin, user_data = get_auth_status()
    telegram_username = user_data.get('telegram_username', '') if user_data else ''
    
    return render_template('submit.html', 
                           title="Подать Модуль", 
                           telegram_username=telegram_username,
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/panel/moderatemod')
@admin_required
def moderation_panel():
    """Панель модерации."""
    logged_in, is_admin, _ = get_auth_status()
    pending_modules = MODULES_DATA 
    
    return render_template('admin.html', 
                           title="Панель Модерации", 
                           pending_modules=pending_modules,
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/account')
@login_required
def account_page():
    """Страница аккаунта."""
    logged_in, is_admin, user_data = get_auth_status()
    if user_data:
        user_data['role_display'] = user_data.get('role', 'user').upper()
    
    return render_template('account.html', 
                           title="Мой Аккаунт", 
                           user=user_data,
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/login')
def login_route():
    logged_in, _, _ = get_auth_status()
    if logged_in:
        return redirect(url_for('account_page'))
    return render_template('login.html', 
                           title="Вход",
                           logged_in=logged_in, 
                           is_admin=False)

@app.route('/logout')
def logout_route():
    session.pop('token', None)
    return redirect(url_for('modules_list'))

# --- CORE API ROUTES (JSON) ---

@app.route('/api/v1/auth', methods=['POST'])
def auth_api():
    """API для приема токена Firebase ID от клиента (после входа email/пароль), 
    его верификации и установки сессии."""
    data = request.get_json()
    id_token = data.get('idToken')
    
    if not id_token or not db:
        return jsonify({"success": False, "message": "Ошибка сервера или токен не предоставлен."}), 503

    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        session['token'] = id_token 
        
        # Регистрация/Обновление пользователя в Firestore
        user_doc = db.collection('Users').document(uid).get()
        if not user_doc.exists:
            # Создаем базовый профиль, если он не существует
            db.collection('Users').document(uid).set({
                'telegram_username': decoded_token.get('name', decoded_token.get('email', 'New User')),
                'email': decoded_token.get('email', 'N/A'),
                'role': 'user', 
                'created_at': firestore.SERVER_TIMESTAMP
            })
        
        return jsonify({"success": True, "message": "Успешный вход", "redirect": url_for('account_page')}), 200

    except auth.InvalidIdTokenError:
        return jsonify({"success": False, "message": "Недействительный токен."}), 401
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка верификации: {e}"}), 500

# Маршруты submit_module_api и analyze_module_code остаются без изменений

if __name__ == '__main__':
    # Включаем статическую папку для заглушек
    if not os.path.exists('static'): os.makedirs('static')
    with open('static/user_avatar.png', 'w') as f: f.write('') 
    if not os.path.exists('templates'): os.makedirs('templates')
    
    app.run(debug=True)
