# app.py
from flask import Flask
from db import db, init_db
from flask_login import LoginManager
from user import user_bp
from routes import routes_bp
from models import User
from werkzeug.security import generate_password_hash
from flask_migrate import Migrate
from sqlalchemy.exc import OperationalError

app = Flask(__name__)
app.config['SECRET_KEY'] = 'glassmorphic_secret_key_123'

# Inicializar Base de datos
init_db(app)

# Inicializar Flask-Migrate (Para preservar la BD existente)
migrate = Migrate(app, db)

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

# ==================================================
# INYECTOR SEGURO DE SUPERUSUARIOS
# ==================================================
def crear_superusuarios():
    super_emails = ['kenth1977@gmail.com', 'lthikingcr@gmail.com']
    nombres = ['Kenth', 'LT Hiking']
    
    try:
        for i, email in enumerate(super_emails):
            # Revisamos si ya existe en la base de datos
            admin = User.query.filter_by(email=email).first()
            
            if not admin:
                print(f"[*] Inyectando superusuario: {email}")
                nuevo_admin = User(
                    nombre=nombres[i],
                    primer_apellido="Super",
                    segundo_apellido="Admin",
                    email=email,
                    password_hash=generate_password_hash('ligaliga'),
                    rec_pin='123456', # PIN de recuperación por defecto
                    is_superuser=True, # ¡Poder absoluto concedido!
                    datos_adicionales={"Rol": "Superusuario Total"}
                )
                db.session.add(nuevo_admin)
                
        # Guardamos los cambios
        db.session.commit()
    except OperationalError:
        # Esto atrapa el error si la columna 'is_superuser' aún no existe
        db.session.rollback()
        print("\n" + "="*60)
        print("[!] AVISO DE MIGRACIÓN PENDIENTE [!]")
        print("La columna 'is_superuser' aún no existe en la base de datos.")
        print("Tus contactos están a salvo. Por favor, detén el servidor (Ctrl+C)")
        print("y ejecuta los siguientes comandos en la terminal en orden:\n")
        print("  1. Inicializar migraciones (solo si no tienes la carpeta 'migrations'):")
        print("     flask db init\n")
        print("  2. Detectar la nueva columna:")
        print("     flask db migrate -m \"Agregada columna is_superuser para administradores\"\n")
        print("  3. Aplicar los cambios a tu base de datos de forma segura:")
        print("     flask db upgrade")
        print("="*60 + "\n")

if __name__ == '__main__':
    with app.app_context():
        # create_all() ignorará las tablas que ya existen, manteniendo tus 200 usuarios a salvo
        db.create_all() 
        # Intenta inyectar a los administradores
        crear_superusuarios() 
        
    app.run(debug=True, port=5000)