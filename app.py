import os
import json
from flask import Flask, jsonify, request, abort
import requests

app = Flask(__name__)

FIREBASE_URL = os.environ.get('FIREBASE_URL')
FIREBASE_SECRET = os.environ.get('FIREBASE_SECRET')

if not FIREBASE_URL or not FIREBASE_SECRET:
    print("FATAL ERROR: Переменные FIREBASE_URL или FIREBASE_SECRET не установлены.")
    exit(1)

# Формируем базовый URL для доступа к API с секретным ключом
# Добавляем '.json' для корректного REST API запроса
BASE_MODULES_URL = f"{FIREBASE_URL.rstrip('/')}/modules.json?auth={FIREBASE_SECRET}"


def module_to_dict(key, data):
    return {
        'id': key, 
        'name': data.get('name', 'N/A'),
        'description': data.get('description', 'Нет описания'),
        'keywords': data.get('keywords', []),
        'link': data.get('link', 'Нет ссылки')
    }

@app.route('/api/v1/modules', methods=['GET', 'POST'])
def handle_modules():
    if request.method == 'GET':
        
        try:
            response = requests.get(BASE_MODULES_URL)
            response.raise_for_status() 
            modules_data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Firebase GET Error: {e}")
            abort(500, description="Ошибка сервера при получении данных из Firebase.")
        
        modules_list = []
        if modules_data:
            for key, data in modules_data.items():
                modules_list.append(module_to_dict(key, data))
        
        return jsonify({
            "status": "success",
            "count": len(modules_list),
            "modules": modules_list
        })
    
    elif request.method == 'POST':
        if not request.json or 'name' not in request.json or 'link' not in request.json:
            abort(400, description="Необходимо указать 'name' и 'link' в теле запроса.")

        new_module_data = {
            'name': request.json['name'],
            'description': request.json.get('description', 'Описание отсутствует'),
            'keywords': request.json.get('keywords', []), 
            'link': request.json['link']
        }
        
        try:
            post_url = f"{FIREBASE_URL.rstrip('/')}/modules.json?auth={FIREBASE_SECRET}"
            response = requests.post(post_url, json=new_module_data)
            response.raise_for_status()

            result = response.json()
            new_module_id = result.get('name')
            
            return jsonify({
                "status": "created",
                "module": module_to_dict(new_module_id, new_module_data)
            }), 201
            
        except requests.exceptions.RequestException as e:
            print(f"Firebase Post Error: {e}")
            abort(500, description="Ошибка сервера при сохранении данных в Firebase.")


@app.route('/api/v1/modules/search', methods=['GET'])
def search_api():
    query = request.args.get('query', '').strip().lower()
    
    if not query:
        return jsonify({
            "status": "error",
            "message": "Параметр 'query' обязателен для поиска."
        }), 400
    
    try:
        response = requests.get(BASE_MODULES_URL)
        response.raise_for_status()
        modules_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Firebase GET Error: {e}")
        abort(500, description="Ошибка сервера при получении данных.")
        
    results_list = []
    if modules_data:
        for key, data in modules_data.items():
            module_name = data.get('name', '').lower()
            module_desc = data.get('description', '').lower()
            module_keywords = [k.lower() for k in data.get('keywords', [])]

            if query in module_name or query in module_desc or query in ' '.join(module_keywords):
                results_list.append(module_to_dict(key, data))

    return jsonify({
        "status": "success",
        "query": query,
        "count": len(results_list),
        "modules": results_list
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
