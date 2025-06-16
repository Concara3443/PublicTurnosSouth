from flask import Flask, render_template, redirect, url_for, request
import ssl
import os
import calendar
from datetime import datetime
from flask_login import LoginManager
import pymysql
from werkzeug.middleware.proxy_fix import ProxyFix

# Importar blueprints
from routes import calendario_bp, nomina_bp, detalle_bp, simulador_bp, api_bp
from routes.auth_routes import auth_bp
from routes.usuario_routes import usuario_bp
from routes.admin_routes import admin_bp
from routes.sincronizacion_routes import sincronizacion_bp
from models.usuario import Usuario


def get_month_name(month_number):
    """
    Obtiene el nombre del mes a partir de su número
    """
    # Solo números válidos de mes (1-12)
    if isinstance(month_number, int) and 1 <= month_number <= 12:
        return calendar.month_name[month_number]
    return ""

def create_app():
    """
    Crea y configura la aplicación Flask
    """
    # Configurar carpetas de plantillas de forma explícita
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    
    # Crear aplicación con configuración explícita
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    
    # IMPORTANTE: Configurar ProxyFix para manejar headers del proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Middleware personalizado para manejar el prefijo
    class PrefixMiddleware:
        def __init__(self, app, prefix=''):
            self.app = app
            self.prefix = prefix

        def __call__(self, environ, start_response):
            # Si hay X-Forwarded-Prefix, usar ese; si no, usar el configurado
            forwarded_prefix = environ.get('HTTP_X_FORWARDED_PREFIX', self.prefix)
            if forwarded_prefix:
                # Guardar el prefijo en el environ para que Flask lo use
                environ['SCRIPT_NAME'] = forwarded_prefix
                # Quitar el prefijo del PATH_INFO si lo tiene
                path_info = environ.get('PATH_INFO', '')
                if path_info.startswith(forwarded_prefix):
                    environ['PATH_INFO'] = path_info[len(forwarded_prefix):] or '/'
            return self.app(environ, start_response)
    
    # Aplicar el middleware
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, '/south')
    
    # Configuración de la aplicación
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key_change_in_production')
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    
    # Inicializar Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.obtener_por_id(int(user_id))
    
    # Configuración de Jinja2
    # Añadir filtro personalizado para month_name
    app.jinja_env.filters['month_name'] = get_month_name
    
    # Añadir funciones de utilidad a los templates
    app.jinja_env.globals.update(
        now=datetime.now,
        calendar=calendar,
        date=datetime.date
    )
    
    # Registrar blueprints SIN prefijos (Nginx maneja el /south/)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(usuario_bp, url_prefix='/usuario')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(sincronizacion_bp, url_prefix='/sincronizacion')
    app.register_blueprint(calendario_bp)
    app.register_blueprint(nomina_bp)
    app.register_blueprint(detalle_bp)
    app.register_blueprint(simulador_bp)
    app.register_blueprint(api_bp)
    
    # Asegurar que exista la carpeta static
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    # Ruta para favicon
    @app.route('/favicon.ico')
    def favicon():
        return app.send_static_file('favicon.ico')
    
    # Ruta raíz que redirecciona al calendario
    @app.route('/')
    def index():
        return redirect(url_for('calendario.home'))
    
    # Manejo de errores 404
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    @app.errorhandler(pymysql.OperationalError)
    def handle_db_error(error):
        """Manejador de errores para problemas de conexión a la base de datos"""
        print(f"Error de conexión a la base de datos: {error}")
        return render_template('error/db_error.html'), 500
    
    return app

# Para Waitress - app definido fuera de main
app = create_app()

if __name__ == '__main__':
    cert_path = r'C:\CertificadosWeb\guillermocort.es-chain.pem'
    key_path = r'C:\CertificadosWeb\guillermocort.es-key.pem'
    
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    
    # Habilitar mensajes de depuración
    app.debug = True
    app.run(host="0.0.0.0", port=int(os.getenv('APP_PORT', 1234)), ssl_context=context)