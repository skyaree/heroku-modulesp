import os
import json
import requests
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from dotenv import load_dotenv

# --- Firebase Setup ---
import firebase_admin
from firebase_admin import credentials, firestore, auth

# Загрузка переменных окружения (для локальной работы)
load_dotenv() 

# Используйте JSON-файл или переменные окружения для credentials
try:
    # Инициализация Firebase, как в оригинальном коде
    FIREBASE_CREDENTIALS_JSON = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if FIREBASE_CREDENTIALS_JSON:
        cred = credentials.Certificate(json.loads(FIREBASE_CREDENTIALS_JSON))
    else:
        # Для локального теста, используйте файл (не рекомендуется на продакшене)
        # Убедитесь, что этот путь настроен или используйте env vars
        cred = credentials.Certificate("path/to/your/serviceAccountKey.json")

    # Инициализируем приложение только один раз
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    # print(f"Ошибка инициализации Firebase: {e}") 
    db = None # Установим None, чтобы приложение могло запуститься без БД

app = Flask(__name__)
# Установите безопасный секретный ключ 
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "A_SUPER_SECRET_KEY_FALLBACK_2025")

# --- PLACEHOLDERS ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")

# --- ДОБАВЛЕННЫЕ ДАННЫЕ ДЛЯ ОТОБРАЖЕНИЯ МОДУЛЕЙ ---
MODULES_DATA = [
    {'id': 1, 'title': 'Модуль 1: Базовая Аутентификация', 
     'description': 'Демонстрация входа, выхода и защиты маршрутов.', 
     'author': 'Иван Смирнов'},
    {'id': 2, 'title': 'Модуль 2: Сбор Обратной Связи', 
     'description': 'Простая форма для предложений новых функций.', 
     'author': 'Петр Козлов'},
    {'id': 3, 'title': 'Модуль 3: Панель Администратора', 
     'description': 'Ограниченный доступ для управления контентом и просмотра предложений.', 
     'author': 'Администратор'},
]

# --- Decorators and Auth Logic ---

def get_user_data(uid):
    """Получает данные пользователя из Firestore, включая роль и ник."""
    if not db: return None 
    try:
        user_doc = db.collection('Users').document(uid).get()
        return user_doc.to_dict() if user_doc.exists else None
    except Exception:
        return None

def get_auth_status():
    """Возвращает статус авторизации и данные пользователя для шаблонов."""
    logged_in = False
    is_admin = False
    user_data = None
    try:
        if 'token' in session:
            # Проверяем токен
            decoded_token = auth.verify_id_token(session['token'])
            uid = decoded_token['uid']
            user_data = get_user_data(uid)
            logged_in = True
            # Проверяем роль
            if user_data and user_data.get('role') == 'admin':
                is_admin = True
    except Exception:
        session.pop('token', None) # Сброс невалидного токена
    return logged_in, is_admin, user_data

def login_required(f):
    """Декоратор для проверки аутентификации."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'token' not in session:
            return redirect(url_for('login_route')) 
        try:
            # Проверка токена (обязательно для API)
            auth.verify_id_token(session['token'])
            return f(*args, **kwargs)
        except Exception:
            session.pop('token', None)
            return redirect(url_for('login_route'))
    return decorated_function

def admin_required(f):
    """Декоратор для проверки прав администратора."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Логика проверки токена уже в login_required
        uid = auth.verify_id_token(session['token'])['uid']
        user_data = get_user_data(uid)
        if user_data and user_data.get('role') == 'admin':
            return f(*args, **kwargs)
        
        # Если не админ, но залогинен
        logged_in, is_admin, _ = get_auth_status()
        return render_template('error.html', 
                               title="Доступ Запрещен", 
                               message="У вас нет прав администратора.",
                               logged_in=logged_in, 
                               is_admin=is_admin), 403
    return decorated_function


# --- CORE WEBSITE ROUTES (HTML) ---

@app.route('/')
@app.route('/modules')
def modules_list():
    """Список всех модулей."""
    # Вместо TODO используем заглушку MODULES_DATA и реальный статус аутентификации
    logged_in, is_admin, _ = get_auth_status()
    
    # TODO: Получение и отображение одобренных модулей из Firestore
    
    return render_template('index.html', 
                           title="Каталог Модулей", 
                           modules=MODULES_DATA,
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/submit', methods=['GET'])
@login_required
def submit_module_form():
    """Форма для подачи модуля."""
    logged_in, is_admin, user_data = get_auth_status()
    
    # Получаем ник для предзаполнения
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
    
    # TODO: Получение модулей со статусом 'pending'
    pending_modules = MODULES_DATA # Заглушка
    
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
    
    # TODO: Отображение данных пользователя (ник, дата регистрации)
    
    return render_template('account.html', 
                           title="Мой Аккаунт", 
                           user=user_data,
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/login')
def login_route():
    """Страница входа."""
    logged_in, _, _ = get_auth_status()
    
    # Если пользователь уже залогинен, перенаправляем его в аккаунт
    if logged_in:
        return redirect(url_for('account_page'))
        
    # Здесь должна быть кнопка "Войти через Google"
    return render_template('login.html', 
                           title="Вход",
                           logged_in=logged_in, 
                           is_admin=False)


# --- CORE API ROUTES (JSON) ---
# ... (Оставлены без изменений, так как они не затрагивают рендеринг HTML)

@app.route('/api/v1/submit', methods=['POST'])
@login_required
def submit_module_api():
    """API-маршрут для приема данных модуля."""
    data = request.get_json()
    uid = auth.verify_id_token(session['token'])['uid']
    
    required_fields = ['name', 'author', 'commands', 'description', 'module_code']
    if not all(field in data for field in required_fields):
        return jsonify({"success": False, "message": "Не все поля заполнены"}), 400

    module_data = {
        "name": data['name'],
        "author": data['author'],
        "commands": data['commands'],
        "description": data['description'],
        "module_code": data['module_code'],
        "developer_uid": uid,
        "status": "pending",
        "created_at": firestore.SERVER_TIMESTAMP,
        "downloads": 0
    }

    try:
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

    # --- ИНТЕГРАЦИЯ GEMINI ---
    prompt = f"""Проанализируй следующий Python-код модуля. 
Найди все команды, помеченные декоратором @loader.command, и их описания (docstring). 
Верни результат в виде простого текста, где каждая команда и ее описание находятся на новой строке, 
например: .cmd1 - Описание команды 1.

КОД:
{code}"""
    
    try:
        # ЗАГЛУШКА: Здесь должен быть вызов реального Gemini API
        # response = requests.post(
        #     "https://api.gemini.ai/v1/generate", 
        #     headers={"Authorization": f"Bearer {GEMINI_API_KEY}"},
        #     json={"prompt": prompt, "model": "gemini-2.5-flash"}
        # )
        # generated_text = response.json().get('text')

        # Заглушка, имитирующая ответ
        generated_text = ".search - Ищет модули в каталоге.\n.fheta - Проверяет версию модуля."
        
        return jsonify({"success": True, "commands": generated_text}), 200
    except Exception as e:
        return jsonify({"success": False, "commands": f"Ошибка анализа API: {e}"}), 500


if __name__ == '__main__':
    app.run(debug=True)
