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
    
    # Almacenamiento JSON para Teléfonos, Cédulas, Grupos, etc.
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
    
    # Configuración Tailscale
    tailscale_device_name = db.Column(db.String(100), default='')
    tailnet_domain = db.Column(db.String(100), default='taileb5c96.ts.net')
    magic_dns = db.Column(db.String(50), default='100.100.100.100')
    global_nameserver = db.Column(db.String(50), default='Local DNS settings')
    enable_funnel = db.Column(db.Boolean, default=False)

# ==========================================
# TABLA: ALERTAS DEL SISTEMA (LOGS)
# ==========================================
class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    mensaje = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(50), default='info') # info, success, warning, danger
    fecha = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    leida = db.Column(db.Boolean, default=False)

# ==========================================
# TABLA: COMUNICADOS (POPUPS OBLIGATORIOS)
# ==========================================
class Announcement(db.Model):
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    
    # Segmentación: 'all', 'individual' (emails), 'grupo' (Nombre_Grupo)
    target_type = db.Column(db.String(50), default='all')
    target_value = db.Column(db.Text, nullable=True) 
    
    scheduled_for = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relación para saber quién lo ha leído (Cascade delete si se borra el anuncio)
    receipts = db.relationship('AnnouncementReceipt', backref='announcement', lazy=True, cascade="all, delete-orphan")

# ==========================================
# TABLA: ACUSES DE RECIBO (HISTORIAL)
# ==========================================
class AnnouncementReceipt(db.Model):
    __tablename__ = 'announcement_receipts'
    
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements.id', ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    
    leido_en = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    no_mostrar = db.Column(db.Boolean, default=False) # True si el usuario dio clic en "Entendido"
    
    user = db.relationship('User', backref='announcement_receipts', lazy=True)