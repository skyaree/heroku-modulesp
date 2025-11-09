import os
import json
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from dotenv import load_dotenv

# --- Firebase Setup ---
import firebase_admin
from firebase_admin import credentials, firestore, auth

# Загрузка переменных окружения (для локальной работы)
load_dotenv() 

# Используйте JSON-файл или переменные окружения для credentials
# Рекомендуется использовать переменные окружения на Render
try:
    # Заглушка: На Render используйте переменную окружения с содержимым service account JSON
    # Например, FIREBASE_CREDENTIALS_JSON
    FIREBASE_CREDENTIALS_JSON = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if FIREBASE_CREDENTIALS_JSON:
        cred = credentials.Certificate(json.loads(FIREBASE_CREDENTIALS_JSON))
    else:
        # Для локального теста, используйте файл (не рекомендуется на продакшене)
        cred = credentials.Certificate("path/to/your/serviceAccountKey.json")

    firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"Ошибка инициализации Firebase: {e}")
    db = None # Установим None, чтобы приложение могло запуститься без БД

app = Flask(__name__)
# Установите безопасный секретный ключ (например, сгенерируйте 32-значную строку)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "A_SUPER_SECRET_KEY_FALLBACK_2025")

# --- PLACEHOLDERS ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")

# --- Decorators and Auth Logic ---
def get_user_data(uid):
    """Получает данные пользователя из Firestore, включая роль и ник."""
    if not db: return None 
    try:
        user_doc = db.collection('Users').document(uid).get()
        return user_doc.to_dict() if user_doc.exists else None
    except Exception:
        return None

def login_required(f):
    """Декоратор для проверки аутентификации."""
    def decorated_function(*args, **kwargs):
        if 'token' not in session:
            # Перенаправление на страницу входа, если нет токена
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
    @login_required
    def decorated_function(*args, **kwargs):
        uid = auth.verify_id_token(session['token'])['uid']
        user_data = get_user_data(uid)
        if user_data and user_data.get('role') == 'admin':
            return f(*args, **kwargs)
        return "Доступ запрещен", 403
    return decorated_function


# --- CORE WEBSITE ROUTES (HTML) ---

@app.route('/')
@app.route('/modules')
def modules_list():
    """Список всех модулей."""
    # TODO: Получение и отображение одобренных модулей из Firestore
    return render_template('index.html', title="Каталог Модулей")

@app.route('/submit', methods=['GET'])
@login_required
def submit_module_form():
    """Форма для подачи модуля."""
    # Получаем ник для предзаполнения
    uid = auth.verify_id_token(session['token'])['uid']
    user_data = get_user_data(uid)
    telegram_username = user_data.get('telegram_username', '') if user_data else ''
    
    return render_template('submit.html', 
                           title="Подать Модуль", 
                           telegram_username=telegram_username)

@app.route('/panel/moderatemod')
@admin_required
def moderation_panel():
    """Панель модерации."""
    # TODO: Получение модулей со статусом 'pending'
    return render_template('admin.html', title="Панель Модерации")

@app.route('/account')
@login_required
def account_page():
    """Страница аккаунта."""
    # TODO: Отображение данных пользователя (ник, дата регистрации)
    uid = auth.verify_id_token(session['token'])['uid']
    user_data = get_user_data(uid)
    return render_template('account.html', title="Мой Аккаунт", user=user_data)

@app.route('/login')
def login_route():
    """Страница входа."""
    # Здесь должна быть кнопка "Войти через Google"
    return render_template('login.html', title="Вход")

# --- CORE API ROUTES (JSON) ---

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
    # В реальном коде здесь должен быть вызов Gemini API.
    # Пример вызова с инструкцией:
    prompt = (
        "Проанализируй следующий Python-код модуля. 
        Найди все команды, помеченные декоратором @loader.command, и их описания (docstring). 
        Верни результат в виде простого текста, где каждая команда и ее описание находятся на новой строке, 
        например: .cmd1 - Описание команды 1."
        f"\n\nКОД:\n{code}"
    )
    
    try:
        # PLACEHOLDER: Вызов реального Gemini API
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

# Чтобы запустить на Render, используйте Gunicorn или Waitress, и Render автоматически обнаружит `app.py`.
# Например, `gunicorn app:app`
