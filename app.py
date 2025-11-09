import os
import json
import requests
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from dotenv import load_dotenv
# Импорт time для отметок времени
from datetime import datetime
import time 

# --- Firebase Setup ---
import firebase_admin
from firebase_admin import credentials, firestore, auth

# ... (Код инициализации Firebase остается без изменений) ...

# ... (Код инициализации Flask остается без изменений) ...


# --- PLACEHOLDERS ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")

# !!! УДАЛЯЕМ ВСЕ СТАРЫЕ ЗАГЛУШКИ: MODULES_DATA, CREATORS_DATA !!!


# --- FIREBASE DATA LOGIC (Новые функции для работы с БД) ---

def get_average_rating(module_id):
    """Считает средний рейтинг модуля из коллекции Ratings."""
    if not db: return 0.0 
    try:
        ratings_ref = db.collection('Ratings').where('module_id', '==', str(module_id)).stream()
        total_score = 0
        count = 0
        for rating in ratings_ref:
            data = rating.to_dict()
            total_score += data.get('score', 0)
            count += 1
        
        return round(total_score / count, 2) if count > 0 else 0.0
    except Exception:
        return 0.0

def get_module_data_with_rating(module_doc):
    """Преобразует документ модуля в словарь с добавлением рейтинга."""
    module = module_doc.to_dict()
    module['id'] = module_doc.id # Важно получить ID документа для маршрута
    module['rating'] = get_average_rating(module_doc.id)
    # Форматируем команды для отображения в шаблоне
    if 'commands' in module and isinstance(module['commands'], str):
        module['commands'] = [c.strip() for c in module['commands'].split('\n') if c.strip()]
    return module

def get_creator_data(uid):
    """Получает данные пользователя, включая количество модулей и рейтинг."""
    user_data = get_user_data(uid)
    if not user_data: 
        return {'uid': uid, 'username': 'Unknown Author', 'modules_count': 0, 'reviews_rating': 0.0}
    
    # Считаем количество модулей
    module_count = db.collection('Modules').where('developer_uid', '==', uid).stream()
    user_data['modules_count'] = len(list(module_count))
    
    # TODO: Более сложная логика среднего рейтинга автора
    user_data['reviews_rating'] = user_data.get('high_rating', 4.7) 
    user_data['username'] = user_data.get('telegram_username', 'User')
    
    return user_data

# --- Decorators and Auth Logic (Остаются без изменений, но используем новую get_user_data) ---

# ... (Код get_user_data, get_auth_status, login_required, admin_required остается без изменений) ...


# --- CORE WEBSITE ROUTES (HTML) ---

@app.route('/')
def home():
    """Главная страница."""
    logged_in, is_admin, _ = get_auth_status()
    # Просто редирект на список модулей или на пустую домашнюю страницу (по твоему прототипу 1000036982.png)
    # Если ты хочешь отдельную домашнюю страницу (1000036982.png), используй:
    return render_template('home.html', 
                           title="Heroku Modules", 
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/modules')
def modules_list():
    """Список всех модулей (Прототип 1000036983.png)."""
    logged_in, is_admin, _ = get_auth_status()
    modules = []
    total_modules = 0
    
    if db:
        try:
            # Получаем только одобренные модули
            modules_ref = db.collection('Modules').where('status', '==', 'approved').stream()
            for doc in modules_ref:
                modules.append(get_module_data_with_rating(doc))
            total_modules = len(modules)
        except Exception:
            pass
            
    return render_template('index.html', 
                           title="Каталог Модулей", 
                           modules=modules,
                           total_modules=total_modules,
                           logged_in=logged_in, 
                           is_admin=is_admin)

@app.route('/module/<module_id>')
def module_detail(module_id):
    """Страница деталей модуля (Прототип 1000036984.png)."""
    logged_in, is_admin, _ = get_auth_status()
    module = None
    
    if db:
        try:
            # Получаем документ по ID
            module_doc = db.collection('Modules').document(module_id).get()
            if module_doc.exists:
                module = get_module_data_with_rating(module_doc)
        except Exception:
            pass
            
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
    creators = []
    total_creators = 0
    
    if db:
        try:
            # Получаем всех пользователей, которые имеют роль 'creator' или 'admin'
            # Для простоты, пока получим всех пользователей и отфильтруем по наличию модулей
            users_ref = db.collection('Users').stream()
            for doc in users_ref:
                creator_data = get_creator_data(doc.id)
                if creator_data and creator_data.get('modules_count', 0) > 0:
                    creators.append(creator_data)
            total_creators = len(creators)
        except Exception:
            pass
            
    return render_template('creators.html', 
                           title="Список Создателей", 
                           creators=creators,
                           total_creators=total_creators,
                           logged_in=logged_in, 
                           is_admin=is_admin)

# ... (Остальные маршруты: submit_module_form, moderation_panel, account_page, login_route, logout_route остаются без изменений) ...


# --- CORE API ROUTES (JSON) ---

# ... (Маршрут auth_api остается без изменений, он создает/обновляет пользователя в коллекции 'Users') ...

@app.route('/api/v1/submit', methods=['POST'])
@login_required
def submit_module_api():
    """API-маршрут для приема данных модуля (Прототип 1000036987.png)."""
    data = request.get_json()
    uid = auth.verify_id_token(session['token'])['uid']
    
    required_fields = ['name', 'author', 'commands', 'description', 'module_code', 'banner_url']
    if not all(field in data for field in required_fields):
        return jsonify({"success": False, "message": "Не все поля заполнены"}), 400

    module_data = {
        "name": data['name'],
        "author": data['author'],
        "commands": data['commands'],
        "description": data['description'],
        "module_code": data['module_code'],
        "banner_url": data['banner_url'], # Новое поле
        "developer_uid": uid,
        "status": "pending", # Всегда отправляем на модерацию
        "created_at": time.time(), # Используем временную метку UNIX 
        "downloads": 0
    }

    try:
        db.collection('Modules').add(module_data)
        return jsonify({"success": True, "message": "Модуль отправлен на модерацию"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка БД: {e}"}), 500

# ... (Маршрут analyze_module_code остается без изменений) ...

# --- НОВЫЙ МАРШРУТ: API для выставления рейтинга ---
@app.route('/api/v1/rate_module/<module_id>', methods=['POST'])
@login_required
def rate_module_api(module_id):
    """Прием рейтинга от пользователя и сохранение в Firestore."""
    data = request.get_json()
    score = data.get('score')
    uid = auth.verify_id_token(session['token'])['uid']

    if score is None or not 1 <= score <= 5:
        return jsonify({"success": False, "message": "Неверный формат рейтинга (1-5)."}), 400

    rating_data = {
        "module_id": str(module_id),
        "user_uid": uid,
        "score": int(score),
        "created_at": time.time()
    }
    
    try:
        # Ищем, оставлял ли пользователь уже рейтинг для этого модуля
        query = db.collection('Ratings').where('module_id', '==', str(module_id)).where('user_uid', '==', uid)
        existing_ratings = query.stream()
        
        updated = False
        for doc in existing_ratings:
            # Если рейтинг уже есть, обновляем его
            db.collection('Ratings').document(doc.id).update({'score': int(score), 'created_at': time.time()})
            updated = True
            break
            
        if not updated:
            # Если нет, создаем новый
            db.collection('Ratings').add(rating_data)
            
        # Возвращаем новый средний рейтинг для обновления на клиенте
        new_avg_rating = get_average_rating(module_id)
        
        return jsonify({"success": True, "message": "Рейтинг сохранен.", "new_rating": new_avg_rating}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка сохранения рейтинга: {e}"}), 500


if __name__ == '__main__':
    app.run(debug=True)
