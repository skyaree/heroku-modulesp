import os
import json
from flask import Flask, jsonify, request, abort

app = Flask(__name__)

MODULES_STORE = [] 
MODULES_STORE.extend([
    {
        "id": 1,
        "name": "heroku-buildpack-python",
        "description": "Официальный Buildpack для развёртывания приложений на Python.",
        "keywords": ["python", "official"],
        "link": "https://github.com/heroku/heroku-buildpack-python"
    },
    {
        "id": 2,
        "name": "heroku-buildpack-nginx",
        "description": "Добавляет NGINX для обслуживания статических файлов.",
        "keywords": ["nginx", "static", "proxy"],
        "link": "https://github.com/heroku/heroku-buildpack-nginx"
    }
])
next_id = 3

@app.route('/api/v1/modules', methods=['GET', 'POST'])
def handle_modules():
    global next_id
    
    if request.method == 'GET':
        return jsonify({
            "status": "success",
            "count": len(MODULES_STORE),
            "modules": MODULES_STORE
        })
    
    elif request.method == 'POST':
        if not request.json or 'name' not in request.json or 'link' not in request.json:
            abort(400, description="Необходимо указать 'name' и 'link' в теле запроса.")

        new_module = {
            'id': next_id,
            'name': request.json['name'],
            'description': request.json.get('description', 'Описание отсутствует'),
            'keywords': request.json.get('keywords', []),
            'link': request.json['link']
        }
        
        MODULES_STORE.append(new_module)
        next_id += 1
        
        return jsonify({
            "status": "created",
            "module": new_module
        }), 201

@app.route('/api/v1/modules/search', methods=['GET'])
def search_api():
    query = request.args.get('query', '').strip().lower()
    
    if not query:
        return jsonify({
            "status": "error",
            "message": "Параметр 'query' обязателен для поиска."
        }), 400
    
    results = []
    for module in MODULES_STORE:
        if (query in module.get('name', '').lower() or
            query in module.get('description', '').lower() or
            any(query in k.lower() for k in module.get('keywords', []))):
            results.append(module)
            
    return jsonify({
        "status": "success",
        "query": query,
        "count": len(results),
        "modules": results
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
