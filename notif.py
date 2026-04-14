# notif.py
from flask import Blueprint, render_template, flash, redirect, url_for, request, send_file
from flask_login import login_required, current_user
from db import db
from models import Notification
from datetime import datetime
import json
import io

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
        
    # Obtener el número de página de los parámetros de la URL (por defecto 1)
    page = request.args.get('page', 1, type=int)
    
    # Extraer y ordenar aplicando Paginación (15 elementos por página)
    paginated_notifs = Notification.query.order_by(Notification.fecha.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    
    # Marcar automáticamente como leídas las notificaciones de la página actual
    cambios = False
    for n in paginated_notifs.items:
        if not n.leida:
            n.leida = True
            cambios = True
            
    if cambios:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[!] Error al marcar notificaciones como leídas: {e}")
            
    return render_template('notificador.html', notificaciones=paginated_notifs)

@notif_bp.route('/eliminar_notificacion/<int:id>', methods=['GET'])
@login_required
def eliminar_notificacion(id):
    """Elimina una notificación específica por ID"""
    if not current_user.is_superuser:
        return redirect(url_for('routes.home'))
        
    notif = Notification.query.get_or_404(id)
    try:
        db.session.delete(notif)
        db.session.commit()
        flash('Notificación eliminada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar la notificación.', 'danger')
        
    # Redirigir a la misma página donde estaba (si se puede extraer del referer)
    return redirect(request.referrer or url_for('notif.notificaciones'))

@notif_bp.route('/limpiar_notificaciones', methods=['POST'])
@login_required
def limpiar_notificaciones():
    """Borra todo el historial de la tabla notifications"""
    if current_user.is_superuser:
        try:
            Notification.query.delete()
            db.session.commit()
            flash('El panel de notificaciones ha sido limpiado.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error al intentar limpiar el panel de notificaciones.', 'danger')
            
    return redirect(url_for('notif.notificaciones'))

@notif_bp.route('/exportar_notificaciones', methods=['GET'])
@login_required
def exportar_notificaciones():
    """Genera un archivo JSON descargable con todas las notificaciones"""
    if not current_user.is_superuser:
        return redirect(url_for('routes.home'))
        
    todas = Notification.query.order_by(Notification.fecha.desc()).all()
    data_export = []
    
    for n in todas:
        data_export.append({
            "mensaje": n.mensaje,
            "tipo": n.tipo,
            "fecha": n.fecha.strftime('%Y-%m-%d %H:%M:%S'),
            "leida": n.leida
        })
        
    mem = io.BytesIO()
    mem.write(json.dumps(data_export, indent=4).encode('utf-8'))
    mem.seek(0)
    
    filename = f"notificaciones_respaldo_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    
    return send_file(
        mem, 
        as_attachment=True, 
        download_name=filename, 
        mimetype='application/json'
    )

@notif_bp.route('/importar_notificaciones', methods=['POST'])
@login_required
def importar_notificaciones():
    """Lee un archivo JSON y carga las notificaciones a la base de datos"""
    if not current_user.is_superuser:
        return redirect(url_for('routes.home'))
        
    if 'json_file' not in request.files:
        flash('No se seleccionó ningún archivo.', 'danger')
        return redirect(url_for('notif.notificaciones'))
        
    file = request.files['json_file']
    if file.filename == '':
        flash('El archivo seleccionado está vacío.', 'danger')
        return redirect(url_for('notif.notificaciones'))
        
    try:
        content = file.read().decode('utf-8')
        data = json.loads(content)
        
        count = 0
        for item in data:
            if 'mensaje' in item:
                # Intentar parsear la fecha o usar la actual si falla
                fecha_str = item.get('fecha')
                try:
                    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S')
                except:
                    fecha_obj = datetime.utcnow()
                    
                nueva = Notification(
                    mensaje=item.get('mensaje'),
                    tipo=item.get('tipo', 'info'),
                    fecha=fecha_obj,
                    leida=item.get('leida', True)
                )
                db.session.add(nueva)
                count += 1
                
        db.session.commit()
        flash(f'Importación exitosa. Se agregaron {count} notificaciones.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al procesar el archivo JSON: {str(e)}', 'danger')
        
    return redirect(url_for('notif.notificaciones'))