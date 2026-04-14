# app.py
import os
import subprocess
from datetime import datetime
from flask import Flask
from db import db, init_db
from flask_login import LoginManager
from user import user_bp
from routes import routes_bp
from notif import notif_bp  # IMPORTAMOS EL NUEVO BLUEPRINT
# IMPORTAMOS LOS NUEVOS MODELOS DE COMUNICADOS
from models import User, AppConfig, Notification, Announcement, AnnouncementReceipt  
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
# INYECTOR DE VARIABLES GLOBALES Y POPUPS
# ==================================================
@app.context_processor
def inject_global_settings():
    from flask_login import current_user
    unread_notifs = 0
    active_popup = None
    
    try:
        if current_user.is_authenticated:
            now = datetime.utcnow()
            
            # 1. Extraer el grupo del usuario de forma ultra-segura para comparaciones
            user_group = ''
            if getattr(current_user, 'datos_adicionales', None):
                if isinstance(current_user.datos_adicionales, dict):
                    user_group = current_user.datos_adicionales.get('Nombre_Grupo', '')
                elif isinstance(current_user.datos_adicionales, str):
                    import json
                    try: 
                        user_group = json.loads(current_user.datos_adicionales).get('Nombre_Grupo', '')
                    except: 
                        pass
            
            user_email_clean = str(current_user.email).strip().lower()
            
            # 2. Obtener TODOS los comunicados vigentes (cuyas fechas ya pasaron)
            query = Announcement.query.filter(Announcement.scheduled_for <= now)
            all_past_announcements = query.order_by(Announcement.scheduled_for.desc()).all()
            
            # 3. Filtrar los comunicados que corresponden a este usuario (Individual, Grupo o Todos)
            my_announcements = []
            for ann in all_past_announcements:
                target_val = str(ann.target_value or '').strip().lower()
                
                if ann.target_type == 'all':
                    my_announcements.append(ann)
                elif ann.target_type == 'individual':
                    # Soporte multi-correo: dividimos por coma y limpiamos cada uno
                    target_emails = [e.strip().lower() for e in target_val.split(',')]
                    if user_email_clean in target_emails:
                        my_announcements.append(ann)
                elif ann.target_type == 'grupo' and str(user_group).strip().lower() == target_val:
                    my_announcements.append(ann)
            
            # 4. Buscar IDs de comunicados que el usuario ya marcó como "No Mostrar" (Descartados)
            dismissed_receipts = AnnouncementReceipt.query.filter_by(user_id=current_user.id, no_mostrar=True).all()
            dismissed_ids = [r.announcement_id for r in dismissed_receipts]
            
            # 5. Seleccionar el Pop-Up activo (el más reciente de "mi lista" que no haya sido descartado)
            for ann in my_announcements:
                if ann.id not in dismissed_ids:
                    active_popup = ann
                    break  # Solo mostramos un Pop-up obligatorio a la vez
            
            # 6. Calcular los "No Leídos" para la Campanita de ESTE usuario (comunicados pendientes)
            unread_notifs = len([a for a in my_announcements if a.id not in dismissed_ids])
            
            # 7. Si además es Superadmin, sumarle las alertas de sistema (Logs) a la campanita
            if current_user.is_superuser:
                unread_notifs += Notification.query.filter_by(leida=False).count()
                
        # 8. Traer ajustes estéticos y de configuración
        config = AppConfig.query.first()
        if config:
            return {
                'global_site_name': config.site_name,
                'global_support_email': config.support_email,
                'global_theme': config.global_theme,
                'unread_notifs': unread_notifs,
                'active_popup': active_popup
            }
    except Exception as e:
        # Pasa en silencio si la tabla aún no se ha creado o hay errores de BD
        print(f"Error Context Processor: {e}")
        pass
        
    # Valores por defecto de emergencia
    return {
        'global_site_name': 'GlassApp Portable',
        'global_support_email': 'soporte@midominio.com',
        'global_theme': '',
        'unread_notifs': unread_notifs,
        'active_popup': active_popup
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