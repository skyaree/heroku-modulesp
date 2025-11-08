import os
import json
from flask import Flask, jsonify, request, abort
from sqlalchemy import create_engine, Column, Integer, String, Text, ARRAY, cast
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

app = Flask(__name__)

DB_URL = os.environ.get('DATABASE_URL')

if DB_URL and DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

if not DB_URL:
    engine = create_engine('sqlite:///modules.db')
else:
    engine = create_engine(DB_URL)

Base = declarative_base()

class Module(Base):
    __tablename__ = 'modules'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, default='Описание отсутствует')
    keywords = Column(ARRAY(String), default=[]) 
    link = Column(String(512), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'keywords': self.keywords if self.keywords is not None else [], 
            'link': self.link
        }

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

@app.route('/api/v1/modules', methods=['GET', 'POST'])
def handle_modules():
    session = Session()
    try:
        if request.method == 'GET':
            all_modules = session.query(Module).all()
            
            return jsonify({
                "status": "success",
                "count": len(all_modules),
                "modules": [m.to_dict() for m in all_modules]
            })
        
        elif request.method == 'POST':
            if not request.json or 'name' not in request.json or 'link' not in request.json:
                abort(400, description="Необходимо указать 'name' и 'link' в теле запроса.")

            new_module = Module(
                name=request.json['name'],
                description=request.json.get('description', 'Описание отсутствует'),
                keywords=request.json.get('keywords', []), 
                link=request.json['link']
            )
            
            session.add(new_module)
            session.commit()
            
            return jsonify({
                "status": "created",
                "module": new_module.to_dict()
            }), 201
            
    except Exception as e:
        session.rollback()
        print(f"Database error: {e}")
        abort(500, description="Ошибка сервера при работе с базой данных.")
    finally:
        session.close()


@app.route('/api/v1/modules/search', methods=['GET'])
def search_api():
    session = Session()
    try:
        query = request.args.get('query', '').strip().lower()
        
        if not query:
            return jsonify({
                "status": "error",
                "message": "Параметр 'query' обязателен для поиска."
            }), 400
        
        search_term = f"%{query}%"
        
        results = session.query(Module).filter(
            (Module.name.ilike(search_term)) |
            (Module.description.ilike(search_term)) |
            (cast(Module.keywords, Text).ilike(search_term))
        ).all()
        
        return jsonify({
            "status": "success",
            "query": query,
            "count": len(results),
            "modules": [m.to_dict() for m in results]
        })
    finally:
        session.close()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    if not DB_URL:
        Base.metadata.create_all(engine)
        
    app.run(host='0.0.0.0', port=port)
