from flask_login import LoginManager
from models.usuario import Usuario
from models.registro_actividad import RegistroActividad

def init_login_manager(app):
    """Inicializa el gestor de login para la aplicación Flask"""
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Cargador de usuario para Flask-Login"""
        return Usuario.obtener_por_id(int(user_id))
    
    @app.before_request
    def before_request():
        """Acciones a realizar antes de cada petición"""
        from flask import request, g
        from flask_login import current_user
        
        # Guardar la IP del cliente en g para registros
        g.client_ip = request.remote_addr
        
        # Si hay un usuario autenticado, registrar último acceso
        if current_user.is_authenticated:
            current_user.actualizar_ultimo_acceso()
    
    return login_manager