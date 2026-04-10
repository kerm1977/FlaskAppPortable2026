# user.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from db import db
from models import User
import json
import io
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
        
        # Crear estructura del archivo JSON para descargar
        archivo_json = json.dumps({"llave_seguridad": encrypted_token}, indent=4)
        session['download_key'] = archivo_json
        session['trigger_download'] = True
        
        flash('Debes guardar esta llave en tu correo. NUNCA compartas esta llave de recuperación poque puede acceder a tu perfil.', 'warning')
        
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
            # Leer el archivo
            file_content = file.read().decode('utf-8').strip()
            
            # Extraer el token (Soporta si es el JSON nuevo o un texto plano viejo)
            try:
                data_json = json.loads(file_content)
                encrypted_token = data_json.get('llave_seguridad', file_content)
            except json.JSONDecodeError:
                encrypted_token = file_content

            # Desencriptar
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
            
            # Generar NUEVA llave JSON Encriptada
            payload = json.dumps({"email": email, "pin": user.rec_pin, "hash": user.password_hash}).encode('utf-8')
            encrypted_token = cipher_suite.encrypt(payload).decode('utf-8')
            
            archivo_json = json.dumps({"llave_seguridad": encrypted_token}, indent=4)
            session['download_key'] = archivo_json
            session['trigger_download'] = True
            
            session.pop('reset_email', None)
            
            flash('Contraseña actualizada. Debes guardar esta llave en tu correo. NUNCA compartas esta llave de recuperación poque puede acceder a tu perfil.', 'warning')
            
            return redirect(url_for('user.login'))
            
    return render_template('new_pass.html')

# --- NUEVA RUTA PARA DESCARGAR EL ARCHIVO FÍSICO ---
@user_bp.route('/download_key')
def download_key():
    if 'download_key' in session:
        key_content = session.pop('download_key')
        
        # Crear un archivo en memoria
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

@user_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'POST':
        current_user.nombre = request.form.get('nombre')
        current_user.primer_apellido = request.form.get('primer_apellido')
        current_user.segundo_apellido = request.form.get('segundo_apellido')
        db.session.commit()
        flash('Perfil actualizado con éxito', 'success')
    return render_template('perfil.html', user=current_user)

@user_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('user.login'))