// static/js/perfilBloqueo.js

document.addEventListener("DOMContentLoaded", function() {
    let lockoutTimer = null;
    let cropper = null;

    // ==========================================
    // 1. TOOLTIPS Y CONTRASEÑAS
    // ==========================================
    try {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) { return new bootstrap.Tooltip(tooltipTriggerEl); });
    } catch(e) {}

    function togglePassword(inputId, iconId) {
        const input = document.getElementById(inputId);
        const icon = document.getElementById(iconId);
        if (input && icon) {
            if (input.type === 'password') {
                input.type = 'text'; icon.classList.replace('bi-eye', 'bi-eye-slash');
            } else {
                input.type = 'password'; icon.classList.replace('bi-eye-slash', 'bi-eye');
            }
        }
    }

    document.querySelectorAll('.btn-toggle-password').forEach(btn => {
        btn.addEventListener('click', function() {
            togglePassword(this.getAttribute('data-target'), this.getAttribute('data-icon'));
        });
    });

    const pinInputs = [document.getElementById('curr-pin'), document.getElementById('pin-new-input')];
    pinInputs.forEach(input => {
        if(input) {
            input.addEventListener('input', function() {
                this.value = this.value.replace(/[^0-9]/g, '');
            });
        }
    });

    // ==========================================
    // 2. MODO EDICIÓN
    // ==========================================
    function toggleEditMode() {
        const wrapper = document.getElementById('profile-wrapper');
        if(wrapper) {
            wrapper.classList.remove('view-mode');
            wrapper.classList.add('edit-mode');
            const inputs = wrapper.querySelectorAll('form#perfil-form input[type="text"], form#perfil-form input[type="number"], form#perfil-form select');
            inputs.forEach(input => input.removeAttribute('readonly'));
        }
    }

    // ==========================================
    // 3. EDITOR DE IMAGEN (CROPPER)
    // ==========================================
    function triggerImageUpload() {
        const wrapper = document.getElementById('profile-wrapper');
        if (wrapper && wrapper.classList.contains('edit-mode')) {
            document.getElementById('flyer-input').click();
        }
    }

    const flyerInput = document.getElementById('flyer-input');
    if(flyerInput) {
        flyerInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function(event) {
                const imgElement = document.getElementById('image-to-crop');
                document.getElementById('editor-container').style.display = 'block';
                document.getElementById('editor-controls').style.display = 'flex';
                document.getElementById('profile-preview-container').style.display = 'none';
                document.getElementById('submit-btn').disabled = true;
                
                imgElement.onload = function() {
                    if (cropper) cropper.destroy();
                    cropper = new Cropper(imgElement, {
                        viewMode: 1, dragMode: 'move', aspectRatio: 1, autoCropArea: 0.8,
                        restore: false, guides: true, center: true, highlight: false,
                        cropBoxMovable: true, cropBoxResizable: true, toggleDragModeOnDblclick: false,
                    });
                };
                imgElement.src = event.target.result;
            };
            reader.readAsDataURL(file);
        });
    }

    function saveCrop() {
        if (!cropper) return;
        const canvas = cropper.getCroppedCanvas({ width: 800, height: 800 });
        const dataUrl = canvas.toDataURL('image/jpeg', 0.7); 
        const sizeInMB = (Math.round((dataUrl.length * 3) / 4) / (1024 * 1024)).toFixed(2);
        
        if (sizeInMB > 1.0) return alert("La imagen sigue siendo mayor a 1MB. Por favor selecciona otra imagen.");

        document.getElementById('current-profile-img').src = dataUrl;
        document.getElementById('current-profile-img').style.display = 'inline-block';
        document.getElementById('placeholder-profile-img').style.display = 'none';
        document.getElementById('carnet-img').src = dataUrl;
        document.getElementById('carnet-img').style.display = 'block';
        document.getElementById('carnet-placeholder').style.display = 'none';
        document.getElementById('imagen_flyer_hidden').value = dataUrl;
        
        const msg = document.getElementById('compression-msg');
        if(msg) {
            msg.innerHTML = `<i class="bi bi-check-circle-fill"></i> Foto actualizada temporalmente. <b>Debes dar clic en "Guardar Cambios" para finalizar.</b>`;
            msg.style.display = 'block';
        }
        cancelCrop();
    }

    function cancelCrop() {
        document.getElementById('editor-container').style.display = 'none';
        document.getElementById('editor-controls').style.display = 'none';
        document.getElementById('profile-preview-container').style.display = 'block';
        document.getElementById('submit-btn').disabled = false;
        if(flyerInput) flyerInput.value = "";
    }

    // ==========================================
    // 4. CAMPOS DINÁMICOS
    // ==========================================
    function addDynamicField() {
        const container = document.getElementById('dynamic-fields-container');
        const selector = document.getElementById('field-selector');
        if(!container || !selector) return;
        
        const type = selector.value;
        if(!type) return;

        const iconMap = {
            'Telefono': 'bi-telephone-fill', 'Whatsapp': 'bi-whatsapp',
            'Emergencia': 'bi-heart-pulse-fill', 'Contacto_Emergencia': 'bi-person-heart',
            'Sangre': 'bi-droplet-fill', 'Nacimiento': 'bi-calendar-event-fill',
            'Provincia': 'bi-map-fill', 'Pais': 'bi-globe-americas',
            'Empresa': 'bi-building-fill', 'Nombre_Grupo': 'bi-people-fill',
            'Usuario': 'bi-person-badge-fill', 'Otros': 'bi-info-circle-fill'
        };

        const div = document.createElement('div');
        div.className = 'mb-3 input-group';
        const iconClass = iconMap[type] || 'bi-info-circle-fill';
        
        let innerHTML = `<span class="input-group-text bg-transparent border-0 shadow-none pe-3" title="${type.replace('_', ' ')}" data-bs-toggle="tooltip"><i class="bi ${iconClass} fs-5 dynamic-icon text-white"></i></span>`;
        
        if(type === 'Sangre') {
            innerHTML += `<select name="dynamic_Sangre" class="form-select glass-input"><option value="O+">O Positivo (O+)</option><option value="O-">O Negativo (O-)</option><option value="A+">A Positivo (A+)</option><option value="A-">A Negativo (A-)</option><option value="B+">B Positivo (B+)</option><option value="B-">B Negativo (B-)</option><option value="AB+">AB Positivo (AB+)</option><option value="AB-">AB Negativo (AB-)</option></select>`;
        } else if (type === 'Provincia') {
            innerHTML += `<select name="dynamic_Provincia" class="form-select glass-input"><option value="San José">San José</option><option value="Alajuela">Alajuela</option><option value="Cartago">Cartago</option><option value="Heredia">Heredia</option><option value="Guanacaste">Guanacaste</option><option value="Puntarenas">Puntarenas</option><option value="Limón">Limón</option></select>`;
        } else if (type === 'Nacimiento') {
            const currentYear = new Date().getFullYear();
            innerHTML += `<input type="number" placeholder="Día" min="1" max="31" name="dynamic_DiaNac" class="form-control glass-input" required><input type="number" placeholder="Mes" min="1" max="12" name="dynamic_MesNac" class="form-control glass-input" required><input type="number" placeholder="Año" max="${currentYear - 16}" name="dynamic_AnoNac" class="form-control glass-input" required>`;
        } else if (['Telefono', 'Whatsapp', 'Emergencia'].includes(type)) {
            innerHTML += `<input type="text" name="dynamic_${type}" class="form-control glass-input" placeholder="Solo 8 números" pattern="\\d{8}" maxlength="8" oninput="this.value = this.value.replace(/[^0-9]/g, '').slice(0, 8);" required>`;
        } else {
            innerHTML += `<input type="text" name="dynamic_${type}" class="form-control glass-input" required>`;
        }

        innerHTML += `<button type="button" class="btn btn-danger glass-btn edit-only btn-remove-dynamic-field">X</button>`;
        div.innerHTML = innerHTML;
        container.appendChild(div);
        try { new bootstrap.Tooltip(div.querySelector('[data-bs-toggle="tooltip"]')); } catch(e){}
    }

    const dfContainer = document.getElementById('dynamic-fields-container');
    if(dfContainer) {
        dfContainer.addEventListener('click', function(e) {
            if(e.target.closest('.btn-remove-dynamic-field')) {
                e.target.closest('.input-group').remove();
            }
        });
    }

    // ==========================================
    // 5. CARNET DIGITAL
    // ==========================================
    function descargarCarnet() {
        const carnetNode = document.getElementById('carnet-export-node');
        const btn = document.getElementById('btn-descargar');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Procesando...';
        btn.disabled = true;

        setTimeout(() => {
            window.html2canvas(carnetNode, {
                scale: 3, backgroundColor: 'transparent', useCORS: true, allowTaint: true, logging: false
            }).then(canvas => {
                btn.innerHTML = originalText;
                btn.disabled = false;
                let enlace = document.createElement('a');
                enlace.download = `Carnet_${window.APP_CONFIG.userName}.png`; // Variable segura del puente JS
                enlace.href = canvas.toDataURL('image/png');
                document.body.appendChild(enlace);
                enlace.click();
                document.body.removeChild(enlace);
            }).catch(err => {
                console.error("Error capturando carnet:", err);
                btn.innerHTML = originalText;
                btn.disabled = false;
                alert("Ocurrió un error al intentar exportar la imagen.");
            });
        }, 300);
    }

    // ==========================================
    // 6. SEGURIDAD Y BLOQUEO DE SESIÓN
    // ==========================================
    function unlockNewPasswordFields(unlock) {
        const fields = document.querySelectorAll('.new-pwd-field');
        const submitBtn = document.getElementById('btn-submit-pass');
        const section = document.getElementById('new-pwd-section');
        
        fields.forEach(el => el.disabled = !unlock);
        if(submitBtn) submitBtn.disabled = !unlock;
        if(section) section.style.opacity = unlock ? '1' : '0.5';
    }

    function displayLockoutUI(rem) {
        const feedback = document.getElementById('cred-feedback');
        if(!feedback) return;
        let h = Math.floor(rem / 3600);
        let m = Math.floor((rem % 3600) / 60);
        let s = rem % 60;
        
        let timeStr = "";
        if(h > 0) timeStr += `${h}h `;
        timeStr += `${m}:${s < 10 ? '0' : ''}${s}`;
        
        feedback.innerHTML = `
            <div class="text-danger small fw-bold lh-sm mb-2">
                <i class="bi bi-x-octagon-fill"></i> Verificación fallida. Credenciales incorrectas o llave inválida.<br>
                <span class="text-warning mt-1 d-block"><i class="bi bi-lock-fill"></i> Bloqueado por ${timeStr}. Usa la Opción B si lo prefieres.</span>
            </div>`;
    }

    function applyLockout(remainingSeconds) {
        const pwdInput = document.getElementById('curr-pwd');
        const pinInput = document.getElementById('curr-pin');
        const btnVerify = document.getElementById('btn-verify-cred');
        const keyFileInput = document.getElementById('key_file_input');
        
        if(pwdInput) pwdInput.disabled = true;
        if(pinInput) pinInput.disabled = true;
        if(btnVerify) btnVerify.disabled = true;
        
        if(!keyFileInput || keyFileInput.files.length === 0) {
            unlockNewPasswordFields(false);
        }

        if(lockoutTimer) clearInterval(lockoutTimer);
        
        let rem = remainingSeconds;
        displayLockoutUI(rem);
        
        lockoutTimer = setInterval(() => {
            rem--;
            if(rem <= 0) {
                clearInterval(lockoutTimer);
                if(pwdInput) pwdInput.disabled = false;
                if(pinInput) pinInput.disabled = false;
                if(btnVerify) btnVerify.disabled = false;
                const feedback = document.getElementById('cred-feedback');
                if(feedback) feedback.innerHTML = '';
            } else {
                displayLockoutUI(rem);
            }
        }, 1000);
    }

    async function verifyCredentialsAjax() {
        const pwdEl = document.getElementById('curr-pwd');
        const pinEl = document.getElementById('curr-pin');
        const feedback = document.getElementById('cred-feedback');
        
        if(!pwdEl || !pinEl || !feedback) return;

        const pwd = pwdEl.value;
        const pin = pinEl.value;
        
        if(!pwd || !pin) {
            feedback.innerHTML = '<span class="text-warning small mb-2 d-block"><i class="bi bi-exclamation-circle"></i> Ingresa la contraseña y el PIN.</span>';
            return;
        }

        try {
            // Uso de la variable segura del puente APP_CONFIG
            const res = await fetch(window.APP_CONFIG.urls.verifyCredentials, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({password: pwd, pin: pin})
            });
            const data = await res.json();
            
            if(data.success) {
                feedback.innerHTML = '<span class="text-success small fw-bold mb-2 d-block"><i class="bi bi-check-circle-fill"></i> ¡Correcto! Ya puedes cambiar tu contraseña.</span>';
                unlockNewPasswordFields(true);
                const keyFileInput = document.getElementById('key_file_input');
                if(keyFileInput) keyFileInput.value = '';
            } else if (data.locked) {
                applyLockout(data.remaining_seconds);
            }
        } catch(err) {
            console.error(err);
        }
    }

    async function verifyKeyAjax() {
        const fileInput = document.getElementById('key_file_input');
        const feedback = document.getElementById('cred-feedback');
        
        if(!fileInput || !feedback) return;

        if(fileInput.files.length === 0) {
            feedback.innerHTML = '<span class="text-warning small mb-2 d-block"><i class="bi bi-exclamation-circle"></i> Selecciona un archivo de llave primero.</span>';
            return;
        }
        
        const formData = new FormData();
        formData.append('key_file', fileInput.files[0]);
        
        try {
            // Uso de la variable segura del puente APP_CONFIG
            const res = await fetch(window.APP_CONFIG.urls.verifyKeyAjax, {
                method: "POST",
                body: formData
            });
            const data = await res.json();
            
            if(data.success) {
                let prependHtml = '<span class="text-info small fw-bold d-block mb-2"><i class="bi bi-file-earmark-check"></i> ¡Llave correcta! Crea tu nueva contraseña.</span>';
                if(lockoutTimer) {
                    if(!feedback.innerHTML.includes('¡Llave correcta!')) {
                        feedback.innerHTML = prependHtml + feedback.innerHTML;
                    }
                } else {
                    feedback.innerHTML = prependHtml;
                }
                unlockNewPasswordFields(true);
                const currPwd = document.getElementById('curr-pwd');
                const currPin = document.getElementById('curr-pin');
                if(currPwd) currPwd.value = '';
                if(currPin) currPin.value = '';
            } else {
                feedback.innerHTML = `<div class="text-danger small fw-bold lh-sm mb-2"><i class="bi bi-x-octagon-fill"></i> Verificación fallida. Credenciales incorrectas o llave inválida.</div>`;
                unlockNewPasswordFields(false);
                fileInput.value = '';
            }
        } catch(err) {
            console.error(err);
        }
    }

    const keyFileInput = document.getElementById('key_file_input');
    if(keyFileInput) {
        keyFileInput.addEventListener('change', function() {
            if(this.files.length === 0) {
                const feedback = document.getElementById('cred-feedback');
                if(!lockoutTimer) {
                    if(feedback) feedback.innerHTML = '';
                } else {
                    if(feedback) feedback.innerHTML = feedback.innerHTML.replace(/<span.*?¡Llave correcta!.*?<\/span>/, '');
                }
                unlockNewPasswordFields(false);
            }
        });
    }

    // ==========================================
    // 7. ASIGNAR EVENTOS A LOS BOTONES (BINDING)
    // ==========================================
    const bindEvent = (id, event, fn) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener(event, fn);
    };

    // Conectamos todos los botones que antes usaban onclick=""
    bindEvent('btn-edit-profile', 'click', toggleEditMode);
    bindEvent('btn-cancel-profile', 'click', () => location.reload());
    bindEvent('profile-avatar-wrapper', 'click', triggerImageUpload);
    bindEvent('btn-crop-zoom-in', 'click', () => { if(cropper) cropper.zoom(0.1); });
    bindEvent('btn-crop-zoom-out', 'click', () => { if(cropper) cropper.zoom(-0.1); });
    bindEvent('btn-crop-move', 'click', () => { if(cropper) cropper.setDragMode('move'); });
    bindEvent('btn-crop-save', 'click', saveCrop);
    bindEvent('btn-crop-cancel', 'click', cancelCrop);
    bindEvent('btn-add-dynamic-field', 'click', addDynamicField);
    bindEvent('btn-descargar', 'click', descargarCarnet);
    bindEvent('btn-verify-cred', 'click', verifyCredentialsAjax);
    bindEvent('btn-verify-key', 'click', verifyKeyAjax);

    // ==========================================
    // 8. EJECUCIONES AL CARGAR LA PÁGINA
    // ==========================================
    const autoDownloadTrigger = document.getElementById('auto-download-key-trigger');
    if (autoDownloadTrigger) {
        const a = document.createElement('a');
        a.href = autoDownloadTrigger.getAttribute('data-url');
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    const initialLockout = window.APP_CONFIG?.lockoutRemaining || 0;
    if (initialLockout > 0) {
        applyLockout(initialLockout);
    }
});