# notif.py
from flask import Blueprint, render_template, flash, redirect, url_for, request, send_file, jsonify
from flask_login import login_required, current_user
from db import db
from models import Notification, Announcement, AnnouncementReceipt, User
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
    now = datetime.utcnow()
    
    # 1. Extraer el grupo del usuario de forma ultra-segura para los filtros
    user_group = ''
    if getattr(current_user, 'datos_adicionales', None):
        if isinstance(current_user.datos_adicionales, dict):
            user_group = current_user.datos_adicionales.get('Nombre_Grupo', '')
        elif isinstance(current_user.datos_adicionales, str):
            try: 
                user_group = json.loads(current_user.datos_adicionales).get('Nombre_Grupo', '')
            except: 
                pass
            
    user_email_clean = str(current_user.email).strip().lower()

    # ==========================================
    # VISTA PARA SUPERADMINISTRADORES
    # ==========================================
    if current_user.is_superuser:
        # Obtener el número de página de los parámetros de la URL (por defecto 1)
        page = request.args.get('page', 1, type=int)
        
        # Extraer y ordenar aplicando Paginación (15 elementos por página)
        paginated_notifs = Notification.query.order_by(Notification.fecha.desc()).paginate(
            page=page, per_page=15, error_out=False
        )
        
        # EXTRAER LOS COMUNICADOS (POPUPS) PROGRAMADOS
        comunicados = Announcement.query.order_by(Announcement.scheduled_for.desc()).all()
        
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
                
        # Se envían AMBAS variables a la vista
        return render_template('notificador.html', notificaciones=paginated_notifs, comunicados=comunicados)

    # ==========================================
    # VISTA PARA USUARIOS REGULARES (BANDEJA PERSONAL)
    # ==========================================
    else:
        # Los usuarios regulares NO ven los logs del sistema (alertas de superusuario)
        paginated_notifs = None 
        
        # Obtener los anuncios que ya deberían mostrarse por fecha
        all_ann = Announcement.query.filter(Announcement.scheduled_for <= now).order_by(Announcement.scheduled_for.desc()).all()
        comunicados_usuario = []
        
        # Filtrar exactamente los que le corresponden a este usuario
        for ann in all_ann:
            target_val = str(ann.target_value or '').strip().lower()
            
            if ann.target_type == 'all':
                comunicados_usuario.append(ann)
            elif ann.target_type == 'individual':
                # Comprobar si el correo del usuario está en la lista separada por comas
                target_emails = [e.strip().lower() for e in target_val.split(',')]
                if user_email_clean in target_emails:
                    comunicados_usuario.append(ann)
            elif ann.target_type == 'grupo' and str(user_group).strip().lower() == target_val:
                comunicados_usuario.append(ann)
                
        return render_template('notificador.html', notificaciones=paginated_notifs, comunicados=comunicados_usuario)

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

# ==================================================
# LÓGICA DE COMUNICADOS (ANNOUNCEMENTS POPUPS)
# ==================================================
@notif_bp.route('/crear_comunicado', methods=['POST'])
@login_required
def crear_comunicado():
    if not current_user.is_superuser: return redirect(url_for('routes.home'))
    
    try:
        scheduled_str = request.form.get('scheduled_for')
        scheduled_for = datetime.strptime(scheduled_str, '%Y-%m-%dT%H:%M') if scheduled_str else datetime.utcnow()
            
        target_type = request.form.get('target_type')
        target_value = None
        
        if target_type == 'grupo':
            target_value = request.form.get('target_value_grupo')
        elif target_type == 'individual':
            target_value = request.form.get('target_value_individual') # Los correos separados por comas
            
        nuevo = Announcement(
            titulo=request.form.get('titulo'),
            mensaje=request.form.get('mensaje'),
            target_type=target_type,
            target_value=target_value,
            scheduled_for=scheduled_for
        )
        db.session.add(nuevo)
        db.session.commit()
        flash('Comunicado creado y programado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear comunicado: {str(e)}', 'danger')
        
    return redirect(url_for('notif.notificaciones'))

@notif_bp.route('/editar_comunicado/<int:id>', methods=['POST'])
@login_required
def editar_comunicado(id):
    if not current_user.is_superuser: return redirect(url_for('routes.home'))
    comunicado = Announcement.query.get_or_404(id)
    try:
        comunicado.titulo = request.form.get('titulo')
        comunicado.mensaje = request.form.get('mensaje')
        comunicado.target_type = request.form.get('target_type')
        comunicado.target_value = request.form.get('target_value')
        
        scheduled_str = request.form.get('scheduled_for')
        if scheduled_str:
            comunicado.scheduled_for = datetime.strptime(scheduled_str, '%Y-%m-%dT%H:%M')
            
        db.session.commit()
        flash('Comunicado actualizado con éxito.', 'success')
    except:
        db.session.rollback()
        flash('Error al actualizar comunicado.', 'danger')
    return redirect(url_for('notif.notificaciones'))

@notif_bp.route('/eliminar_comunicado/<int:id>', methods=['GET'])
@login_required
def eliminar_comunicado(id):
    if not current_user.is_superuser: return redirect(url_for('routes.home'))
    comunicado = Announcement.query.get_or_404(id)
    try:
        db.session.delete(comunicado)
        db.session.commit()
        flash('Comunicado y todos sus acuses de recibo eliminados.', 'success')
    except:
        db.session.rollback()
        flash('Error al eliminar comunicado.', 'danger')
    return redirect(url_for('notif.notificaciones'))

@notif_bp.route('/marcar_comunicado_ajax', methods=['POST'])
@login_required
def marcar_comunicado_ajax():
    """Recibe 'view' (visto automático), 'remind' (posponer) o 'dismiss' (entendido)"""
    data = request.get_json()
    ann_id = data.get('id')
    action = data.get('action') # 'view', 'remind' o 'dismiss'
    
    if not ann_id: return jsonify({'success': False})
        
    receipt = AnnouncementReceipt.query.filter_by(announcement_id=ann_id, user_id=current_user.id).first()
    
    if not receipt:
        receipt = AnnouncementReceipt(announcement_id=ann_id, user_id=current_user.id)
        db.session.add(receipt)
        
    receipt.leido_en = datetime.utcnow()
    
    # 'dismiss' significa que el usuario aceptó el mensaje y no quiere verlo más
    if action == 'dismiss':
        receipt.no_mostrar = True
    # 'view' registra que se le mostró el popup aunque no haya interactuado aún
    elif action == 'view' and not receipt.no_mostrar:
        pass
        
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# ==================================================
# BUSCADOR EN VIVO DE USUARIOS
# ==================================================
@notif_bp.route('/buscar_usuarios_ajax', methods=['GET'])
@login_required
def buscar_usuarios_ajax():
    """Busca en todos los campos (incluyendo el JSON dinámico) a medida que el usuario escribe"""
    if not current_user.is_superuser:
        return jsonify([])
        
    query_str = request.args.get('q', '').strip().lower()
    if len(query_str) < 2:
        return jsonify([])
        
    # Extraer todos los usuarios para buscar a fondo
    todos = User.query.all()
    resultados = []
    
    for u in todos:
        match = False
        nombre_completo = f"{u.nombre} {u.primer_apellido} {u.segundo_apellido}".lower()
        
        if query_str in nombre_completo or query_str in u.email.lower():
            match = True
            
        if not match and u.datos_adicionales:
            for val in u.datos_adicionales.values():
                if query_str in str(val).lower():
                    match = True
                    break
                    
        if match:
            # Rescatamos algo de información extra para mostrar en el frontend
            extra_info = []
            if u.datos_adicionales:
                if 'Telefono' in u.datos_adicionales:
                    extra_info.append(f"Tel: {u.datos_adicionales['Telefono']}")
                if 'Nombre_Grupo' in u.datos_adicionales:
                    extra_info.append(f"Grupo: {u.datos_adicionales['Nombre_Grupo']}")
            
            if not extra_info:
                extra_info.append(f"Rol: {u.rol}")
                
            resultados.append({
                "email": u.email,
                "nombre_completo": f"{u.nombre} {u.primer_apellido}",
                "extra": " | ".join(extra_info)
            })
            
        if len(resultados) >= 15:
            break
            
    return jsonify(resultados)

# ==================================================
# EXPORTACIÓN E IMPORTACIÓN DE ALERTAS
# ==================================================
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