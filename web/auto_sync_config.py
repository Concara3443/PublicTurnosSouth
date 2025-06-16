# web/auto_sync_config.py
"""
Configuración del sistema de sincronización automática
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class AutoSyncConfig:
    """Configuración centralizada para el auto-sync"""
    
    # ============================================
    # CONFIGURACIÓN DE CICLOS
    # ============================================
    
    # Tiempo de espera entre ciclos completos (en segundos)
    # Por defecto: 1 hora = 3600 segundos
    CYCLE_INTERVAL = int(os.getenv('AUTO_SYNC_CYCLE_INTERVAL', 3600))
    
    # Tiempo de espera entre usuarios (en segundos)
    # Por defecto: 5 segundos
    USER_DELAY = int(os.getenv('AUTO_SYNC_USER_DELAY', 5))
    
    # ============================================
    # CONFIGURACIÓN DE REINTENTOS
    # ============================================
    
    # Número máximo de reintentos para timeouts
    MAX_RETRIES = int(os.getenv('AUTO_SYNC_MAX_RETRIES', 5))
    
    # Tiempo de espera entre reintentos (en segundos)
    RETRY_DELAY = int(os.getenv('AUTO_SYNC_RETRY_DELAY', 30))
    
    # Timeout para requests HTTP (en segundos)
    HTTP_TIMEOUT = int(os.getenv('AUTO_SYNC_HTTP_TIMEOUT', 30))
    
    # ============================================
    # CONFIGURACIÓN DE LOGS
    # ============================================
    
    # Archivo de log principal
    LOG_FILE = os.getenv('AUTO_SYNC_LOG_FILE', 'auto_sync.log')
    
    # Nivel de logging
    LOG_LEVEL = os.getenv('AUTO_SYNC_LOG_LEVEL', 'INFO')
    
    # Rotación de logs (tamaño máximo en bytes)
    LOG_MAX_BYTES = int(os.getenv('AUTO_SYNC_LOG_MAX_BYTES', 10485760))  # 10MB
    
    # Número de archivos de backup para logs
    LOG_BACKUP_COUNT = int(os.getenv('AUTO_SYNC_LOG_BACKUP_COUNT', 5))
    
    # ============================================
    # CONFIGURACIÓN DE RENDIMIENTO
    # ============================================
    
    # Tiempo máximo para completar un ciclo antes de mostrar advertencia (en segundos)
    MAX_CYCLE_DURATION = int(os.getenv('AUTO_SYNC_MAX_CYCLE_DURATION', 1800))  # 30 minutos
    
    # Número máximo de usuarios a procesar en un ciclo
    # (0 = sin límite)
    MAX_USERS_PER_CYCLE = int(os.getenv('AUTO_SYNC_MAX_USERS_PER_CYCLE', 0))
    
    # ============================================
    # CONFIGURACIÓN DE NOTIFICACIONES
    # ============================================
    
    # Habilitar notificaciones por email en caso de errores críticos
    EMAIL_NOTIFICATIONS = os.getenv('AUTO_SYNC_EMAIL_NOTIFICATIONS', 'false').lower() == 'true'
    
    # Email del administrador para notificaciones
    ADMIN_EMAIL = os.getenv('AUTO_SYNC_ADMIN_EMAIL', '')
    
    # Número de errores consecutivos antes de enviar notificación
    ERROR_THRESHOLD = int(os.getenv('AUTO_SYNC_ERROR_THRESHOLD', 10))
    
    # ============================================
    # CONFIGURACIÓN DE FILTROS DE USUARIOS
    # ============================================
    
    # Solo sincronizar usuarios que se hayan conectado en los últimos N días
    # (0 = sincronizar todos los usuarios activos)
    LAST_LOGIN_DAYS = int(os.getenv('AUTO_SYNC_LAST_LOGIN_DAYS', 0))
    
    # Excluir usuarios específicos por número de empleado (separados por comas)
    EXCLUDED_USERS = [
        user.strip() 
        for user in os.getenv('AUTO_SYNC_EXCLUDED_USERS', '').split(',') 
        if user.strip()
    ]
    
    # ============================================
    # CONFIGURACIÓN DE FECHAS DE SINCRONIZACIÓN
    # ============================================
    
    # Número de días hacia atrás para sincronizar
    DAYS_BACK = int(os.getenv('AUTO_SYNC_DAYS_BACK', 30))
    
    # Número de días hacia adelante para sincronizar
    DAYS_FORWARD = int(os.getenv('AUTO_SYNC_DAYS_FORWARD', 60))
    
    # ============================================
    # MÉTODOS DE UTILIDAD
    # ============================================
    
    @classmethod
    def get_config_summary(cls):
        """Devuelve un resumen de la configuración actual"""
        return {
            'cycle_interval_minutes': cls.CYCLE_INTERVAL // 60,
            'user_delay_seconds': cls.USER_DELAY,
            'max_retries': cls.MAX_RETRIES,
            'retry_delay_seconds': cls.RETRY_DELAY,
            'http_timeout_seconds': cls.HTTP_TIMEOUT,
            'log_file': cls.LOG_FILE,
            'log_level': cls.LOG_LEVEL,
            'max_users_per_cycle': cls.MAX_USERS_PER_CYCLE if cls.MAX_USERS_PER_CYCLE > 0 else 'Sin límite',
            'email_notifications': cls.EMAIL_NOTIFICATIONS,
            'excluded_users_count': len(cls.EXCLUDED_USERS),
            'sync_range': f"{cls.DAYS_BACK} días atrás a {cls.DAYS_FORWARD} días adelante"
        }
    
    @classmethod
    def validate_config(cls):
        """Valida la configuración y devuelve una lista de advertencias/errores"""
        warnings = []
        errors = []
        
        # Validar intervalos
        if cls.CYCLE_INTERVAL < 300:  # Menos de 5 minutos
            warnings.append(f"Intervalo de ciclo muy corto: {cls.CYCLE_INTERVAL}s (mínimo recomendado: 300s)")
        
        if cls.USER_DELAY < 1:
            warnings.append(f"Delay entre usuarios muy corto: {cls.USER_DELAY}s (mínimo recomendado: 1s)")
        
        # Validar reintentos
        if cls.MAX_RETRIES > 10:
            warnings.append(f"Demasiados reintentos: {cls.MAX_RETRIES} (máximo recomendado: 10)")
        
        if cls.RETRY_DELAY < 5:
            warnings.append(f"Delay de reintento muy corto: {cls.RETRY_DELAY}s (mínimo recomendado: 5s)")
        
        # Validar timeouts
        if cls.HTTP_TIMEOUT < 10:
            warnings.append(f"Timeout HTTP muy corto: {cls.HTTP_TIMEOUT}s (mínimo recomendado: 10s)")
        
        # Validar notificaciones por email
        if cls.EMAIL_NOTIFICATIONS and not cls.ADMIN_EMAIL:
            errors.append("Email de notificaciones habilitado pero no se especificó ADMIN_EMAIL")
        
        # Validar rangos de fechas
        if cls.DAYS_BACK < 0:
            errors.append(f"DAYS_BACK no puede ser negativo: {cls.DAYS_BACK}")
        
        if cls.DAYS_FORWARD < 0:
            errors.append(f"DAYS_FORWARD no puede ser negativo: {cls.DAYS_FORWARD}")
        
        return {
            'warnings': warnings,
            'errors': errors,
            'is_valid': len(errors) == 0
        }

# ============================================
# EJEMPLO DE ARCHIVO .env PARA AUTO-SYNC
# ============================================

ENV_EXAMPLE = """
# Configuración de sincronización automática

# Intervalo entre ciclos completos (en segundos)
# 3600 = 1 hora, 1800 = 30 minutos, 7200 = 2 horas
AUTO_SYNC_CYCLE_INTERVAL=3600

# Delay entre usuarios (en segundos)
AUTO_SYNC_USER_DELAY=5

# Configuración de reintentos
AUTO_SYNC_MAX_RETRIES=5
AUTO_SYNC_RETRY_DELAY=30
AUTO_SYNC_HTTP_TIMEOUT=30

# Configuración de logs
AUTO_SYNC_LOG_FILE=auto_sync.log
AUTO_SYNC_LOG_LEVEL=INFO
AUTO_SYNC_LOG_MAX_BYTES=10485760
AUTO_SYNC_LOG_BACKUP_COUNT=5

# Límites de rendimiento
AUTO_SYNC_MAX_CYCLE_DURATION=1800
AUTO_SYNC_MAX_USERS_PER_CYCLE=0

# Notificaciones por email
AUTO_SYNC_EMAIL_NOTIFICATIONS=false
AUTO_SYNC_ADMIN_EMAIL=admin@tuempresa.com
AUTO_SYNC_ERROR_THRESHOLD=10

# Filtros de usuarios
AUTO_SYNC_LAST_LOGIN_DAYS=0
AUTO_SYNC_EXCLUDED_USERS=012345,067890

# Rango de fechas para sincronizar
AUTO_SYNC_DAYS_BACK=30
AUTO_SYNC_DAYS_FORWARD=60
"""

if __name__ == "__main__":
    # Mostrar configuración actual
    print("=== CONFIGURACIÓN ACTUAL DE AUTO-SYNC ===")
    config = AutoSyncConfig.get_config_summary()
    for key, value in config.items():
        print(f"{key}: {value}")
    
    print("\n=== VALIDACIÓN DE CONFIGURACIÓN ===")
    validation = AutoSyncConfig.validate_config()
    
    if validation['warnings']:
        print("⚠️ ADVERTENCIAS:")
        for warning in validation['warnings']:
            print(f"  - {warning}")
    
    if validation['errors']:
        print("❌ ERRORES:")
        for error in validation['errors']:
            print(f"  - {error}")
    
    if validation['is_valid']:
        print("✅ Configuración válida")
    else:
        print("❌ Configuración inválida - corrige los errores antes de continuar")
        
    print(f"\n=== EJEMPLO DE ARCHIVO .env ===")
    print(ENV_EXAMPLE)