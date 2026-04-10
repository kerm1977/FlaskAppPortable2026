# models.py
from db import db
from flask_login import UserMixin
import datetime
import pytz

def get_cr_time():
    cr_tz = pytz.timezone('America/Costa_Rica')
    return datetime.datetime.now(cr_tz)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    imagen_flyer = db.Column(db.String(255), nullable=True) # Ruta de la imagen
    nombre = db.Column(db.String(100), nullable=False)
    primer_apellido = db.Column(db.String(100), nullable=False)
    segundo_apellido = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rec_pin = db.Column(db.String(6), nullable=False) # Pin de seguridad de 6 dígitos
    
    # SOLUCIÓN SQLITE: Al quitar nullable=False, SQLite permitirá añadir la columna a los 200 usuarios sin fallar
    is_superuser = db.Column(db.Boolean, default=False)
    
    # NUEVO: Rol oficial del usuario para el panel de administración
    rol = db.Column(db.String(50), default='Usuario', server_default='Usuario')
    
    # Campos dinámicos guardados como JSON para mayor flexibilidad
    datos_adicionales = db.Column(db.JSON, default={})
    
    fecha_registro = db.Column(db.DateTime, default=get_cr_time)