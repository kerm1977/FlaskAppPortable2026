# app.py
from flask import Flask
from db import db, init_db
from flask_login import LoginManager
from user import user_bp
from routes import routes_bp
from models import User

app = Flask(__name__)
app.config['SECRET_KEY'] = 'glassmorphic_secret_key_123'

# Inicializar Base de datos
init_db(app)

# Configurar Login Manager
login_manager = LoginManager()
login_manager.login_view = 'user.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Registrar Blueprints
app.register_blueprint(user_bp)
app.register_blueprint(routes_bp)

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Crear la base de datos automáticamente si no existe
    app.run(debug=True, port=5000)