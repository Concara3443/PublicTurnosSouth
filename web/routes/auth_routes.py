from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
import bcrypt
from models.usuario import Usuario
from models.whitelist import EmpleadoWhitelist
from database import execute_query
from datetime import date, timedelta, datetime

# Crear el blueprint de autenticación
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión"""
    # Si ya está autenticado, redirigir a la página principal
    if current_user.is_authenticated:
        return redirect(url_for('calendario.home'))
    
    if request.method == 'POST':
        numero_empleado = request.form.get('numero_empleado')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        # Verificar si existe el usuario
        usuario = Usuario.obtener_por_numero_empleado(numero_empleado)
        
        if usuario:
            # Usuario existe, verificar contraseña
            if usuario.verificar_password(password):
                if not usuario.activo:
                    flash('Esta cuenta está desactivada.', 'danger')
                    return render_template('auth/login.html')
                
                login_user(usuario, remember=remember)
                
                # Actualizar último acceso
                usuario.actualizar_ultimo_acceso()
                
                # Verificar si el usuario tiene turnos en el mes actual
                try:
                    hoy = datetime.now()
                    primer_dia = date(hoy.year, hoy.month, 1)
                    if hoy.month == 12:
                        ultimo_dia = date(hoy.year + 1, 1, 1) - timedelta(days=1)
                    else:
                        ultimo_dia = date(hoy.year, hoy.month + 1, 1) - timedelta(days=1)
                    
                    # Verificar si hay turnos para este mes
                    query_turnos = """
                        SELECT COUNT(*) as count
                        FROM turnos_empleado
                        WHERE empleado_id = %s 
                        AND dia BETWEEN %s AND %s
                        AND activo = 1
                    """
                    result = execute_query(query_turnos, (usuario.id, primer_dia, ultimo_dia), fetchone=True)
                    tiene_turnos = result['count'] > 0 if result else False

                    # Verificar si tiene credenciales SITA configuradas
                    query_credenciales = """
                        SELECT COUNT(*) as count
                        FROM credenciales_sita
                        WHERE empleado_id = %s
                    """
                    result = execute_query(query_credenciales, (usuario.id,), fetchone=True)
                    tiene_credenciales = result['count'] > 0 if result else False
                except Exception as e:
                    print(f"Error al verificar turnos: {e}")
                    tiene_turnos = False
                    tiene_credenciales = False
                
                # Si no tiene turnos pero tiene credenciales, redirigir a sincronización
                if not tiene_turnos and tiene_credenciales:
                    return redirect(url_for('sincronizacion.sincronizar_turnos'))
                
                # Si no tiene credenciales, redirigir a configuración de credenciales
                if not tiene_credenciales:
                    flash('Por favor, configura tus credenciales SITA para sincronizar tus turnos.', 'info')
                    return redirect(url_for('usuario.credenciales_sita'))
                
                # Redirigir a la página original o a la página principal
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                else:
                    return redirect(url_for('calendario.home'))
            else:
                flash('Usuario o contraseña incorrectos.', 'danger')
        else:
            # Verificar si está en la lista blanca
            whitelist_info = EmpleadoWhitelist.verificar(numero_empleado)
            if whitelist_info:
                # Está en la lista blanca, redirigir a registro
                return redirect(url_for('auth.register', numero_empleado=numero_empleado))
            else:
                flash('Usuario o contraseña incorrectos.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Cierra la sesión del usuario"""
    logout_user()
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register/<numero_empleado>', methods=['GET', 'POST'])
def register(numero_empleado):
    """Registro de nuevo usuario desde la lista blanca"""
    # Verificar si ya está autenticado
    if current_user.is_authenticated:
        return redirect(url_for('calendario.home'))

    # Verificar si está en la lista blanca
    whitelist_info = EmpleadoWhitelist.verificar(numero_empleado)
    if not whitelist_info:
        flash('El número de empleado no está autorizado para registrarse.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        # Obtener datos del formulario
        nombre_completo = request.form.get('nombre_completo')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')

        # Validar datos
        if not all([nombre_completo, password, password_confirm]):
            flash('Todos los campos obligatorios deben completarse.', 'danger')
            return render_template('auth/register.html', numero_empleado=numero_empleado, whitelist_info=whitelist_info)

        if password != password_confirm:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('auth/register.html', numero_empleado=numero_empleado, whitelist_info=whitelist_info)

        # Crear usuario
        try:
            user_id = Usuario.crear(numero_empleado, nombre_completo, password, email)
            if user_id:
                # Marcar como registrado en la lista blanca
                EmpleadoWhitelist.marcar_como_registrado(numero_empleado)

                # Iniciar sesión automáticamente
                usuario = Usuario.obtener_por_id(user_id)
                login_user(usuario)

                flash('¡Registro completado con éxito! Ahora puedes configurar tus credenciales de SITA.', 'success')
                return redirect(url_for('usuario.credenciales_sita'))
            else:
                flash('Error al crear el usuario.', 'danger')
        except Exception as e:
            flash(f'Error al registrar usuario: {str(e)}', 'danger')

        return render_template('auth/register.html', numero_empleado=numero_empleado, whitelist_info=whitelist_info)

    return render_template('auth/register.html', numero_empleado=numero_empleado, whitelist_info=whitelist_info)

@auth_bp.route('/demo-login')
def demo_login():
    """Inicio de sesión automático con usuario demo para portfolio"""
    # Si ya está autenticado con otro usuario, cerrar sesión primero
    if current_user.is_authenticated and not current_user.es_demo:
        logout_user()

    # Si ya está autenticado como demo, redirigir al calendario
    if current_user.is_authenticated and current_user.es_demo:
        return redirect(url_for('calendario.home'))

    # Buscar el usuario DEMO
    usuario_demo = Usuario.obtener_por_numero_empleado('DEMO')

    if not usuario_demo:
        flash('Usuario demo no encontrado. Por favor, ejecuta el script de configuración.', 'danger')
        return redirect(url_for('auth.login'))

    if not usuario_demo.activo:
        flash('El usuario demo está desactivado.', 'danger')
        return redirect(url_for('auth.login'))

    # Iniciar sesión con el usuario demo
    login_user(usuario_demo, remember=False)

    # Actualizar último acceso
    usuario_demo.actualizar_ultimo_acceso()

    flash('¡Bienvenido al modo demo! Explora todas las funcionalidades sin afectar datos reales.', 'info')

    # Redirigir al calendario
    return redirect(url_for('calendario.home'))