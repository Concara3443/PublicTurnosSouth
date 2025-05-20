import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime, date, timedelta
import json
import time
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def get_db_connection(max_retries=3, retry_delay=2):
    """
    Establece conexión con la base de datos con reintentos
    """
    for attempt in range(max_retries):
        try:
            conn = pymysql.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                cursorclass=DictCursor,
                connect_timeout=int(os.getenv("DB_CONNECTION_TIMEOUT", 30)),
                read_timeout=int(os.getenv("DB_READ_TIMEOUT", 30)),
                write_timeout=int(os.getenv("DB_WRITE_TIMEOUT", 30)),
                autocommit=False,
                charset='utf8mb4'
            )
            # Probar la conexión con una consulta simple
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return conn
        except pymysql.OperationalError as e:
            error_code = e.args[0]
            if error_code in (2002, 2003, 2006, 2013) and attempt < max_retries - 1:
                print(f"Error de conexión a la base de datos (intento {attempt+1}/{max_retries}): {e}")
                print(f"Reintentando en {retry_delay} segundos...")
                time.sleep(retry_delay)
            else:
                # Si se agotan los reintentos o es otro tipo de error, relanzarlo
                raise
        except Exception as e:
            print(f"Error inesperado al conectar a la base de datos: {e}")
            raise
            
# Decorador para manejo de errores en consultas a la base de datos
def db_error_handler(max_retries=3, retry_delay=2):
    """Decorador para manejar errores de conexión en funciones que usan la base de datos"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except pymysql.OperationalError as e:
                    error_code = e.args[0]
                    if error_code in (2002, 2003, 2006, 2013) and attempt < max_retries - 1:
                        print(f"Error de BD en {func.__name__} (intento {attempt+1}/{max_retries}): {e}")
                        print(f"Reintentando en {retry_delay} segundos...")
                        time.sleep(retry_delay)
                    else:
                        raise
                except Exception as e:
                    print(f"Error inesperado en {func.__name__}: {e}")
                    raise
        return wrapper
    return decorator

# Función segura para ejecutar consultas
def execute_query(query, params=None, fetchone=False, commit=False):
    """Ejecuta una consulta de forma segura con manejo de errores y reconexión"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            
            if fetchone:
                result = cursor.fetchone()
            else:
                result = cursor.fetchall()
                
            if commit:
                conn.commit()
                
            return result
    except Exception as e:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# Mantener el resto de funciones existentes pero actualizarlas para usar el nuevo sistema
def get_turnos_by_month(year, month):
    """
    Obtiene todos los turnos en un mes, ajustando para incluir semanas completas
    """
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year+1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month+1, 1) - timedelta(days=1)

    # Ajustar para incluir semanas completas
    first_weekday = start_date.weekday()  # Día de la semana del primer día del mes (0=Lunes, 6=Domingo)
    last_weekday = end_date.weekday()  # Día de la semana del último día del mes (0=Lunes, 6=Domingo)
    adjusted_start_date = start_date - timedelta(days=first_weekday)  # Retroceder al lunes anterior
    adjusted_end_date = end_date + timedelta(days=(6 - last_weekday))  # Avanzar al domingo siguiente

    query = """
        SELECT id, dia, turno
        FROM turnos
        WHERE dia >= %s AND dia <= %s AND activo=1
    """
    params = (adjusted_start_date.strftime("%Y-%m-%d"), adjusted_end_date.strftime("%Y-%m-%d"))
    
    return execute_query(query, params)

def get_turnos_by_day(day_str):
    """
    Obtiene los turnos de un día específico
    """
    query = """
        SELECT id, dia, turno 
        FROM turnos 
        WHERE dia = %s AND activo=1
    """
    return execute_query(query, (day_str,))

def get_turnos_by_range(start_date, end_date):
    """
    Obtiene los turnos en un rango de fechas específico
    """
    # Convertir fechas a string si son objetos date
    if isinstance(start_date, date):
        start_str = start_date.strftime("%Y-%m-%d")
    else:
        start_str = start_date
        
    if isinstance(end_date, date):
        end_str = end_date.strftime("%Y-%m-%d")
    else:
        end_str = end_date

    query = """
        SELECT id, dia, turno
        FROM turnos
        WHERE dia >= %s AND dia <= %s AND activo=1
    """
    return execute_query(query, (start_str, end_str))

def parse_turno_json(turno_data):
    """
    Parsea el JSON de un turno y devuelve una lista de shifts
    """
    if turno_data is None:
        return []
    elif isinstance(turno_data, str):
        try:
            shift_list = json.loads(turno_data)
            if not isinstance(shift_list, list):
                return []
            return shift_list
        except Exception as e:
            print(f"Error decodificando JSON de turno: {e}")
            return []
    elif isinstance(turno_data, list):
        return turno_data
    else:
        return []
    
# Implementación simple de pool de conexiones
class ConnectionPool:
    def __init__(self, max_connections=10):
        self.max_connections = max_connections
        self.connections = []
        self.in_use = set()
    
    def get_connection(self):
        """Obtiene una conexión del pool o crea una nueva"""
        for i, conn in enumerate(self.connections):
            if i not in self.in_use:
                try:
                    # Verificar que la conexión está activa
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                    
                    # Marcar como en uso
                    self.in_use.add(i)
                    return conn, i
                except:
                    # La conexión está cerrada, crear una nueva
                    self.connections[i] = get_db_connection()
                    self.in_use.add(i)
                    return self.connections[i], i
        
        # Si llegamos aquí, no hay conexiones disponibles
        if len(self.connections) < self.max_connections:
            # Crear una nueva conexión
            conn = get_db_connection()
            self.connections.append(conn)
            idx = len(self.connections) - 1
            self.in_use.add(idx)
            return conn, idx
        
        # Si todas las conexiones están en uso, esperar y reintentar
        time.sleep(0.5)
        return self.get_connection()
    
    def release_connection(self, idx):
        """Libera una conexión para que pueda ser reutilizada"""
        if idx in self.in_use:
            self.in_use.remove(idx)
    
    def close_all(self):
        """Cierra todas las conexiones del pool"""
        for conn in self.connections:
            try:
                conn.close()
            except:
                pass
        self.connections = []
        self.in_use = set()

# Crear un pool global
pool = ConnectionPool()

# Y luego modificar la función execute_query para usar el pool
def execute_query(query, params=None, fetchone=False, commit=False):
    """Ejecuta una consulta de forma segura con manejo de errores y reconexión usando pool"""
    conn = None
    conn_idx = None
    try:
        conn, conn_idx = pool.get_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            
            if fetchone:
                result = cursor.fetchone()
            else:
                result = cursor.fetchall()
                
            if commit:
                conn.commit()
                
            return result
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        raise
    finally:
        if conn_idx is not None:
            pool.release_connection(conn_idx)