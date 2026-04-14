# app.py
import os
import subprocess
from flask import Flask
from db import db, init_db
from flask_login import LoginManager
from user import user_bp
from routes import routes_bp
from notif import notif_bp  # IMPORTAMOS EL NUEVO BLUEPRINT
from models import User, AppConfig, Notification  # IMPORTAMOS EL MODELO NOTIFICATION
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
app.register_blueprint(notif_bp)  # REGISTRAMOS LAS RUTAS DE NOTIFICACIONES

# ==================================================
# INYECTOR DE VARIABLES GLOBALES (DESDE BASE DE DATOS)
# ==================================================
@app.context_processor
def inject_global_settings():
    from flask_login import current_user
    unread_notifs = 0
    try:
        # Calcular notificaciones no leídas solo si el usuario es Superadmin
        if current_user.is_authenticated and current_user.is_superuser:
            unread_notifs = Notification.query.filter_by(leida=False).count()
            
        config = AppConfig.query.first()
        if config:
            return {
                'global_site_name': config.site_name,
                'global_support_email': config.support_email,
                'global_theme': config.global_theme,
                'unread_notifs': unread_notifs
            }
    except Exception:
        # Pasa en silencio si la tabla aún no se ha creado
        pass
        
    # Valores por defecto de emergencia
    return {
        'global_site_name': 'GlassApp Portable',
        'global_support_email': 'soporte@midominio.com',
        'global_theme': '',
        'unread_notifs': unread_notifs
    }

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
# INICIADOR AUTOMÁTICO DE TAILSCALE FUNNEL (DESDE BD)
# ==================================================
def iniciar_tailscale(app_instance):
    """Lee la Base de Datos SQLite y lanza el Funnel si está activo"""
    with app_instance.app_context():
        from notif import crear_notificacion # Importado dentro del contexto para evitar errores circulares
        try:
            config = AppConfig.query.first()
            if config and config.enable_funnel:
                print("\n" + "="*60)
                print("[*] INICIANDO TAILSCALE FUNNEL DESDE LA BASE DE DATOS...")
                
                # Ejecuta el comando de Tailscale capturando la salida
                result = subprocess.run(["tailscale", "funnel", "--bg", "5000"], capture_output=True, text=True, shell=True)
                
                # Construye la URL exacta con los datos guardados
                device = config.tailscale_device_name or 'desktop-7dh07va'
                domain = config.tailnet_domain or 'taileb5c96.ts.net'
                url = f"https://{device}.{domain}"
                
                # Si el comando fue exitoso
                if result.returncode == 0:
                    print("[+] ¡ÉXITO! Tailscale Funnel configurado en el puerto 5000.")
                    print(f"[+] ENLACE PÚBLICO ACTIVO: {url}")
                    crear_notificacion(f"Tailscale Funnel CONECTADO: {url}", "success")
                    if result.stdout:
                        print(f"[+] Respuesta Tailscale: {result.stdout.strip()}")
                else:
                    print("[-] ATENCIÓN: Tailscale rechazó la apertura del túnel.")
                    print(f"[-] Razón del error: {result.stderr.strip() or result.stdout.strip()}")
                    crear_notificacion("Tailscale Funnel falló al conectar o se DESCONECTÓ.", "danger")
                
                print("="*60 + "\n")
        except Exception as e:
            print(f"[!] Error al intentar leer la base de datos o iniciar Tailscale: {e}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
        crear_superusuarios() 
        
    # Ejecuta el script de Tailscale pasándole el contexto de la aplicación para que pueda leer la BD
    iniciar_tailscale(app)
        
    app.run(debug=True, port=5000)