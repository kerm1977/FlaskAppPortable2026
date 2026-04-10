# user.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from db import db
from models import User
import json
import io
import time
from cryptography.fernet import Fernet

user_bp = Blueprint('user', __name__)

# Clave de encriptación para la llave JSON (En producción, usar variables de entorno)
SECRET_KEY_FERNET = Fernet.generate_key()
cipher_suite = Fernet(SECRET_KEY_FERNET)

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('routes.home'))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')
    return render_template('login.html')

@user_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        email = request.form.get('email')
        if User.query.filter_by(email=email).first():
            flash('El correo ya está registrado.', 'danger')
            return redirect(url_for('user.registro'))
            
        password = request.form.get('password')
        pin = request.form.get('rec_pin')
        hashed_pw = generate_password_hash(password)
        
        # Recolectar campos dinámicos
        datos_adicionales = {}
        for key, value in request.form.items():
            if key.startswith('dynamic_'):
                datos_adicionales[key.replace('dynamic_', '')] = value
                
        nuevo_usuario = User(
            imagen_flyer=request.form.get('imagen_flyer'),
            nombre=request.form.get('nombre'),
            primer_apellido=request.form.get('primer_apellido'),
            segundo_apellido=request.form.get('segundo_apellido'),
            email=email,
            password_hash=hashed_pw,
            rec_pin=pin,
            datos_adicionales=datos_adicionales
        )
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        # Generar JSON Encriptado
        payload = json.dumps({"email": email, "pin": pin, "hash": hashed_pw}).encode('utf-8')
        encrypted_token = cipher_suite.encrypt(payload).decode('utf-8')
        
        archivo_json = json.dumps({"llave_seguridad": encrypted_token}, indent=4)
        session['download_key'] = archivo_json
        session['trigger_download'] = True
        
        flash('Debes guardar esta llave en tu correo. NUNCA compartas esta llave de recuperación porque puede acceder a tu perfil.', 'warning')
        
        return redirect(url_for('user.login'))
        
    return render_template('registro.html')

@user_bp.route('/reset_pass', methods=['GET', 'POST'])
def reset_pass():
    if request.method == 'POST':
        if 'key_file' not in request.files:
            flash('No se subió ningún archivo', 'danger')
            return redirect(request.url)
            
        file = request.files['key_file']
        if file.filename == '':
            flash('No seleccionaste ningún archivo', 'danger')
            return redirect(request.url)
            
        try:
            file_content = file.read().decode('utf-8').strip()
            
            try:
                data_json = json.loads(file_content)
                encrypted_token = data_json.get('llave_seguridad', file_content)
            except json.JSONDecodeError:
                encrypted_token = file_content

            decrypted_data = cipher_suite.decrypt(encrypted_token.encode('utf-8')).decode('utf-8')
            key_json = json.loads(decrypted_data)
            
            email = key_json.get('email')
            user = User.query.filter_by(email=email).first()
            
            if user:
                session['reset_email'] = email
                flash('Llave verificada correctamente. Por favor ingresa tu nueva contraseña.', 'success')
                return redirect(url_for('user.new_pass'))
            else:
                flash('La llave no pertenece a ningún usuario registrado.', 'danger')
        except Exception as e:
            print("Error al desencriptar:", str(e))
            flash('El archivo proporcionado no es una llave válida o está corrupto.', 'danger')
            
    return render_template('reset_pass.html')

@user_bp.route('/new_pass', methods=['GET', 'POST'])
def new_pass():
    if 'reset_email' not in session:
        flash('Acceso denegado. Sube tu llave de recuperación primero.', 'danger')
        return redirect(url_for('user.reset_pass'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        verify_password = request.form.get('verify_password')
        
        if password != verify_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('user.new_pass'))
            
        email = session['reset_email']
        user = User.query.filter_by(email=email).first()
        
        if user:
            user.password_hash = generate_password_hash(password)
            db.session.commit()
            
            payload = json.dumps({"email": email, "pin": user.rec_pin, "hash": user.password_hash}).encode('utf-8')
            encrypted_token = cipher_suite.encrypt(payload).decode('utf-8')
            
            archivo_json = json.dumps({"llave_seguridad": encrypted_token}, indent=4)
            session['download_key'] = archivo_json
            session['trigger_download'] = True
            
            session.pop('reset_email', None)
            
            flash('Contraseña actualizada. Debes guardar esta llave en tu correo. NUNCA compartas esta llave de recuperación porque puede acceder a tu perfil.', 'warning')
            
            return redirect(url_for('user.login'))
            
    return render_template('new_pass.html')

@user_bp.route('/download_key')
def download_key():
    if 'download_key' in session:
        key_content = session.pop('download_key')
        mem = io.BytesIO()
        mem.write(key_content.encode('utf-8'))
        mem.seek(0)
        return send_file(
            mem,
            as_attachment=True,
            download_name='llave_recuperacion.json',
            mimetype='application/json'
        )
    return redirect(url_for('user.login'))

# --- VERIFICACIÓN AJAX CON BLOQUEO DE SESIÓN (PRG Y ESCALONADO) ---
@user_bp.route('/verify_credentials', methods=['POST'])
@login_required
def verify_credentials():
    data = request.get_json()
    password = data.get('password')
    pin = data.get('pin')
    
    ahora = time.time()
    
    # 1. Comprobar si actualmente está bloqueado en la sesión
    lockout_until = session.get('cred_lockout_until', 0)
    if ahora < lockout_until:
        remaining = int(lockout_until - ahora)
        return jsonify({"success": False, "locked": True, "remaining_seconds": remaining})

    # 2. Verificación Exitosa
    if current_user and password and pin:
        if check_password_hash(current_user.password_hash, password) and current_user.rec_pin == pin:
            # Limpiar bloqueos al tener éxito
            session.pop('cred_failed_attempts', None)
            session.pop('cred_lockout_until', None)
            return jsonify({"success": True})

    # 3. Verificación Fallida: Incrementar conteo y bloquear
    intentos = session.get('cred_failed_attempts', 0) + 1
    session['cred_failed_attempts'] = intentos
    
    # Lógica de tiempos escalonados
    if intentos == 1:
        bloqueo_segundos = 2 * 60       # 2 minutos
    elif intentos == 2:
        bloqueo_segundos = 4 * 60       # 4 minutos
    elif intentos == 3:
        bloqueo_segundos = 60 * 60      # 1 hora
    elif intentos == 4:
        bloqueo_segundos = 2 * 60 * 60  # 2 horas
    else:
        bloqueo_segundos = 24 * 60 * 60 # 24 horas

    session['cred_lockout_until'] = ahora + bloqueo_segundos

    return jsonify({"success": False, "locked": True, "remaining_seconds": bloqueo_segundos})

# --- NUEVA RUTA: VALIDAR LLAVE EN TIEMPO REAL AJAX ---
@user_bp.route('/verify_key_ajax', methods=['POST'])
@login_required
def verify_key_ajax():
    if 'key_file' not in request.files:
        return jsonify({"success": False})
    
    file = request.files['key_file']
    if file.filename == '':
        return jsonify({"success": False})
        
    try:
        file_content = file.read().decode('utf-8').strip()
        try:
            data_json = json.loads(file_content)
            encrypted_token = data_json.get('llave_seguridad', file_content)
        except json.JSONDecodeError:
            encrypted_token = file_content

        decrypted_data = cipher_suite.decrypt(encrypted_token.encode('utf-8')).decode('utf-8')
        key_json = json.loads(decrypted_data)
        
        if key_json.get('email') == current_user.email:
            return jsonify({"success": True})
    except Exception as e:
        print("Error al desencriptar:", str(e))
        
    return jsonify({"success": False})

@user_bp.route('/change_pass_profile', methods=['POST'])
@login_required
def change_pass_profile():
    new_password = request.form.get('new_password')
    verify_new_password = request.form.get('verify_new_password')

    if new_password != verify_new_password:
        flash('Las contraseñas nuevas no coinciden.', 'danger')
        return redirect(url_for('user.perfil'))

    verificacion_exitosa = False

    # Opción A: Contraseña + PIN (Se verifica solo si NO está bloqueado)
    ahora = time.time()
    lockout_until = session.get('cred_lockout_until', 0)
    
    if ahora >= lockout_until:
        current_password = request.form.get('current_password')
        current_pin = request.form.get('current_pin')
        
        if current_password and current_pin:
            if check_password_hash(current_user.password_hash, current_password) and current_user.rec_pin == current_pin:
                verificacion_exitosa = True

    # Opción B: Llave JSON (Invalida el bloqueo por intentos fallidos de Opción A)
    if not verificacion_exitosa and 'key_file' in request.files:
        file = request.files['key_file']
        if file.filename != '':
            try:
                file_content = file.read().decode('utf-8').strip()
                try:
                    data_json = json.loads(file_content)
                    encrypted_token = data_json.get('llave_seguridad', file_content)
                except json.JSONDecodeError:
                    encrypted_token = file_content

                decrypted_data = cipher_suite.decrypt(encrypted_token.encode('utf-8')).decode('utf-8')
                key_json = json.loads(decrypted_data)
                
                if key_json.get('email') == current_user.email:
                    verificacion_exitosa = True
            except Exception as e:
                print("Error al desencriptar la llave:", str(e))

    if verificacion_exitosa:
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()

        # Limpiar bloqueos porque logró cambiar la clave
        session.pop('cred_failed_attempts', None)
        session.pop('cred_lockout_until', None)

        # Generar Nueva Llave
        payload = json.dumps({"email": current_user.email, "pin": current_user.rec_pin, "hash": current_user.password_hash}).encode('utf-8')
        encrypted_token = cipher_suite.encrypt(payload).decode('utf-8')
        
        archivo_json = json.dumps({"llave_seguridad": encrypted_token}, indent=4)
        session['download_key'] = archivo_json
        session['trigger_download'] = True

        flash('Tu contraseña ha sido actualizada. Se está descargando tu nueva llave de seguridad.', 'success')
    else:
        flash('No pudimos procesar tu cambio de contraseña.', 'danger')

    return redirect(url_for('user.perfil'))

# --- NUEVA RUTA: CAMBIO DE PIN DESDE EL PERFIL ---
@user_bp.route('/change_pin_profile', methods=['POST'])
@login_required
def change_pin_profile():
    current_password = request.form.get('current_password')
    new_pin = request.form.get('new_pin')
    
    if check_password_hash(current_user.password_hash, current_password):
        current_user.rec_pin = new_pin
        db.session.commit()
        
        # Generar nueva llave ya que el PIN cambió
        payload = json.dumps({"email": current_user.email, "pin": new_pin, "hash": current_user.password_hash}).encode('utf-8')
        encrypted_token = cipher_suite.encrypt(payload).decode('utf-8')
        archivo_json = json.dumps({"llave_seguridad": encrypted_token}, indent=4)
        session['download_key'] = archivo_json
        session['trigger_download'] = True
        
        flash('Tu PIN ha sido actualizado y se ha generado una nueva llave de seguridad.', 'success')
    else:
        flash('Contraseña incorrecta. No se pudo cambiar el PIN.', 'danger')
        
    return redirect(url_for('user.perfil'))

@user_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'POST':
        nueva_imagen = request.form.get('imagen_flyer')
        if nueva_imagen:
            current_user.imagen_flyer = nueva_imagen
            
        current_user.nombre = request.form.get('nombre')
        current_user.primer_apellido = request.form.get('primer_apellido')
        current_user.segundo_apellido = request.form.get('segundo_apellido')
        
        nuevos_datos = {}
        for key, value in request.form.items():
            if key.startswith('dynamic_'):
                nuevos_datos[key.replace('dynamic_', '')] = value
                
        if nuevos_datos or any(k.startswith('dynamic_') for k in request.form.keys()):
             current_user.datos_adicionales = nuevos_datos
        
        db.session.commit()
        flash('Perfil actualizado con éxito', 'success')
        return redirect(url_for('user.perfil'))
        
    # Calcular si el usuario está bloqueado actualmente para mandarlo al frontend
    ahora = time.time()
    lockout_until = session.get('cred_lockout_until', 0)
    lockout_remaining = int(lockout_until - ahora) if lockout_until > ahora else 0
        
    return render_template('perfil.html', user=current_user, lockout_remaining=lockout_remaining)

@user_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('user.login'))