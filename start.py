# start.py
#!/usr/bin/env python
import os
import sys
import time
import signal
import subprocess
import logging
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("turnos_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TurnosIbe")

# Cargar variables de entorno
load_dotenv()

# Definir procesos
processes = []

def cleanup(signum, frame):
    """Limpia y cierra todos los procesos al recibir una señal"""
    logger.info("Deteniendo todos los servicios...")
    for proc in processes:
        if proc.poll() is None:  # Si el proceso sigue ejecutándose
            logger.info(f"Terminando proceso {proc.pid}")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Forzando terminación del proceso {proc.pid}")
                proc.kill()
    
    logger.info("Todos los servicios detenidos")
    sys.exit(0)

def check_database(max_retries=3, retry_delay=5):
    """Verifica si la base de datos está configurada para usuarios"""
    import pymysql
    from pymysql.cursors import DictCursor
    import time
    
    db_config = {
        "host": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
        "cursorclass": DictCursor,
        "connect_timeout": 10  # Aumentar el timeout de conexión
    }
    
    for attempt in range(max_retries):
        try:
            conn = pymysql.connect(**db_config)
            with conn.cursor() as cursor:
                # Verificar si existe la tabla empleados
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = 'empleados'
                """, (os.getenv("DB_NAME"),))
                result = cursor.fetchone()
                table_exists = result['count'] > 0
                
                if table_exists:
                    # Verificar si hay algún usuario
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM empleados
                    """)
                    result = cursor.fetchone()
                    has_users = result['count'] > 0
                    
                    if not has_users:
                        logger.warning("No hay usuarios configurados. Debes crear al menos un usuario administrador.")
                        return False
                        
                    conn.close()
                    return True
                else:
                    logger.warning("La tabla 'empleados' no existe. Es necesario ejecutar setup_user_database.py primero.")
                    conn.close()
                    return False
        except pymysql.OperationalError as e:
            error_code = e.args[0]
            if error_code in (2003, 2006, 2013):  # Error de conexión
                if attempt < max_retries - 1:
                    logger.warning(f"Error de conexión a la base de datos (intento {attempt+1}/{max_retries}): {e}")
                    logger.info(f"Reintentando en {retry_delay} segundos...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Error al verificar la base de datos después de {max_retries} intentos: {e}")
                    return False
            else:
                logger.error(f"Error al verificar la base de datos: {e}")
                return False
        except Exception as e:
            logger.error(f"Error al verificar la base de datos: {e}")
            return False
    
    return False
def start_services():
    """Inicia todos los servicios del sistema"""
    logger.info("Iniciando servicios TurnosIbe...")
    
    # Verificar que la base de datos esté configurada
    if not check_database(max_retries=3, retry_delay=5):
        logger.error("""
        ==========================================================================
        Error al conectar con la base de datos o la base de datos no está
        configurada correctamente para usuarios.
        
        Asegúrate de que:
        1. El servicio MySQL/MariaDB está funcionando
        2. Las credenciales en el archivo .env son correctas
        3. Has ejecutado: python scripts/setup_user_database.py
        
        Este script creará las tablas necesarias y configurará un usuario admin.
        ==========================================================================
        """)
        return False
    
    # Iniciar proceso de sincronización de calendario
    calendar_process = subprocess.Popen([sys.executable, "calendar/index.py"])
    processes.append(calendar_process)
    logger.info(f"Servicio de calendario iniciado (PID: {calendar_process.pid})")
    
    # Iniciar servidor web
    web_process = subprocess.Popen([sys.executable, "web/app.py"])
    processes.append(web_process)
    logger.info(f"Servidor web iniciado (PID: {web_process.pid})")
    
    # Configurar puerto de la aplicación web
    web_port = os.getenv("APP_PORT", "5680")
    logger.info(f"Servidor web disponible en: http://localhost:{web_port}")
    
    # Mostrar mensaje de configuración completa
    logger.info("""
    ==========================================================================
    ¡Sistema TurnosIbe iniciado correctamente!
    
    Aplicación web: http://localhost:{port}
    Servicio de sincronización: Activo
    
    Para detener los servicios, presiona Ctrl+C
    ==========================================================================
    """.format(port=web_port))
    
    return True

def main():
    """Función principal"""
    # Registrar manejadores de señales para limpieza al salir
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    # Intentar iniciar servicios con reintentos
    max_retries = 3
    retry_delay = 10
    
    for attempt in range(max_retries):
        if start_services():
            # Servicios iniciados correctamente
            break
        elif attempt < max_retries - 1:
            logger.info(f"Reintentando iniciar servicios en {retry_delay} segundos...")
            time.sleep(retry_delay)
        else:
            logger.error("No se pudieron iniciar los servicios después de varios intentos.")
            return
    
    # Mantener el script en ejecución
    try:
        while True:
            # Verificar que todos los procesos sigan en ejecución
            for proc in processes[:]:
                if proc.poll() is not None:  # El proceso terminó
                    exit_code = proc.returncode
                    logger.error(f"Proceso terminado inesperadamente con código {exit_code}")
                    processes.remove(proc)
                    
                    # Reiniciar el proceso
                    if "calendar/index.py" in proc.args:
                        logger.info("Reiniciando servicio de calendario...")
                        new_proc = subprocess.Popen([sys.executable, "calendar/index.py"])
                        processes.append(new_proc)
                        logger.info(f"Servicio de calendario reiniciado (PID: {new_proc.pid})")
                    elif "web/app.py" in proc.args:
                        logger.info("Reiniciando servidor web...")
                        new_proc = subprocess.Popen([sys.executable, "web/app.py"])
                        processes.append(new_proc)
                        logger.info(f"Servidor web reiniciado (PID: {new_proc.pid})")
            
            # Esperar antes de la siguiente verificación
            time.sleep(5)
    except KeyboardInterrupt:
        # Esta excepción se captura a través del manejador de señales
        pass
    
if __name__ == "__main__":
    main()