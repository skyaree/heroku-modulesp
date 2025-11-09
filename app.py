import os
import json
import requests
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from dotenv import load_dotenv

# --- Firebase Setup (Остается без изменений) ---
import firebase_admin
from firebase_admin import credentials, firestore, auth

# Загрузка переменных окружения
load_dotenv() 

# Используйте JSON-файл или переменные окружения для credentials
try:
    FIREBASE_CREDENTIALS_JSON = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if FIREBASE_CREDENTIALS_JSON:
        cred = credentials.Certificate(json.loads(FIREBASE_CREDENTIALS_JSON))
    else:
        # ЗАМЕНА: Убедитесь, что этот путь настроен или используйте env vars
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
     'commands': ['.login - Вход в систему', '.logout - Выход из системы']},
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

# --- Decorators and Auth Logic (Остается без изменений) ---
# ... (Код функций get_user_data, get_auth_status, login_required, admin_required) ... 

# Добавляем функции из твоего app.py, чтобы они не потерялись.

def get_user_data(uid):
    """Получает данные пользователя из Firestore, включая роль и ник."""
    # Заглушка, если нет БД
    if not db: return {'uid': uid, 'telegram_username': 'Test User', 'role': 'admin', 'modules_count': 5, 'high_rating': 4.7}
    try:
        user_doc = db.collection('Users').document(uid).get()
        data = user_doc.to_dict() if user_doc.exists else {}
        # Добавляем заглушки для полноты
        data['uid'] = uid
        data['modules_count'] = 5 # TODO: Сделать подсчет
        data['high_rating'] = 4.7 # TODO: Сделать подсчет
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


# --- CORE WEBSITE ROUTES (HTML) ---

@app.route('/')
def home():
    """Главная страница с приветствием (Прототип 1000036982.png)"""
    logged_in, is_admin, _ = get_auth_status()
    return render_template('home.html', 
                           title="Heroku Modules", 
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/modules')
def modules_list():
    """Список всех модулей (Прототип 1000036983.png)."""
    logged_in, is_admin, _ = get_auth_status()
    # TODO: Получение и отображение одобренных модулей из Firestore
    return render_template('index.html', 
                           title="Каталог Модулей", 
                           modules=MODULES_DATA,
                           total_modules=len(MODULES_DATA), # Заглушка
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/module/<module_id>')
def module_detail(module_id):
    """Страница деталей модуля (Прототип 1000036984.png)."""
    logged_in, is_admin, _ = get_auth_status()
    module = next((m for m in MODULES_DATA if m['id'] == module_id), None)
    
    if module is None:
        return "Модуль не найден", 404
        
    return render_template('module_detail.html', 
                           title=module['title'],
                           module=module,
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/creators')
def creators_list():
    """Список создателей (Прототип 1000036985.png)."""
    logged_in, is_admin, _ = get_auth_status()
    # TODO: Получение списка создателей
    return render_template('creators.html', 
                           title="Список Создателей", 
                           creators=CREATORS_DATA,
                           total_creators=len(CREATORS_DATA), # Заглушка
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/submit', methods=['GET'])
@login_required
def submit_module_form():
    """Форма для подачи модуля (Прототип 1000036987.png)."""
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
    """Панель модерации (Прототип 1000036989.png)."""
    logged_in, is_admin, _ = get_auth_status()
    pending_modules = MODULES_DATA # Заглушка
    
    return render_template('admin.html', 
                           title="Панель Модерации", 
                           pending_modules=pending_modules,
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/account')
@login_required
def account_page():
    """Страница аккаунта (Прототипы 1000036986.png, 1000036988.png)."""
    logged_in, is_admin, user_data = get_auth_status()
    
    # Расширяем user_data для соответствия прототипу (если данных нет, используем заглушки)
    if user_data:
        user_data['id_tg'] = 'N/A' # TODO: Получить из БД
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

# ... (Маршруты /api/v1/auth, /api/v1/submit, /api/v1/analyze_code остаются без изменений) ... 

@app.route('/api/v1/auth', methods=['POST'])
def auth_api():
    """API для приема токена Firebase ID от клиента, его верификации и установки сессии."""
    data = request.get_json()
    id_token = data.get('idToken')
    
    if not id_token:
        return jsonify({"success": False, "message": "Токен не предоставлен."}), 400

    if not db:
        return jsonify({"success": False, "message": "Сервис временно недоступен. (Firebase Auth не инициализирован)"}), 503

    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        session['token'] = id_token 
        
        # Регистрация/Обновление пользователя в Firestore
        user_doc = db.collection('Users').document(uid).get()
        if not user_doc.exists:
            db.collection('Users').document(uid).set({
                # Используем никнейм из токена, если есть.
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


@app.route('/api/v1/submit', methods=['POST'])
@login_required
def submit_module_api():
    """API-маршрут для приема данных модуля."""
    data = request.get_json()
    # uid = auth.verify_id_token(session['token'])['uid'] # Раскомментировать после отладки
    uid = 'test_uid_123' # Заглушка для теста
    
    required_fields = ['name', 'author', 'commands', 'description', 'module_code', 'banner_url']
    if not all(field in data for field in required_fields):
        return jsonify({"success": False, "message": "Не все поля заполнены"}), 400

    module_data = {
        "name": data['name'],
        "author": data['author'],
        "commands": data['commands'],
        "description": data['description'],
        "module_code": data['module_code'],
        "banner_url": data['banner_url'], # Добавлено поле для баннера
        "developer_uid": uid,
        "status": "pending",
        "created_at": firestore.SERVER_TIMESTAMP,
        "downloads": 0
    }

    try:
        if db:
            db.collection('Modules').add(module_data)
        return jsonify({"success": True, "message": "Модуль отправлен на модерацию"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка БД: {e}"}), 500


@app.route('/api/v1/analyze_code', methods=['POST'])
@login_required
def analyze_module_code():
    """API для анализа кода с помощью Gemini."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        return jsonify({"success": False, "commands": "Анализ недоступен. Нет ключа API."}), 200
        
    code = request.get_json().get('code')
    if not code:
        return jsonify({"success": False, "commands": "Код не предоставлен."}), 400

    # ... (Логика Gemini API остается заглушкой) ...
    generated_text = ".search - Ищет модули в каталоге.\n.fheta - Проверяет версию модуля."
        
    return jsonify({"success": True, "commands": generated_text}), 200


if __name__ == '__main__':
    # Включаем статическую папку для заглушек
    if not os.path.exists('static'): os.makedirs('static')
    with open('static/user_avatar.png', 'w') as f: f.write('') # Заглушка для аватара
    
    # Создаем папку templates, если её нет
    if not os.path.exists('templates'): os.makedirs('templates')
    
    app.run(debug=True)
