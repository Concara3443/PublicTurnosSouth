from datetime import datetime, timedelta
import os
import requests
import time
import json
import pymysql
import schedule
import logging
from colorama import Fore, Style, init
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("turnos_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TurnosManager")

# Cargar variables de entorno
load_dotenv()
init(autoreset=True)

# Constantes
SCOPES = [os.getenv("GOOGLE_CALENDAR_SCOPES")]
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")
ACCUWEATHER_API_KEY = os.getenv("ACCUWEATHER_API_KEY")
AUTH_URL = os.getenv("AUTH_URL")
ROSTER_URL = os.getenv("ROSTER_URL")
SITA_USERNAME = os.getenv("SITA_USERNAME")
SITA_PASSWORD = os.getenv("SITA_PASSWORD")
SITE_ID = os.getenv("SITE_ID")
CVATION_TENANTID = os.getenv("CVATION_TENANTID")
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "cursorclass": pymysql.cursors.DictCursor
}

class TurnosManager:
    def __init__(self):
        """Inicializa el gestor de turnos"""
        self.check_environment_vars()
    
    def check_environment_vars(self):
        """Verifica que todas las variables de entorno estén configuradas"""
        required_vars = ["GOOGLE_CALENDAR_SCOPES", "GOOGLE_CALENDAR_ID", "ACCUWEATHER_API_KEY", 
                         "AUTH_URL", "ROSTER_URL", "SITA_USERNAME", "SITA_PASSWORD", 
                         "SITE_ID", "CVATION_TENANTID", "DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME",
                         "NTFY_TOPIC"]
        
        for var in required_vars:
            if not os.getenv(var):
                logger.warning(f"Variable de entorno {var} no configurada")
    
    def get_db_connection(self):
        """Establece una conexión a la base de datos"""
        try:
            conn = pymysql.connect(**DB_CONFIG)
            return conn
        except Exception as e:
            logger.error(f"Error al conectar con la base de datos: {e}")
            return None
    
    def normalize_date(self, date_str):
        """Normaliza una fecha en formato ISO a formato MySQL"""
        if date_str.endswith("Z"):
            date_str = date_str[:-1]
        return datetime.fromisoformat(date_str).strftime("%Y-%m-%d %H:%M:%S")
    
    def ntfy_send(self, message, title=None, priority=3, tags=None, click=None, attach=None):
        """Envía una notificación a través de la API de ntfy."""
        url = "https://ntfy.sh/"
        headers = {"Content-Type": "application/json"}
        payload = {
            "topic": os.getenv("NTFY_TOPIC"),
            "message": message,
        }
        
        if title:
            payload["title"] = title
        if tags:
            payload["tags"] = tags
        if priority:
            payload["priority"] = priority
        if click:
            payload["click"] = click
        if attach:
            payload["attach"] = attach
            
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            if response.status_code == 200:
                logger.info("Notificación enviada correctamente.")
            else:
                logger.error(f"Error al enviar la notificación: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            logger.error(f"Error al conectar con la API de ntfy: {e}")
    
    def get_google_credentials(self):
        """Devuelve las credenciales de Google para Calendar."""
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        return creds
    
    def create_calendar_event(self, event_start, event_end, summary="Trabajo", location="Terminal T1"):
        """Crea un evento en Google Calendar."""
        creds = self.get_google_credentials()
        if not creds:
            logger.error("No se pudieron obtener credenciales para Google Calendar")
            return None

        try:
            # Ajustar fecha/hora
            if event_start.endswith("Z"):
                event_start = event_start[:-1]
            if event_end.endswith("Z"):
                event_end = event_end[:-1]

            event_start_dt = datetime.fromisoformat(event_start)
            event_end_dt = datetime.fromisoformat(event_end)

            # Reconvertir a ISO
            event_start = event_start_dt.isoformat()
            event_end = event_end_dt.isoformat()

            service = build("calendar", "v3", credentials=creds)
            event_body = {
                "summary": "Trabajo",
                "location": "Terminal T1",
                "description": f"Summary: {summary}\nLocation: {location}",
                "start": {"dateTime": event_start, "timeZone": "Europe/Madrid"},
                "end": {"dateTime": event_end, "timeZone": "Europe/Madrid"},
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 24 * 60},
                    ],
                },
            }
            event = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
            logger.info(f"Evento creado con ID: {event.get('id')}")
            return event.get("id")
        except HttpError as error:
            logger.error(f"Ocurrió un error al crear el evento: {error}")
            return None
    
    def delete_calendar_event(self, event_id):
        """Elimina un evento de Google Calendar por su ID."""
        if not event_id:
            return
            
        creds = self.get_google_credentials()
        if not creds:
            logger.error("No se pudieron obtener credenciales para Google Calendar")
            return
            
        try:
            service = build("calendar", "v3", credentials=creds)
            service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
            logger.info(f"Evento {event_id} eliminado de Google Calendar.")
        except HttpError as error:
            logger.error(f"No se pudo eliminar el evento {event_id}: {error}")
    
    def delete_calendar_events(self, event_ids_json):
        """Elimina todos los eventos listados en event_ids_json."""
        if not event_ids_json:
            return
            
        try:
            event_ids = json.loads(event_ids_json)
            for eid in event_ids:
                self.delete_calendar_event(eid)
        except (TypeError, json.JSONDecodeError) as e:
            logger.error(f"Error al procesar los IDs de eventos: {e}")
    
    def get_weather_forecast(self, start_time, end_time):
        """Obtiene la probabilidad de precipitación para un rango de tiempo."""
        location_key = 304479  # Ejemplo de clave de ubicación
        url = f"https://dataservice.accuweather.com/forecasts/v1/hourly/12hour/{location_key}"
        params = {"apikey": ACCUWEATHER_API_KEY, "language": "es", "details": "true", "metric": "true"}
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                start_time_dt = datetime.fromisoformat(start_time)
                end_time_dt = datetime.fromisoformat(end_time)
                min_time = start_time_dt - timedelta(hours=2)
                max_time = end_time_dt + timedelta(hours=2)
                
                precipitation_data = []
                for entry in data:
                    entry_time = datetime.strptime(entry["DateTime"], "%Y-%m-%dT%H:%M:%S%z")
                    if min_time <= entry_time <= max_time:
                        precipitation_data.append((entry_time, entry["PrecipitationProbability"]))
                
                return precipitation_data
            else:
                logger.error(f"Error al obtener pronóstico: {response.status_code}, {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error al obtener pronóstico del tiempo: {e}")
            return None

    def get_turnos(self, from_date, to_date, sita_username, sita_password, site_id, cvation_tenantid, roster_url, max_retries=5, retry_delay=10):
        """Obtiene los turnos del servicio remoto para un usuario específico."""
        headers = {
            "accept": "application/json",
            "accept-language": "es-ES,es;q=0.9,ca;q=0.8",
            "authorization": "Bearer",
            "content-type": "application/json",
            "cvation_tenantid": cvation_tenantid,
            "origin": "https://sitaess-prod-frontdoor.azurefd.net",
            "priority": "u=1, i",
            "referer": "https://sitaess-prod-frontdoor.azurefd.net/...",
            "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ..."
        }

        payload = {
            "username": sita_username,
            "password": sita_password,
            "siteId": site_id
        }

        # URL de autenticación
        auth_url = "https://sitaess-prod-frontdoor.azurefd.net/api/v1/auth/signin"
        
        # Autenticación
        token = None
        for attempt in range(max_retries):
            try:
                resp = requests.post(auth_url, headers=headers, json=payload)
                if resp.status_code == 200:
                    token = resp.json().get("sessionToken")
                    logger.info(f"Autenticación exitosa para usuario {sita_username}.")
                    break
                else:
                    logger.warning(f"Error autenticando usuario {sita_username} (intento {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"No se pudo autenticar usuario {sita_username} tras varios intentos.")
                        return None
            except Exception as e:
                logger.error(f"Error en la autenticación para usuario {sita_username}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    return None

        if not token:
            return None

        # Obtener datos de turnos
        headers["authorization"] = f"Bearer {token}"
        params = {"fromDate": from_date, "toDate": to_date}

        # Si la URL del roster no termina con el número de empleado, añadirlo
        if not roster_url.endswith(sita_username):
            roster_url = f"{roster_url.rstrip('/')}/{sita_username}"

        for attempt in range(max_retries):
            try:
                resp = requests.get(roster_url, headers=headers, params=params)
                if resp.status_code == 200:
                    logger.info(f"Turnos obtenidos correctamente para usuario {sita_username} en el periodo {from_date} - {to_date}")
                    return resp.json()
                else:
                    logger.warning(f"Error al solicitar datos para usuario {sita_username} (intento {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"No se pudieron obtener los turnos para usuario {sita_username} tras varios intentos.")
                        return None
            except Exception as e:
                logger.error(f"Error al solicitar datos de turnos para usuario {sita_username}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    return None    
    
    def sort_shifts(self, shifts):
        """Ordena los turnos por hora de inicio, fin, rol y área de trabajo."""
        if not shifts:
            return []
            
        return sorted(
            shifts,
            key=lambda x: (
                x.get("start", ""),
                x.get("end", ""),
                x.get("roleCode", ""),
                x.get("workingArea", "")
            )
        )
    
    def deactivate_all_active_turnos_for_day(self, conn, dia):
        """Desactiva todos los turnos activos para un día específico."""
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE turnos 
                SET activo = 0 
                WHERE dia = %s AND activo = 1
                """,
                (dia,)
            )
            updated = cursor.rowcount
            if updated > 0:
                logger.info(f"Se desactivaron {updated} turnos para el día {dia}")
            return updated
    
    def process_free_day(self, conn, dia):
        """Procesa un día libre (sin turnos) en la base de datos."""
        with conn.cursor() as cursor:
            # Verificar si ya existe un día libre activo
            cursor.execute(
                """
                SELECT id, google_event_ids, activo
                FROM turnos
                WHERE dia = %s AND turno IS NULL
                """,
                (dia,)
            )
            free_day = cursor.fetchone()
            
            # Desactivar todos los turnos activos para este día
            self.deactivate_all_active_turnos_for_day(conn, dia)
            
            if free_day:
                if free_day["activo"] == 1:
                    logger.info(f"Ya existe día libre activo para {dia}. No se hace nada.")
                    return True
                else:
                    # Reactivar el día libre existente
                    cursor.execute(
                        """
                        UPDATE turnos
                        SET activo = 1
                        WHERE id = %s
                        """,
                        (free_day["id"],)
                    )
                    logger.info(f"Día libre reactivado para {dia}")
                    return True
            
            # Crear nuevo día libre
            cursor.execute(
                """
                INSERT INTO turnos (dia, turno, activo, google_event_ids)
                VALUES (%s, NULL, 1, NULL)
                """,
                (dia,)
            )
            logger.info(f"Nuevo día libre insertado para {dia}")
            return True
    
    def compare_turnos(self, old_shifts_str, new_shifts_str):
        """Compara dos conjuntos de turnos y devuelve True si son iguales."""
        if not old_shifts_str and not new_shifts_str:
            return True
            
        if not old_shifts_str or not new_shifts_str:
            return False
            
        try:
            old_shifts = json.loads(old_shifts_str)
            new_shifts = json.loads(new_shifts_str)
            
            old_sorted = self.sort_shifts(old_shifts)
            new_sorted = self.sort_shifts(new_shifts)
            
            return json.dumps(old_sorted, ensure_ascii=False, sort_keys=True) == json.dumps(new_sorted, ensure_ascii=False, sort_keys=True)
        except json.JSONDecodeError:
            return False
    
    def insert_into_db(self, turnos_json):
        """Inserta o actualiza turnos en la base de datos."""
        if not turnos_json:
            logger.warning("No hay turnos para procesar")
            return False
            
        conn = self.get_db_connection()
        if not conn:
            return False
            
        try:
            for turno in turnos_json:
                # Normalizar la fecha
                dia_iso = turno["date"]
                dia = self.normalize_date(dia_iso)
                
                # Procesar turnos
                shifts = turno.get("shifts", [])
                sorted_shifts = self.sort_shifts(shifts)
                
                # Si no hay turnos, es un día libre
                if not sorted_shifts:
                    self.process_free_day(conn, dia)
                    continue
                
                # Convertir turnos a formato JSON string
                shifts_str = json.dumps(sorted_shifts, ensure_ascii=False, sort_keys=True)
                
                with conn.cursor() as cursor:
                    # Verificar si ya existe un turno activo
                    cursor.execute(
                        """
                        SELECT id, turno, activo, google_event_ids
                        FROM turnos
                        WHERE dia = %s AND activo = 1
                        """,
                        (dia,)
                    )
                    active_turno = cursor.fetchone()
                    
                    if active_turno:
                        # Si ya existe un turno activo, comparar
                        if active_turno["turno"] is not None and self.compare_turnos(active_turno["turno"], shifts_str):
                            logger.info(f"Turno idéntico ya activo para {dia}. No se hace nada.")
                            continue
                        
                        # Si son diferentes, desactivar todos los turnos activos
                        self.deactivate_all_active_turnos_for_day(conn, dia)
                        
                        # Si había eventos de calendario, eliminarlos
                        if active_turno["google_event_ids"]:
                            self.delete_calendar_events(active_turno["google_event_ids"])
                            
                        # Enviar notificación sobre el cambio
                        old_turno_str = json.dumps(json.loads(active_turno["turno"]), indent=2, ensure_ascii=False) if active_turno["turno"] else "Ninguno"
                        new_turno_str = json.dumps(json.loads(shifts_str), indent=2, ensure_ascii=False)
                        
                        self.ntfy_send(
                            message=f"Cambio de turno detectado para el día {dia}.\n\n"
                                    f"Turno anterior:\n{old_turno_str}\n\n"
                                    f"Nuevo turno:\n{new_turno_str}",
                            title="Cambio de Turno",
                            priority=4,
                            tags=["calendar", "update"],
                            click="https://calendar.google.com/"
                        )
                    
                    # Verificar si existe un turno inactivo idéntico
                    cursor.execute(
                        """
                        SELECT id
                        FROM turnos
                        WHERE dia = %s AND activo = 0 AND turno = %s
                        """,
                        (dia, shifts_str)
                    )
                    inactive_turno = cursor.fetchone()
                    
                    if inactive_turno:
                        # Reactivar el turno inactivo
                        cursor.execute(
                            """
                            UPDATE turnos
                            SET activo = 1
                            WHERE id = %s
                            """,
                            (inactive_turno["id"],)
                        )
                        logger.info(f"Turno reactivado para {dia}")
                    else:
                        # Insertar nuevo turno
                        cursor.execute(
                            """
                            INSERT INTO turnos (dia, turno, activo, google_event_ids)
                            VALUES (%s, %s, 1, NULL)
                            """,
                            (dia, shifts_str)
                        )
                        logger.info(f"Nuevo turno insertado para {dia}")
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error al procesar turnos en la base de datos: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def process_calendar_events(self):
        """Crea eventos en Google Calendar para los turnos activos sin eventos."""
        conn = self.get_db_connection()
        if not conn:
            return False
            
        try:
            with conn.cursor() as cursor:
                # Obtener turnos activos sin eventos de calendario
                cursor.execute(
                    """
                    SELECT id, dia, turno
                    FROM turnos
                    WHERE activo = 1 AND turno IS NOT NULL AND google_event_ids IS NULL
                    """
                )
                turnos_sin_eventos = cursor.fetchall()
                
                for turno in turnos_sin_eventos:
                    try:
                        shifts = json.loads(turno["turno"])
                        event_ids = []
                        
                        for shift in shifts:
                            event_id = self.create_calendar_event(
                                shift["start"], 
                                shift["end"],
                                summary=f"Trabajo - {shift.get('roleCode', 'Sin rol')}",
                                location=shift.get("workingArea", "Terminal T1")
                            )
                            if event_id:
                                event_ids.append(event_id)
                        
                        if event_ids:
                            cursor.execute(
                                """
                                UPDATE turnos
                                SET google_event_ids = %s
                                WHERE id = %s
                                """,
                                (json.dumps(event_ids), turno["id"])
                            )
                            logger.info(f"Eventos de calendario creados para turno del día {turno['dia']}")
                    except json.JSONDecodeError:
                        logger.error(f"Error al procesar turno con ID {turno['id']}")
                        continue
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error al procesar eventos de calendario: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def insertar_turnos_usuario(self, empleado_id, turnos_json):
        """Inserta o actualiza turnos de un usuario específico en la base de datos."""
        if not turnos_json:
            logger.warning(f"No hay turnos para procesar para el usuario {empleado_id}")
            return False
            
        conn = self.get_db_connection()
        if not conn:
            return False
            
        try:
            for turno in turnos_json:
                # Normalizar la fecha
                dia_iso = turno["date"]
                dia = self.normalize_date(dia_iso)
                
                # Procesar turnos
                shifts = turno.get("shifts", [])
                sorted_shifts = self.sort_shifts(shifts)
                
                # Si no hay turnos, es un día libre
                if not sorted_shifts:
                    # Desactivar todos los turnos activos para ese día de ese usuario
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            UPDATE turnos_empleado
                            SET activo = 0
                            WHERE dia = %s AND empleado_id = %s AND activo = 1
                            """,
                            (dia, empleado_id)
                        )
                    
                    # Insertar registro de día libre
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            INSERT INTO turnos_empleado (empleado_id, dia, turno, activo, google_event_ids)
                            VALUES (%s, %s, NULL, 1, NULL)
                            """,
                            (empleado_id, dia)
                        )
                    
                    continue
                
                # Convertir turnos a formato JSON string
                shifts_str = json.dumps(sorted_shifts, ensure_ascii=False, sort_keys=True)
                
                with conn.cursor() as cursor:
                    # Verificar si ya existe un turno activo para este usuario y día
                    cursor.execute(
                        """
                        SELECT id, turno, activo, google_event_ids
                        FROM turnos_empleado
                        WHERE dia = %s AND empleado_id = %s AND activo = 1
                        """,
                        (dia, empleado_id)
                    )
                    active_turno = cursor.fetchone()
                    
                    if active_turno:
                        # Si ya existe un turno activo, comparar
                        if active_turno["turno"] is not None and self.compare_turnos(active_turno["turno"], shifts_str):
                            logger.info(f"Turno idéntico ya activo para {dia} y usuario {empleado_id}. No se hace nada.")
                            continue
                        
                        # Si son diferentes, desactivar todos los turnos activos
                        cursor.execute(
                            """
                            UPDATE turnos_empleado
                            SET activo = 0
                            WHERE dia = %s AND empleado_id = %s AND activo = 1
                            """,
                            (dia, empleado_id)
                        )
                        
                        # Si había eventos de calendario, eliminarlos
                        if active_turno["google_event_ids"]:
                            self.delete_calendar_events(active_turno["google_event_ids"])
                            
                        # Enviar notificación sobre el cambio
                        old_turno_str = json.dumps(json.loads(active_turno["turno"]), indent=2, ensure_ascii=False) if active_turno["turno"] else "Ninguno"
                        new_turno_str = json.dumps(json.loads(shifts_str), indent=2, ensure_ascii=False)
                        
                        self.ntfy_send(
                            message=f"Cambio de turno detectado para el día {dia} y usuario {empleado_id}.\n\n"
                                    f"Turno anterior:\n{old_turno_str}\n\n"
                                    f"Nuevo turno:\n{new_turno_str}",
                            title="Cambio de Turno",
                            priority=4,
                            tags=["calendar", "update"],
                            click="https://calendar.google.com/"
                        )
                    
                    # Insertar el nuevo turno
                    cursor.execute(
                        """
                        INSERT INTO turnos_empleado (empleado_id, dia, turno, activo, google_event_ids)
                        VALUES (%s, %s, %s, 1, NULL)
                        """,
                        (empleado_id, dia, shifts_str)
                    )
                    logger.info(f"Nuevo turno insertado para {dia} y usuario {empleado_id}")
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error al procesar turnos en la base de datos para usuario {empleado_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
            
    def sincronizar_todos_los_usuarios(self):
        """Sincroniza los turnos de todos los usuarios con credenciales configuradas"""
        logger.info("Iniciando sincronización de turnos para todos los usuarios...")
        
        # Obtener todos los usuarios activos con credenciales configuradas
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT e.id, e.numero_empleado, e.nombre_completo, 
                           c.sita_username, c.sita_password_encrypted, 
                           c.site_id, c.cvation_tenantid, c.roster_url
                    FROM empleados e
                    JOIN credenciales_sita c ON e.id = c.empleado_id
                    WHERE e.activo = 1
                """)
                
                usuarios = cursor.fetchall()
                
                if not usuarios:
                    logger.warning("No se encontraron usuarios activos con credenciales configuradas.")
                    return
                
                logger.info(f"Se encontraron {len(usuarios)} usuarios para sincronizar.")
                
                # Procesar cada usuario
                for usuario in usuarios:
                    try:
                        logger.info(f"Sincronizando turnos para: {usuario['nombre_completo']} ({usuario['numero_empleado']})")
                        
                        # Desencriptar contraseña
                        from cryptography.fernet import Fernet
                        import os
                        
                        # Obtener clave de encriptación
                        encryption_key = os.getenv('ENCRYPTION_KEY')
                        if not encryption_key:
                            logger.error("ENCRYPTION_KEY no encontrada en variables de entorno.")
                            continue
                        
                        # Crear cifrador
                        cipher_suite = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
                        
                        # Desencriptar contraseña
                        try:
                            password_encriptada = usuario['sita_password_encrypted']
                            if isinstance(password_encriptada, str):
                                password_encriptada = password_encriptada.encode()
                            
                            sita_password = cipher_suite.decrypt(password_encriptada).decode()
                        except Exception as e:
                            logger.error(f"Error al desencriptar contraseña para usuario {usuario['id']}: {e}")
                            continue
                        
                        # Obtener turnos desde SITA
                        hoy = datetime.now()
                        start_date = hoy
                        
                        # Último día del mes siguiente
                        end_date = datetime(hoy.year, hoy.month, 1) + timedelta(days=62)
                        end_date = end_date.replace(day=1) - timedelta(days=1)
                        
                        start_str = start_date.isoformat()
                        end_str = end_date.isoformat()
                        
                        # Obtener turnos usando las credenciales del usuario
                        turnos = self.get_turnos(
                            from_date=start_str,
                            to_date=end_str,
                            sita_username=usuario['sita_username'],
                            sita_password=sita_password,
                            site_id=usuario['site_id'],
                            cvation_tenantid=usuario['cvation_tenantid'],
                            roster_url=usuario['roster_url']
                        )
                        
                        if not turnos:
                            logger.warning(f"No se encontraron turnos para el usuario {usuario['numero_empleado']}.")
                            continue
                        
                        # Insertar turnos en la base de datos
                        self.insertar_turnos_usuario(usuario['id'], turnos)
                        
                        logger.info(f"Sincronización completada para usuario {usuario['numero_empleado']}.")
                    
                    except Exception as e:
                        logger.error(f"Error al sincronizar turnos para usuario {usuario.get('numero_empleado', 'desconocido')}: {e}")
        except Exception as e:
            logger.error(f"Error al obtener usuarios para sincronización: {e}")
        finally:
            conn.close()
    
    def run_job(self):
        """Ejecuta el trabajo principal de sincronización de turnos."""
        try:
            # Sincronizar turnos para todos los usuarios
            self.sincronizar_todos_los_usuarios()
            
            # Crear eventos en Google Calendar
            self.process_calendar_events()
            
            logger.info("Sincronización completada para todos los usuarios.")
        except Exception as e:
            logger.error(f"Error durante la sincronización: {e}")
            
def setup_database():
    """Configura la base de datos si no existe."""
    conn = pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        cursorclass=pymysql.cursors.DictCursor
    )
    
    try:
        with conn.cursor() as cursor:
            # Crear base de datos si no existe
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {os.getenv('DB_NAME')}")
            cursor.execute(f"USE {os.getenv('DB_NAME')}")
            
            # Crear tabla turnos si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS turnos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    dia DATETIME NOT NULL,
                    turno JSON NULL,
                    activo TINYINT(1) DEFAULT 1,
                    google_event_ids JSON NULL,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_dia (dia),
                    INDEX idx_activo (activo)
                )
            """)
            
            conn.commit()
            logger.info("Base de datos configurada correctamente.")
    except Exception as e:
        logger.error(f"Error al configurar la base de datos: {e}")
    finally:
        conn.close()

def main():
    """Función principal de la aplicación."""
    # Configurar base de datos
    setup_database()
    
    # Crear instancia del gestor de turnos
    manager = TurnosManager()
    
    # Ejecutar trabajo inicial
    logger.info("Ejecutando trabajo inicial...")
    manager.run_job()
    
    # Programar ejecución periódica
    schedule.every(1).hours.do(manager.run_job)
    logger.info("Programador de tareas iniciado. El trabajo se ejecutará cada hora.")
    
    # Bucle principal
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Programa interrumpido por el usuario.")
    except Exception as e:
        logger.error(f"Error inesperado: {e}")

if __name__ == "__main__":
    main()