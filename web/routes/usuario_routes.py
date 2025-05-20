from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import bcrypt
from models.usuario import Usuario
from models.credencial_sita import CredencialSita

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
                
                conn.commit()
                flash('Perfil actualizado correctamente.', 'success')
        except Exception as e:
            flash(f'Error al actualizar perfil: {str(e)}', 'danger')
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
        
        # Validar datos
        if not all([sita_username, sita_password, site_id, cvation_tenantid, roster_url]):
            flash('Todos los campos son obligatorios.', 'danger')
            return redirect(url_for('usuario.credenciales_sita'))
        
        # Validar credenciales SITA
        es_valido, mensaje = CredencialSita.validar_credenciales(
            sita_username, sita_password, site_id, cvation_tenantid, roster_url
        )
        
        if not es_valido:
            flash(f'Error en las credenciales SITA: {mensaje}', 'danger')
            return render_template('usuario/credenciales_sita.html', credenciales=credenciales)
        
        # Guardar credenciales
        if CredencialSita.guardar(
            current_user.id, sita_username, sita_password, 
            site_id, cvation_tenantid, roster_url
        ):
            flash('Credenciales guardadas correctamente.', 'success')
            
            # Redirigir a sincronización inmediata
            return redirect(url_for('sincronizacion.sincronizar_turnos'))
        else:
            flash('Error al guardar las credenciales.', 'danger')
        
        return redirect(url_for('usuario.credenciales_sita'))
    
    return render_template('usuario/credenciales_sita.html', credenciales=credenciales)