document.addEventListener('DOMContentLoaded', function() {
    // --- Lógica del Título Dinámico ---
    const siteNameInput = document.getElementById('site-name-input');
    if(siteNameInput) {
        siteNameInput.addEventListener('input', function() {
            const newTitle = this.value.trim() || 'GlassApp Portable';
            
            // Actualiza el título de la pestaña del navegador
            document.title = newTitle;
            
            // Actualiza el nombre en la barra de navegación superior si existe
            const navbarBrand = document.querySelector('.navbar-brand');
            if(navbarBrand) {
                navbarBrand.textContent = newTitle;
            }
        });
    }

    // --- Lógica de Cambio de Tema ---
    const themeBtns = document.querySelectorAll('.theme-btn');
    const hiddenThemeInput = document.getElementById('hidden-theme-input');
    const currentTheme = localStorage.getItem('glass-theme') || 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
    
    // APLICAR AL CARGAR LA PÁGINA (Usamos backgroundImage para no perder el scroll fijo)
    document.body.style.backgroundImage = currentTheme;
    document.body.style.backgroundAttachment = "fixed";
    if(hiddenThemeInput) hiddenThemeInput.value = currentTheme;
    
    // Aplicar bordes al tema actualmente cargado
    themeBtns.forEach(btn => {
        if(btn.getAttribute('data-theme') === currentTheme) {
            btn.style.borderColor = 'white';
            btn.style.transform = 'scale(1.1)';
        }
        
        // Hover e interacción
        btn.addEventListener('mouseenter', () => btn.style.transform = 'scale(1.1)');
        btn.addEventListener('mouseleave', function() {
            if (this.style.borderColor !== 'white') this.style.transform = 'scale(1)';
        });

        // Click para cambiar
        btn.addEventListener('click', function(e) {
            e.preventDefault(); 
            const selectedTheme = this.getAttribute('data-theme');
            
            // Aplicar al body de inmediato para previsualización
            document.body.style.backgroundImage = selectedTheme;
            document.body.style.backgroundAttachment = "fixed";
            
            // Guardar preferencia en el dispositivo y en el input oculto
            localStorage.setItem('glass-theme', selectedTheme);
            if(hiddenThemeInput) hiddenThemeInput.value = selectedTheme;
            
            // Actualizar interfaz de botones
            themeBtns.forEach(b => {
                b.style.borderColor = 'transparent';
                b.style.transform = 'scale(1)';
            });
            this.style.borderColor = 'white';
            this.style.transform = 'scale(1.1)';
        });
    });
});