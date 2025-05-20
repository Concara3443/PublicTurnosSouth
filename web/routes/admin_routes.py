from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
import bcrypt
from models.usuario import Usuario

admin_bp = Blueprint('admin', __name__)

# Middleware para verificar que el usuario es administrador
def admin_required(func):
    """Decorador que verifica que el usuario actual es administrador"""
    @login_required
    def decorated_view(*args, **kwargs):
        if not current_user.es_admin:
            flash('Acceso denegado. Se requieren privilegios de administrador.', 'danger')
            return redirect(url_for('calendario.home'))
        return func(*args, **kwargs)
    # Preservar el nombre y docstring de la función original
    decorated_view.__name__ = func.__name__
    decorated_view.__doc__ = func.__doc__
    return decorated_view

@admin_bp.route('/')
@admin_required
def panel():
    """Muestra el panel de administración principal"""
    return render_template('admin/panel.html')

@admin_bp.route('/usuarios')
@admin_required
def listar_usuarios():
    """Muestra la lista de todos los usuarios del sistema"""
    # Obtener todos los usuarios
    conn = Usuario.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, numero_empleado, nombre_completo, email, 
                       fecha_creacion, ultimo_acceso, activo, es_admin
                FROM empleados
                ORDER BY nombre_completo
            """)
            usuarios = cursor.fetchall()
    finally:
        conn.close()
    
    return render_template('admin/usuarios.html', usuarios=usuarios)

@admin_bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@admin_required
def nuevo_usuario():
    """Crea un nuevo usuario"""
    if request.method == 'POST':
        # Obtener datos del formulario
        numero_empleado = request.form.get('numero_empleado')
        nombre_completo = request.form.get('nombre_completo')
        email = request.form.get('email')
        password = request.form.get('password')
        es_admin = 'es_admin' in request.form
        
        # Validar datos
        if not all([numero_empleado, nombre_completo, password]):
            flash('Número de empleado, nombre y contraseña son obligatorios.', 'danger')
            return render_template('admin/nuevo_usuario.html')
        
        # Verificar si ya existe un usuario con ese número
        existing = Usuario.obtener_por_numero_empleado(numero_empleado)
        if existing:
            flash(f'Ya existe un usuario con el número de empleado {numero_empleado}.', 'danger')
            return render_template('admin/nuevo_usuario.html')
        
        # Crear usuario
        try:
            user_id = Usuario.crear(numero_empleado, nombre_completo, password, email, es_admin)
            if user_id:
                flash('Usuario creado correctamente.', 'success')
                return redirect(url_for('admin.listar_usuarios'))
            else:
                flash('Error al crear usuario.', 'danger')
        except Exception as e:
            flash(f'Error al crear usuario: {str(e)}', 'danger')
        
        return render_template('admin/nuevo_usuario.html')
    
    return render_template('admin/nuevo_usuario.html')

@admin_bp.route('/usuarios/editar/<int:usuario_id>', methods=['GET', 'POST'])
@admin_required
def editar_usuario(usuario_id):
    """Edita un usuario existente"""
    # Obtener usuario
    conn = Usuario.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, numero_empleado, nombre_completo, email, 
                       fecha_creacion, ultimo_acceso, activo, es_admin
                FROM empleados
                WHERE id = %s
            """, (usuario_id,))
            usuario = cursor.fetchone()
            
            if not usuario:
                flash('Usuario no encontrado.', 'danger')
                return redirect(url_for('admin.listar_usuarios'))
            
            if request.method == 'POST':
                # Obtener datos del formulario
                nombre_completo = request.form.get('nombre_completo')
                email = request.form.get('email')
                password = request.form.get('password')
                es_admin = 'es_admin' in request.form
                activo = 'activo' in request.form
                
                # Actualizar usuario
                update_query = """
                    UPDATE empleados
                    SET nombre_completo = %s, 
                        email = %s,
                        es_admin = %s,
                        activo = %s
                """
                params = [nombre_completo, email, 1 if es_admin else 0, 1 if activo else 0]
                
                # Si se proporciona contraseña, actualizarla
                if password:
                    password_hash = bcrypt.hashpw(
                        password.encode('utf-8'),
                        bcrypt.gensalt()
                    ).decode('utf-8')
                    update_query += ", password_hash = %s"
                    params.append(password_hash)
                
                update_query += " WHERE id = %s"
                params.append(usuario_id)
                
                cursor.execute(update_query, params)
                conn.commit()
                
                flash('Usuario actualizado correctamente.', 'success')
                return redirect(url_for('admin.listar_usuarios'))
    except Exception as e:
        flash(f'Error al procesar la solicitud: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return render_template('admin/editar_usuario.html', usuario=usuario)

@admin_bp.route('/usuarios/cambiar-estado/<int:usuario_id>', methods=['POST'])
@admin_required
def cambiar_estado(usuario_id):
    """Cambia el estado de un usuario (activo/inactivo)"""
    # Verificar que no sea el usuario actual
    if usuario_id == current_user.id:
        flash('No puedes desactivar tu propia cuenta.', 'danger')
        return redirect(url_for('admin.listar_usuarios'))
    
    # Obtener el estado actual y cambiarlo
    conn = Usuario.get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Obtener estado actual
            cursor.execute("SELECT activo FROM empleados WHERE id = %s", (usuario_id,))
            result = cursor.fetchone()
            
            if not result:
                flash('Usuario no encontrado.', 'danger')
                return redirect(url_for('admin.listar_usuarios'))
            
            # Cambiar estado
            nuevo_estado = 0 if result['activo'] else 1
            cursor.execute(
                "UPDATE empleados SET activo = %s WHERE id = %s",
                (nuevo_estado, usuario_id)
            )
            conn.commit()
            
            estado_str = "activado" if nuevo_estado else "desactivado"
            flash(f'Usuario {estado_str} correctamente.', 'success')
    except Exception as e:
        flash(f'Error al cambiar estado: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('admin.listar_usuarios'))

@admin_bp.route('/usuarios/eliminar/<int:usuario_id>', methods=['POST'])
@admin_required
def eliminar_usuario(usuario_id):
    """Elimina un usuario del sistema"""
    # Verificar que no sea el usuario actual
    if usuario_id == current_user.id:
        flash('No puedes eliminar tu propia cuenta.', 'danger')
        return redirect(url_for('admin.listar_usuarios'))
    
    # Eliminar usuario
    conn = Usuario.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM empleados WHERE id = %s", (usuario_id,))
            conn.commit()
            flash('Usuario eliminado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar usuario: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('admin.listar_usuarios'))
from models.whitelist import EmpleadoWhitelist

@admin_bp.route('/whitelist')
@admin_required
def whitelist():
    """Muestra la lista blanca de empleados que pueden registrarse"""
    empleados = EmpleadoWhitelist.listar_todos()
    return render_template('admin/whitelist.html', empleados=empleados)

@admin_bp.route('/whitelist/agregar', methods=['GET', 'POST'])
@admin_required
def agregar_whitelist():
    """Agrega un empleado a la lista blanca"""
    if request.method == 'POST':
        numero_empleado = request.form.get('numero_empleado')
        nombre_completo = request.form.get('nombre_completo')
        email = request.form.get('email')
        
        if not numero_empleado:
            flash('El número de empleado es obligatorio.', 'danger')
            return render_template('admin/agregar_whitelist.html')
        
        # Verificar si ya existe un usuario con ese número
        from models.usuario import Usuario
        existing = Usuario.obtener_por_numero_empleado(numero_empleado)
        if existing:
            flash(f'Ya existe un usuario registrado con el número {numero_empleado}.', 'danger')
            return render_template('admin/agregar_whitelist.html')
        
        # Agregar a la lista blanca
        if EmpleadoWhitelist.agregar(numero_empleado, nombre_completo, email):
            flash('Empleado agregado a la lista blanca correctamente.', 'success')
            return redirect(url_for('admin.whitelist'))
        else:
            flash('Error al agregar empleado a la lista blanca.', 'danger')
        
        return render_template('admin/agregar_whitelist.html')
    
    return render_template('admin/agregar_whitelist.html')

@admin_bp.route('/whitelist/eliminar/<numero_empleado>', methods=['POST'])
@admin_required
def eliminar_whitelist(numero_empleado):
    """Elimina un empleado de la lista blanca"""
    if EmpleadoWhitelist.eliminar(numero_empleado):
        flash('Empleado eliminado de la lista blanca correctamente.', 'success')
    else:
        flash('Error al eliminar empleado de la lista blanca.', 'danger')
    
    return redirect(url_for('admin.whitelist'))