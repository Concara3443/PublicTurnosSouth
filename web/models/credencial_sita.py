from database import get_db_connection, execute_query
from cryptography.fernet import Fernet
import os
import base64
import requests
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CredencialSita")

class CredencialSita:
    """Clase para manejar las credenciales de SITA de los usuarios"""
    
    @staticmethod
    def obtener_por_empleado(empleado_id):
        """Obtiene las credenciales de SITA de un empleado por su ID"""
        try:
            query = """
                SELECT id, empleado_id, sita_username, sita_password_encrypted,
                       site_id, cvation_tenantid, roster_url, fecha_actualizacion
                FROM credenciales_sita
                WHERE empleado_id = %s
            """
            
            result = execute_query(query, (empleado_id,), fetchone=True)
            
            if result:
                # Desencriptar contraseña
                encryption_key = os.getenv('ENCRYPTION_KEY')
                if encryption_key and result['sita_password_encrypted']:
                    try:
                        cipher_suite = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
                        encrypted_password = result['sita_password_encrypted']
                        
                        if isinstance(encrypted_password, str):
                            encrypted_password = encrypted_password.encode()
                        
                        sita_password = cipher_suite.decrypt(encrypted_password).decode()
                    except Exception as e:
                        logger.error(f"Error al desencriptar: {e}")
                        sita_password = None
                else:
                    sita_password = None
                
                # Devolver diccionario con credenciales
                return {
                    'id': result['id'],
                    'empleado_id': result['empleado_id'],
                    'sita_username': result['sita_username'],
                    'sita_password': sita_password,
                    'sita_password_encrypted': result['sita_password_encrypted'],
                    'site_id': result['site_id'],
                    'cvation_tenantid': result['cvation_tenantid'],
                    'roster_url': result['roster_url'],
                    'fecha_actualizacion': result['fecha_actualizacion']
                }
        except Exception as e:
            logger.error(f"Error al obtener credenciales SITA: {e}")
        
        return None
    
    @staticmethod
    def guardar(empleado_id, sita_username, sita_password, site_id, cvation_tenantid, roster_url, validar=False):
        """
        Guarda o actualiza las credenciales de SITA de un empleado
        
        Args:
            empleado_id: ID del empleado
            sita_username: Nombre de usuario de SITA
            sita_password: Contraseña de SITA
            site_id: ID del sitio
            cvation_tenantid: ID del tenant
            roster_url: URL del roster
            validar: Si es True, valida las credenciales antes de guardar
        
        Returns:
            Tupla (bool, str) con el resultado y mensaje
        """
        try:
            # Si se solicita validación, intentar validar primero
            if validar:
                success, message = CredencialSita.validar_credenciales(
                    sita_username, sita_password, site_id, cvation_tenantid, roster_url
                )
                if not success:
                    return False, message
            
            # Obtener o generar clave de encriptación
            encryption_key = os.getenv('ENCRYPTION_KEY')
            if not encryption_key:
                encryption_key = Fernet.generate_key().decode()
                logger.warning(f"ENCRYPTION_KEY no encontrada. Se ha generado una nueva.")
            
            # Crear cifrador
            cipher_suite = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
            
            # Encriptar contraseña
            encrypted_password = cipher_suite.encrypt(sita_password.encode()).decode()
            
            # Verificar si ya existen credenciales
            query = "SELECT id FROM credenciales_sita WHERE empleado_id = %s"
            existing = execute_query(query, (empleado_id,), fetchone=True)
            
            if existing:
                # Actualizar
                query = """
                    UPDATE credenciales_sita
                    SET sita_username = %s,
                        sita_password_encrypted = %s,
                        site_id = %s,
                        cvation_tenantid = %s,
                        roster_url = %s
                    WHERE empleado_id = %s
                """
                execute_query(query, (sita_username, encrypted_password, site_id, 
                                    cvation_tenantid, roster_url, empleado_id), commit=True)
            else:
                # Crear nuevo
                query = """
                    INSERT INTO credenciales_sita
                    (empleado_id, sita_username, sita_password_encrypted, 
                    site_id, cvation_tenantid, roster_url)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                execute_query(query, (empleado_id, sita_username, encrypted_password,
                                    site_id, cvation_tenantid, roster_url), commit=True)
            
            return True, "Credenciales guardadas correctamente"
        except Exception as e:
            logger.error(f"Error al guardar credenciales: {e}")
            return False, f"Error al guardar credenciales: {str(e)}"
    
    @staticmethod
    def validar_credenciales(sita_username, sita_password, site_id, cvation_tenantid, roster_url, timeout=30):
        """
        Valida las credenciales SITA intentando realizar una autenticación
        
        Args:
            sita_username: Nombre de usuario de SITA
            sita_password: Contraseña de SITA
            site_id: ID del sitio
            cvation_tenantid: ID del tenant
            roster_url: URL del roster
            timeout: Tiempo máximo de espera en segundos
            
        Returns:
            Tupla (bool, str) con el resultado y mensaje
        """
        try:
            # Validar parámetros básicos
            if not all([sita_username, sita_password, site_id, cvation_tenantid, roster_url]):
                return False, "Todos los campos son obligatorios"
            
            # Cabeceras para la solicitud
            headers = {
                "accept": "application/json",
                "accept-language": "es-ES,es;q=0.9",
                "authorization": "Bearer",
                "content-type": "application/json",
                "cvation_tenantid": cvation_tenantid,
                "origin": "https://sitaess-prod-frontdoor.azurefd.net",
                "referer": "https://sitaess-prod-frontdoor.azurefd.net/",
                "sec-ch-ua": '"Chromium";v="116", "Not:A-Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            # Datos de autenticación
            payload = {
                "username": sita_username,
                "password": sita_password,
                "siteId": site_id
            }

            # URL de autenticación
            auth_url = "https://sitaess-prod-frontdoor.azurefd.net/api/v1/auth/signin"
            
            logger.info(f"Intentando validar credenciales para usuario: {sita_username}")
            
            try:
                # Realizar solicitud de autenticación con timeout ampliado
                response = requests.post(auth_url, headers=headers, json=payload, timeout=timeout)
                
                # Verificar si la autenticación fue exitosa
                if response.status_code == 200:
                    data = response.json()
                    if "sessionToken" in data:
                        logger.info(f"Credenciales validadas correctamente para usuario: {sita_username}")
                        return True, "Credenciales válidas"
                
                # Si llegamos aquí, hubo un error
                logger.warning(f"Error de autenticación: {response.status_code} - {response.text}")
                return False, f"Error de autenticación: {response.status_code} - {response.text}"
            
            except requests.exceptions.ConnectTimeout:
                logger.warning(f"Timeout al conectar con SITA")
                return False, "Tiempo de espera agotado al conectar con SITA. El servidor podría estar ocupado."
            
            except requests.exceptions.ReadTimeout:
                logger.warning(f"Timeout al leer respuesta de SITA")
                return False, "Tiempo de espera agotado al esperar respuesta de SITA. Intente de nuevo más tarde."
            
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Error de conexión: {e}")
                return False, "No se pudo conectar con el servidor SITA. Verifique su conexión a Internet."
            
            except requests.exceptions.RequestException as e:
                logger.warning(f"Error en la solicitud: {e}")
                return False, f"Error al validar credenciales: {str(e)}"
        
        except Exception as e:
            logger.error(f"Error inesperado al validar credenciales: {e}")
            return False, f"Error inesperado al validar credenciales: {str(e)}"