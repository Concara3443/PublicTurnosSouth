from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import bcrypt
from models.usuario import Usuario
from models.credencial_sita import CredencialSita
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("usuario_routes")

usuario_bp = Blueprint('usuario', __name__)

@usuario_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    """Muestra y permite editar el perfil del usuario"""
    if request.method == 'POST':
        # Procesar cambios en el perfil
        nombre_completo = request.form.get('nombre_completo')
        email = request.form.get('email')
        password_actual = request.form.get('password_actual')
        password_nueva = request.form.get('password_nueva')
        password_confirmacion = request.form.get('password_confirmacion')
        
        # Validar datos básicos
        if not nombre_completo:
            flash('El nombre completo es obligatorio.', 'danger')
            return redirect(url_for('usuario.perfil'))
        
        # Actualizar nombre y email
        conn = Usuario.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Actualizar nombre y email primero
                cursor.execute("""
                    UPDATE empleados
                    SET nombre_completo = %s, email = %s
                    WHERE id = %s
                """, (nombre_completo, email, current_user.id))
                
                # Si se proporcionó contraseña, actualizarla
                if password_actual and password_nueva and password_confirmacion:
                    # Verificar contraseña actual
                    if not current_user.verificar_password(password_actual):
                        flash('La contraseña actual no es correcta.', 'danger')
                        return redirect(url_for('usuario.perfil'))
                    
                    # Verificar que las contraseñas nuevas coincidan
                    if password_nueva != password_confirmacion:
                        flash('Las contraseñas nuevas no coinciden.', 'danger')
                        return redirect(url_for('usuario.perfil'))
                    
                    # Verificar longitud mínima
                    if len(password_nueva) < 6:
                        flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
                        return redirect(url_for('usuario.perfil'))
                    
                    # Actualizar contraseña
                    password_hash = bcrypt.hashpw(
                        password_nueva.encode('utf-8'), 
                        bcrypt.gensalt()
                    ).decode('utf-8')
                    
                    cursor.execute("""
                        UPDATE empleados
                        SET password_hash = %s
                        WHERE id = %s
                    """, (password_hash, current_user.id))
                    
                    flash('Contraseña actualizada correctamente.', 'success')
                
                conn.commit()
                flash('Perfil actualizado correctamente.', 'success')
        except Exception as e:
            logger.error(f"Error al actualizar perfil: {e}")
            flash(f'Error al actualizar perfil. Por favor, intente nuevamente.', 'danger')
        finally:
            conn.close()
        
        return redirect(url_for('usuario.perfil'))
    
    return render_template('usuario/perfil.html')

@usuario_bp.route('/credenciales-sita', methods=['GET', 'POST'])
@login_required
def credenciales_sita():
    """Permite al usuario configurar sus credenciales de SITA"""
    # Obtener credenciales actuales
    credenciales = CredencialSita.obtener_por_empleado(current_user.id)
    
    if request.method == 'POST':
        # Obtener datos del formulario
        sita_username = request.form.get('sita_username')
        sita_password = request.form.get('sita_password')
        site_id = request.form.get('site_id')
        cvation_tenantid = request.form.get('cvation_tenantid')
        roster_url = request.form.get('roster_url')
        skip_validation = request.form.get('skip_validation') == 'on'
        
        # Validar datos
        if not all([sita_username, sita_password, site_id, cvation_tenantid, roster_url]):
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('usuario/credenciales_sita.html', credenciales=credenciales)
        
        # Si se solicita omitir validación o hay credenciales guardadas previamente, guardar directamente
        if skip_validation or credenciales:
            success, message = CredencialSita.guardar(
                current_user.id, sita_username, sita_password, 
                site_id, cvation_tenantid, roster_url,
                validar=False
            )
            
            if success:
                flash('Credenciales guardadas correctamente.', 'success')
                # Redirigir a sincronización inmediata
                return redirect(url_for('sincronizacion.sincronizar_turnos'))
            else:
                flash(f'Error al guardar las credenciales: {message}', 'danger')
        else:
            # Intentar validar las credenciales
            success, message = CredencialSita.validar_credenciales(
                sita_username, sita_password, site_id, cvation_tenantid, roster_url,
                timeout=30  # Aumentar timeout a 30 segundos
            )
            
            if success:
                # Si la validación es exitosa, guardar las credenciales
                success, save_msg = CredencialSita.guardar(
                    current_user.id, sita_username, sita_password, 
                    site_id, cvation_tenantid, roster_url,
                    validar=False  # Ya validamos, no es necesario validar de nuevo
                )
                
                if success:
                    flash('Credenciales validadas y guardadas correctamente.', 'success')
                    # Redirigir a sincronización inmediata
                    return redirect(url_for('sincronizacion.sincronizar_turnos'))
                else:
                    flash(f'Error al guardar las credenciales: {save_msg}', 'danger')
            else:
                # Si la validación falla, mostrar el error y la opción de guardar sin validar
                flash(f'Error en las credenciales SITA: {message}', 'danger')
                return render_template('usuario/credenciales_sita_error.html', 
                                     credenciales=credenciales,
                                     form_data={
                                         'sita_username': sita_username,
                                         'sita_password': sita_password,
                                         'site_id': site_id,
                                         'cvation_tenantid': cvation_tenantid,
                                         'roster_url': roster_url
                                     })
        
        return redirect(url_for('usuario.credenciales_sita'))
    
    return render_template('usuario/credenciales_sita.html', credenciales=credenciales)

@usuario_bp.route('/credenciales-sita/guardar-sin-validar', methods=['POST'])
@login_required
def guardar_credenciales_sin_validar():
    """Guarda las credenciales SITA sin validar"""
    # Obtener datos del formulario
    sita_username = request.form.get('sita_username')
    sita_password = request.form.get('sita_password')
    site_id = request.form.get('site_id')
    cvation_tenantid = request.form.get('cvation_tenantid')
    roster_url = request.form.get('roster_url')
    
    # Validar datos
    if not all([sita_username, sita_password, site_id, cvation_tenantid, roster_url]):
        flash('Todos los campos son obligatorios.', 'danger')
        return redirect(url_for('usuario.credenciales_sita'))
    
    # Guardar sin validar
    success, message = CredencialSita.guardar(
        current_user.id, sita_username, sita_password, 
        site_id, cvation_tenantid, roster_url,
        validar=False
    )
    
    if success:
        flash('Credenciales guardadas correctamente (sin validación).', 'success')
        # Redirigir a página principal
        return redirect(url_for('calendario.home'))
    else:
        flash(f'Error al guardar las credenciales: {message}', 'danger')
        return redirect(url_for('usuario.credenciales_sita'))

@usuario_bp.route('/check-servidor-sita', methods=['GET'])
@login_required
def check_servidor_sita():
    """Verifica si el servidor SITA está disponible"""
    import requests
    
    try:
        response = requests.get("https://sitaess-prod-frontdoor.azurefd.net", timeout=5)
        if response.status_code == 200:
            return jsonify({"status": "ok", "message": "El servidor SITA está disponible"})
        else:
            return jsonify({"status": "error", "message": f"El servidor SITA respondió con código {response.status_code}"})
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "message": f"No se pudo conectar con el servidor SITA: {str(e)}"})