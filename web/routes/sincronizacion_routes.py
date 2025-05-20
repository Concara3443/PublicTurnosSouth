from flask import Blueprint, jsonify, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
import requests
import json
import time
from datetime import datetime, timedelta
import os
from cryptography.fernet import Fernet
from models.credencial_sita import CredencialSita  # Asegúrate de que esta importación es correcta
from database import get_db_connection, execute_query

sincronizacion_bp = Blueprint('sincronizacion', __name__)

@sincronizacion_bp.route('/sincronizar-turnos')
@login_required
def sincronizar_turnos():
    """Sincroniza los turnos del usuario actual"""
    # Verificar si el usuario tiene credenciales SITA
    credenciales = CredencialSita.obtener_por_empleado(current_user.id)
    if not credenciales:
        flash('No tienes credenciales SITA configuradas. Por favor, configúralas primero.', 'warning')
        return redirect(url_for('usuario.credenciales_sita'))
    
    # Renderizar página de carga que hará la petición AJAX
    return render_template('sincronizacion/cargando.html')

@sincronizacion_bp.route('/api/sincronizar', methods=['POST'])
@login_required
def api_sincronizar():
    """API para sincronizar turnos del usuario actual"""
    logs = []
    
    def add_log(message):
        """Añade un mensaje al registro"""
        logs.append(message)
        print(message)
    
    try:
        add_log(f"Iniciando sincronización para usuario: {current_user.nombre_completo}")
        
        # Obtener credenciales SITA
        add_log("Obteniendo credenciales SITA...")
        credenciales = CredencialSita.obtener_por_empleado(current_user.id)
        if not credenciales:
            add_log("ERROR: No se encontraron credenciales SITA configuradas")
            return jsonify({
                'success': False, 
                'message': 'No hay credenciales SITA configuradas',
                'logs': logs
            })
        
        # Verificar que las credenciales tienen toda la información necesaria
        add_log("Verificando credenciales...")
        required_keys = ['sita_username', 'site_id', 'cvation_tenantid', 'roster_url']
        missing_keys = [key for key in required_keys if key not in credenciales]
        
        if missing_keys:
            add_log(f"ERROR: Faltan claves en las credenciales: {', '.join(missing_keys)}")
            return jsonify({
                'success': False, 
                'message': f'Faltan claves en las credenciales: {", ".join(missing_keys)}',
                'logs': logs
            })
        
        # Verificar que hay al menos una forma de obtener la contraseña
        if 'sita_password' not in credenciales and 'sita_password_encrypted' not in credenciales:
            add_log("ERROR: No se encontró la contraseña SITA (ni encriptada ni en texto plano)")
            return jsonify({
                'success': False, 
                'message': 'No se encontró la contraseña SITA (ni encriptada ni en texto plano)',
                'logs': logs
            })
        
        # Obtener turnos desde SITA
        add_log(f"Conectando con SITA con usuario: {credenciales['sita_username']}...")
        try:
            turnos = obtener_turnos_sita(credenciales)
            if turnos:
                dias_totales = len(turnos)
                add_log(f"Se obtuvieron datos de {dias_totales} días desde SITA")
            else:
                add_log("No se encontraron turnos en SITA para el rango especificado")
                return jsonify({
                    'success': False, 
                    'message': 'No se encontraron turnos en SITA',
                    'logs': logs
                })
        except Exception as e:
            add_log(f"ERROR al obtener turnos de SITA: {str(e)}")
            return jsonify({
                'success': False, 
                'message': f'Error al obtener turnos desde SITA: {str(e)}',
                'logs': logs
            })
        
        # Insertar turnos en la base de datos
        add_log("Guardando turnos en la base de datos...")
        try:
            actualizados = insertar_turnos_en_bd(current_user.id, turnos)
            add_log(f"Se actualizaron {actualizados} días con turnos en la base de datos")
        except Exception as e:
            add_log(f"ERROR al guardar turnos en la base de datos: {str(e)}")
            return jsonify({
                'success': False, 
                'message': f'Error al guardar turnos: {str(e)}',
                'logs': logs
            })
        
        add_log("Sincronización completada exitosamente")
        return jsonify({
            'success': True, 
            'message': f'Sincronización completada. {actualizados} días actualizados.',
            'redirect_url': url_for('calendario.home'),
            'logs': logs,
            'updated_days': actualizados
        })
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        add_log(f"ERROR durante la sincronización: {str(e)}")
        add_log(f"Detalles del error: {error_details}")
        
        return jsonify({
            'success': False, 
            'message': f'Error durante la sincronización: {str(e)}',
            'logs': logs
        })

def obtener_turnos_sita(credenciales):
    """Obtiene los turnos desde SITA para el usuario actual"""
    # Desencriptar contraseña SITA
    encryption_key = os.getenv('ENCRYPTION_KEY')
    if not encryption_key:
        raise ValueError("No se encontró ENCRYPTION_KEY en las variables de entorno")
    
    # Revisar qué clave contiene la contraseña
    if 'sita_password' in credenciales:
        # Si ya está desencriptada
        sita_password = credenciales['sita_password']
    elif 'sita_password_encrypted' in credenciales:
        # Si está encriptada
        cipher_suite = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        password_encrypted = credenciales['sita_password_encrypted']
        sita_password = cipher_suite.decrypt(
            password_encrypted.encode() if isinstance(password_encrypted, str) else password_encrypted
        ).decode()
    else:
        # No se encontró la contraseña
        raise ValueError("No se encontró la contraseña SITA en las credenciales")
    
    # Definir cabeceras y payload para la autenticación
    headers = {
        "accept": "application/json",
        "accept-language": "es-ES,es;q=0.9",
        "authorization": "Bearer",
        "content-type": "application/json",
        "cvation_tenantid": credenciales['cvation_tenantid'],
        "origin": "https://sitaess-prod-frontdoor.azurefd.net",
        "priority": "u=1, i",
        "referer": "https://sitaess-prod-frontdoor.azurefd.net/",
        "sec-ch-ua": '"Chromium";v="116", "Not:A-Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
    }
    
    payload = {
        "username": credenciales['sita_username'],
        "password": sita_password,
        "siteId": credenciales['site_id']
    }
    
    # Log para depuración
    log_message = f"Intentando autenticar con: Usuario={credenciales['sita_username']}, SiteID={credenciales['site_id']}"
    print(log_message)
    
    # URL de autenticación
    auth_url = "https://sitaess-prod-frontdoor.azurefd.net/api/v1/auth/signin"
    
    # Autenticación
    response = requests.post(auth_url, headers=headers, json=payload, timeout=30)
    
    if response.status_code != 200:
        error_msg = f"Error de autenticación: {response.status_code} - {response.text}"
        print(error_msg)
        raise Exception(error_msg)
    
    data = response.json()
    token = data.get("sessionToken")
    if not token:
        raise Exception("No se recibió token de autenticación")
    
    print(f"Autenticación exitosa. Token obtenido.")
    
    # Definir rango de fechas para la consulta - desde el día 1 del mes actual
    hoy = datetime.now()
    fecha_inicio = datetime(hoy.year, hoy.month, 1)  # Día 1 del mes actual
    
    # Último día del mes siguiente
    fecha_fin = datetime(hoy.year, hoy.month, 1) + timedelta(days=62)
    fecha_fin = fecha_fin.replace(day=1) - timedelta(days=1)
    
    print(f"Obteniendo turnos desde {fecha_inicio.strftime('%d/%m/%Y')} hasta {fecha_fin.strftime('%d/%m/%Y')}")
    
    # Obtener turnos
    headers["authorization"] = f"Bearer {token}"
    roster_url = credenciales['roster_url']
    
    # Asegurarse de que la URL del roster termine con el número de empleado
    if not roster_url.endswith(credenciales['sita_username']):
        roster_url = f"{roster_url.rstrip('/')}/{credenciales['sita_username']}"
    
    params = {
        "fromDate": fecha_inicio.isoformat(),
        "toDate": fecha_fin.isoformat()
    }
    
    print(f"URL de roster a usar: {roster_url}")
    
    response = requests.get(roster_url, headers=headers, params=params, timeout=30)
    if response.status_code != 200:
        error_msg = f"Error al obtener turnos: {response.status_code} - {response.text}"
        print(error_msg)
        raise Exception(error_msg)
    
    print(f"Turnos obtenidos correctamente.")
    return response.json()

def insertar_turnos_en_bd(empleado_id, turnos_json):
    """Inserta o actualiza los turnos en la base de datos usando execute_query"""
    if not turnos_json:
        return 0

    actualizados = 0

    for turno in turnos_json:
        # Normalizar la fecha
        dia_iso = turno["date"]
        if dia_iso.endswith("Z"):
            dia_iso = dia_iso[:-1]
        dia = datetime.fromisoformat(dia_iso).strftime("%Y-%m-%d %H:%M:%S")

        # Procesar turnos
        shifts = turno.get("shifts", [])
        sorted_shifts = sorted(
            shifts,
            key=lambda x: (
                x.get("start", ""),
                x.get("end", ""),
                x.get("roleCode", ""),
                x.get("workingArea", "")
            )
        )

        if not sorted_shifts:
            # Desactivar todos los turnos activos para ese día
            execute_query(
                """
                UPDATE turnos_empleado
                SET activo = 0
                WHERE dia = %s AND empleado_id = %s AND activo = 1
                """,
                (dia, empleado_id),
                commit=True
            )
            # Insertar registro de día libre
            execute_query(
                """
                INSERT INTO turnos_empleado (empleado_id, dia, turno, activo, google_event_ids)
                VALUES (%s, %s, NULL, 1, NULL)
                """,
                (empleado_id, dia),
                commit=True
            )
            actualizados += 1
            continue

        shifts_str = json.dumps(sorted_shifts, ensure_ascii=False, sort_keys=True)

        # Verificar si ya existe un turno activo para este usuario y día
        active_turno = execute_query(
            """
            SELECT id, turno, activo, google_event_ids
            FROM turnos_empleado
            WHERE dia = %s AND empleado_id = %s AND activo = 1
            """,
            (dia, empleado_id),
            fetchone=True
        )

        if active_turno:
            # Si ya existe un turno activo, comparar
            if active_turno["turno"] is not None and json.dumps(json.loads(active_turno["turno"]), ensure_ascii=False, sort_keys=True) == shifts_str:
                # Turno idéntico, no hacer nada
                continue
            # Si son diferentes, desactivar todos los turnos activos
            execute_query(
                """
                UPDATE turnos_empleado
                SET activo = 0
                WHERE dia = %s AND empleado_id = %s AND activo = 1
                """,
                (dia, empleado_id),
                commit=True
            )

        # Insertar el nuevo turno
        execute_query(
            """
            INSERT INTO turnos_empleado (empleado_id, dia, turno, activo, google_event_ids)
            VALUES (%s, %s, %s, 1, NULL)
            """,
            (empleado_id, dia, shifts_str),
            commit=True
        )
        actualizados += 1

    return actualizados
