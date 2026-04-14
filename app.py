# app.py
import os
import json
import subprocess
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

# FIX SQLITE: render_as_batch=True es OBLIGATORIO para que SQLite pueda alterar tablas existentes
migrate = Migrate(app, db, render_as_batch=True)

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
            admin = User.query.filter_by(email=email).first()
            if not admin:
                print(f"[*] Inyectando superusuario: {email}")
                nuevo_admin = User(
                    nombre=nombres[i],
                    primer_apellido="Super",
                    segundo_apellido="Admin",
                    email=email,
                    password_hash=generate_password_hash('ligaliga'),
                    rec_pin='123456', 
                    is_superuser=True, 
                    rol='Superusuario',
                    datos_adicionales={"Rol": "Superusuario Total"}
                )
                db.session.add(nuevo_admin)
        db.session.commit()
    except OperationalError:
        db.session.rollback()
        print("\n" + "="*60)
        print("[!] AVISO DE MIGRACIÓN PENDIENTE [!]")
        print("Ejecuta: flask db migrate -m 'Migración' y luego flask db upgrade")
        print("="*60 + "\n")

# ==================================================
# INICIADOR AUTOMÁTICO DE TAILSCALE FUNNEL
# ==================================================
def iniciar_tailscale():
    """Lee el archivo JSON de configuración y lanza el Funnel si está activo"""
    if os.path.exists('tailscale_config.json'):
        try:
            with open('tailscale_config.json', 'r') as f:
                config = json.load(f)
                
            if config.get('enable_funnel', False):
                print("\n" + "="*60)
                print("[*] INICIANDO TAILSCALE FUNNEL (Ajustes Globales)...")
                
                # Ejecuta el comando de Tailscale capturando la salida para diagnosticar problemas
                # shell=True es crucial en Windows para que reconozca comandos del sistema
                result = subprocess.run(["tailscale", "funnel", "--bg", "5000"], capture_output=True, text=True, shell=True)
                
                # Construye la URL exacta con los datos guardados manualmente
                device = config.get('tailscale_device_name', 'desktop-7dh07va')
                domain = config.get('tailnet_domain', 'taileb5c96.ts.net')
                url = f"https://{device}.{domain}"
                
                # Si el comando fue exitoso (código 0)
                if result.returncode == 0:
                    print("[+] ¡ÉXITO! Tailscale Funnel configurado en el puerto 5000.")
                    print(f"[+] ENLACE PÚBLICO ACTIVO: {url}")
                    if result.stdout:
                        print(f"[+] Respuesta Tailscale: {result.stdout.strip()}")
                else:
                    # Si Tailscale bloquea el túnel, te mostrará la razón exacta aquí
                    print("[-] ATENCIÓN: Tailscale rechazó la apertura del túnel.")
                    print(f"[-] Razón del error: {result.stderr.strip() or result.stdout.strip()}")
                    print("[!] Verifica los 'Access Controls' y 'HTTPS Certificates' en la web de Tailscale.")
                
                print("="*60 + "\n")
        except Exception as e:
            print(f"[!] Error al leer configuración o iniciar Tailscale: {e}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
        crear_superusuarios() 
        
    # Ejecuta el script de Tailscale justo antes de levantar el servidor Flask
    iniciar_tailscale()
        
    app.run(debug=True, port=5000)