# models.py
from db import db
from flask_login import UserMixin
import datetime

# ==========================================
# TABLA: USUARIOS REGISTRADOS
# ==========================================
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    imagen_flyer = db.Column(db.Text, nullable=True)
    nombre = db.Column(db.String(100), nullable=False)
    primer_apellido = db.Column(db.String(100), nullable=False)
    segundo_apellido = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rec_pin = db.Column(db.String(6), nullable=False)
    
    rol = db.Column(db.String(50), default='Usuario Regular')
    is_superuser = db.Column(db.Boolean, default=False)
    
    # Campos dinámicos guardados como JSON para mayor flexibilidad
    datos_adicionales = db.Column(db.JSON, default={})
    
    fecha_registro = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# ==========================================
# TABLA: CONFIGURACIÓN GLOBAL DEL SISTEMA
# ==========================================
class AppConfig(db.Model):
    __tablename__ = 'app_config'
    
    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(100), default='GlassApp Portable')
    support_email = db.Column(db.String(120), default='soporte@midominio.com')
    global_theme = db.Column(db.String(255), default='')
    
    # Configuraciones de Tailscale
    tailscale_device_name = db.Column(db.String(100), default='')
    tailnet_domain = db.Column(db.String(100), default='taileb5c96.ts.net')
    magic_dns = db.Column(db.String(50), default='100.100.100.100')
    global_nameserver = db.Column(db.String(50), default='Local DNS settings')
    enable_funnel = db.Column(db.Boolean, default=False)

# ==========================================
# TABLA: NOTIFICACIONES DEL SISTEMA
# ==========================================
class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    mensaje = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(50), default='info') # success, warning, danger, info
    fecha = db.Column(db.DateTime, default=db.func.current_timestamp())
    leida = db.Column(db.Boolean, default=False)