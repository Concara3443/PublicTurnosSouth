import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class CredentialEncryptor:
    def __init__(self, app=None):
        self.key = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa el encriptador con la clave de la aplicación"""
        # Obtener clave de encriptación de variables de entorno o generar una
        encryption_key = os.environ.get('ENCRYPTION_KEY')
        if not encryption_key:
            # Si no existe, usar una derivación del SECRET_KEY de Flask
            salt = os.environ.get('ENCRYPTION_SALT', 'TurnosIbeSalt').encode()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            encryption_key = base64.urlsafe_b64encode(
                kdf.derive(app.config['SECRET_KEY'].encode())
            )
        
        # Crear la clave Fernet para encriptación/desencriptación
        self.key = encryption_key
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data):
        """Encripta datos sensibles"""
        if not isinstance(data, bytes):
            data = str(data).encode('utf-8')
        return self.cipher.encrypt(data).decode('utf-8')
    
    def decrypt(self, token):
        """Desencripta datos sensibles"""
        if not isinstance(token, bytes):
            token = str(token).encode('utf-8')
        return self.cipher.decrypt(token).decode('utf-8')