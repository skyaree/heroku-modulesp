import os
import json
from flask import Flask, render_template, request

app = Flask(__name__)


try:
    with open('modules.json', 'r', encoding='utf-8') as f:
        MODULES = json.load(f)
except FileNotFoundError:
    MODULES = []
    print("Ошибка: файл modules.json не найден.")


def search_modules(query):
    """Фильтрует модули по совпадению в названии, описании или ключевых словах."""
    if not query:
        return MODULES  

    query_lower = query.lower()
    results = []
    for module in MODULES:
        if (query_lower in module['name'].lower() or
            query_lower in module['description'].lower() or
            any(query_lower in k.lower() for k in module['keywords'])):
            results.append(module)
    return results


@app.route('/', methods=['GET', 'POST'])
def index():
    query = ""
    results = []
    
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        results = search_modules(query)
    else:
        results = MODULES
     
    return render_template('index.html', modules=results, query=query)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
