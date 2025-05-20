from database import get_db_connection, execute_query
from cryptography.fernet import Fernet
import os
import base64

class CredencialSita:
    """Clase para manejar las credenciales de SITA de los usuarios"""
    
    @staticmethod
    def obtener_por_empleado(empleado_id):
        """Obtiene las credenciales de SITA de un empleado por su ID"""
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
                    print(f"Error al desencriptar: {e}")
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
        
        return None
    
    @staticmethod
    def guardar(empleado_id, sita_username, sita_password, site_id, cvation_tenantid, roster_url):
        """Guarda o actualiza las credenciales de SITA de un empleado"""
        # Obtener o generar clave de encriptación
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            encryption_key = Fernet.generate_key().decode()
            print(f"ADVERTENCIA: No se encontró ENCRYPTION_KEY. Se generó una nueva: {encryption_key}")
        
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
        
        return True
    
    @staticmethod
    def validar_credenciales(sita_username, sita_password, site_id, cvation_tenantid, roster_url):
        """Valida las credenciales SITA antes de guardarlas"""
        import requests
        
        # Cabeceras para la solicitud
        headers = {
            "accept": "application/json",
            "accept-language": "es-ES,es;q=0.9",
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
        
        try:
            # Realizar solicitud de autenticación
            response = requests.post(auth_url, headers=headers, json=payload, timeout=15)
            
            # Verificar si la autenticación fue exitosa
            if response.status_code == 200:
                data = response.json()
                if "sessionToken" in data:
                    return True, "Credenciales válidas"
            
            # Si llegamos aquí, hubo un error
            return False, f"Error de autenticación: {response.status_code} - {response.text}"
        
        except Exception as e:
            return False, f"Error al validar credenciales: {str(e)}"