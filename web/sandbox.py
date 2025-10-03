"""
Modo Sandbox para usuarios demo
Intercepta operaciones de escritura en la base de datos para usuarios demo
"""

from functools import wraps
from flask import flash, redirect, url_for, request
from flask_login import current_user

def sandbox_mode(func):
    """
    Decorador que intercepta operaciones de escritura para usuarios en modo demo

    Uso:
        @admin_bp.route('/usuarios/nuevo', methods=['POST'])
        @admin_required
        @sandbox_mode
        def nuevo_usuario():
            # Código que modifica la BD
            pass

    Si el usuario tiene es_demo=True:
    - NO se ejecuta el código de la función
    - Se muestra un mensaje de éxito simulado
    - Se redirige a la página apropiada

    Si el usuario NO es demo:
    - Se ejecuta la función normalmente
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # Verificar si el usuario actual está en modo demo
        if hasattr(current_user, 'es_demo') and current_user.es_demo:
            # Usuario en modo demo - simular la acción sin ejecutarla

            # Determinar el mensaje según la ruta
            route_name = request.endpoint if request.endpoint else 'unknown'

            # Mensajes personalizados según la acción
            if 'nuevo' in route_name or 'agregar' in route_name:
                flash('✅ Elemento creado correctamente (modo demo - sin persistencia)', 'success')
            elif 'editar' in route_name or 'actualizar' in route_name:
                flash('✅ Elemento actualizado correctamente (modo demo - sin persistencia)', 'success')
            elif 'eliminar' in route_name or 'borrar' in route_name:
                flash('✅ Elemento eliminado correctamente (modo demo - sin persistencia)', 'success')
            elif 'cambiar' in route_name or 'activar' in route_name or 'desactivar' in route_name:
                flash('✅ Estado cambiado correctamente (modo demo - sin persistencia)', 'success')
            else:
                flash('✅ Acción completada correctamente (modo demo - sin persistencia)', 'success')

            # Determinar a dónde redirigir según la ruta
            if 'usuario' in route_name:
                return redirect(url_for('admin.listar_usuarios'))
            elif 'whitelist' in route_name:
                return redirect(url_for('admin.whitelist'))
            elif 'admin' in route_name:
                return redirect(url_for('admin.panel'))
            else:
                # Por defecto, intentar volver al referer o al panel admin
                return redirect(request.referrer or url_for('admin.panel'))

        # Usuario NO es demo - ejecutar la función normalmente
        return func(*args, **kwargs)

    return decorated_function

def is_demo_mode():
    """
    Función auxiliar para verificar si el usuario actual está en modo demo

    Returns:
        bool: True si el usuario está en modo demo, False en caso contrario
    """
    return hasattr(current_user, 'es_demo') and current_user.es_demo

def require_real_user(message="Esta acción no está disponible en modo demo."):
    """
    Decorador que bloquea completamente una ruta para usuarios demo
    Útil para rutas que no deben estar accesibles en absoluto para usuarios demo

    Uso:
        @app.route('/admin/peligroso')
        @admin_required
        @require_real_user("Esta operación crítica no está disponible en modo demo.")
        def accion_peligrosa():
            # Código sensible
            pass
    """
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if hasattr(current_user, 'es_demo') and current_user.es_demo:
                flash(message, 'warning')
                return redirect(request.referrer or url_for('admin.panel'))
            return func(*args, **kwargs)
        return decorated_function
    return decorator
