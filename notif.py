# notif.py
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from db import db
from models import Notification

notif_bp = Blueprint('notif', __name__)

def crear_notificacion(mensaje, tipo='info'):
    """Inyecta una notificación silenciosa en la BD. Tipos permitidos: info, success, warning, danger"""
    try:
        nueva_notif = Notification(mensaje=mensaje, tipo=tipo)
        db.session.add(nueva_notif)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[!] Error al crear notificación: {e}")

@notif_bp.route('/notificaciones')
@login_required
def notificaciones():
    if not current_user.is_superuser:
        flash('Acceso denegado. Solo superusuarios pueden ver notificaciones del sistema.', 'danger')
        return redirect(url_for('routes.home'))
        
    # Extraer y ordenar desde la más reciente
    lista_notificaciones = Notification.query.order_by(Notification.fecha.desc()).all()
    
    # Marcar automáticamente como leídas al entrar
    cambios = False
    for n in lista_notificaciones:
        if not n.leida:
            n.leida = True
            cambios = True
            
    if cambios:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[!] Error al marcar notificaciones como leídas: {e}")
            
    return render_template('notificador.html', notificaciones=lista_notificaciones)
    
@notif_bp.route('/limpiar_notificaciones', methods=['POST'])
@login_required
def limpiar_notificaciones():
    if current_user.is_superuser:
        try:
            Notification.query.delete()
            db.session.commit()
            flash('El panel de notificaciones ha sido limpiado.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error al intentar limpiar el panel de notificaciones.', 'danger')
            
    return redirect(url_for('notif.notificaciones'))