# db.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    # La inteligencia para elegir la base de datos (SQLite por defecto para portabilidad)
    # Aquí puedes agregar la lógica para MySQL, Pocketbase o IndexedDB según el entorno
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///glassmorphic_app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)