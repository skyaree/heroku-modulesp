import os
import json
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)
ADMIN_SECRET_KEY = os.environ.get("MODUARCH_SECRET_KEY")

try:
    firebase_config_json = os.environ.get("FIREBASE_SECRET")
    
    if not firebase_config_json:
        raise ValueError("FIREBASE_SECRET environment variable not found.")

    cred_dict = json.loads(firebase_config_json)
    cred = credentials.Certificate(cred_dict)

    database_url = os.environ.get("FIREBASE_DB_URL", "https://heroku-7f15d-default-rtdb.firebaseio.com") 
    
    firebase_admin.initialize_app(cred, {
        'databaseURL': database_url
    })
    
    root_ref = db.reference('/') 

except Exception as e:
    print(f"FATAL ERROR: Failed to initialize Firebase: {e}")
    root_ref = None 

def is_super_admin(req):
    return req.headers.get('X-Super-Admin-Key') == ADMIN_SECRET_KEY

def get_moderators():
    if root_ref:
        moderators = root_ref.child('moduarch_roles/moderators').get()
        return moderators if moderators else []
    return []

@app.route('/', methods=['GET'])
def index():
    return "Moduarch API is running.", 200

@app.route('/api/v1/admin/moderators', methods=['POST'])
def add_moderator():
    if not is_super_admin(request):
        return jsonify({"message": "Access denied"}), 403

    if not root_ref:
        return jsonify({"message": "Firebase not initialized"}), 500

    try:
        data = request.get_json()
        telegram_id = str(data.get('telegram_id'))
        
        if not telegram_id.isdigit():
            return jsonify({"message": "Invalid Telegram ID"}), 400

        current_mods = get_moderators()
        if telegram_id not in current_mods:
            current_mods.append(telegram_id)
            root_ref.child('moduarch_roles/moderators').set(current_mods)
            return jsonify({"message": f"Moderator {telegram_id} added successfully"}), 200
        else:
            return jsonify({"message": f"Moderator {telegram_id} already exists"}), 200

    except Exception as e:
        return jsonify({"message": f"Internal API error: {e}"}), 500

@app.route('/api/v1/admin/moderators', methods=['GET'])
def list_moderators():
    if not is_super_admin(request):
        return jsonify({"message": "Access denied"}), 403
    
    moderators = get_moderators()
    return jsonify({"moderators": moderators}), 200

@app.route('/api/v1/modules/publish', methods=['POST'])
def publish_module():
    if not root_ref:
        return jsonify({"message": "Firebase not initialized"}), 500

    try:
        module_data = request.get_json()
        module_name = module_data.get('name')
        
        if not module_name:
            return jsonify({"message": "Module name is required"}), 400

        module_key = module_name.lower().replace(' ', '_')
        
        root_ref.child(f'moduarch_modules/{module_key}').set(module_data)
        
        return jsonify({"message": f"Module '{module_name}' published successfully"}), 201

    except Exception as e:
        return jsonify({"message": f"Internal API error during publish: {e}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
