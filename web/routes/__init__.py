# Paquete de rutas para la aplicación
from flask import Blueprint

# Crear los Blueprint para las rutas originales
calendario_bp = Blueprint('calendario', __name__)
nomina_bp = Blueprint('nomina', __name__)
detalle_bp = Blueprint('detalle', __name__)
simulador_bp = Blueprint('simulador', __name__)
api_bp = Blueprint('api', __name__)

# Importar las vistas DESPUÉS de crear los blueprints
from routes.calendario_routes import *
from routes.nomina_routes import *
from routes.detalle_routes import *
from routes.simulador_routes import *
from routes.api_routes import *

# NOTA: Los blueprints auth_bp, usuario_bp y admin_bp se crean en sus respectivos archivos
# y NO deben ser definidos aquí para evitar conflictos.