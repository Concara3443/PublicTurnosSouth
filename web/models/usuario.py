from flask_login import UserMixin
import bcrypt
from datetime import datetime
from database import execute_query, get_db_connection, db_error_handler

class Usuario(UserMixin):
    """Clase para representar un usuario del sistema"""
    
    def __init__(self, id=None, numero_empleado=None, nombre_completo=None,
                 email=None, password_hash=None, fecha_creacion=None,
                 ultimo_acceso=None, activo=True, es_admin=False, es_demo=False,
                 vinculado_a_empleado_id=None):
        self.id = id
        self.numero_empleado = numero_empleado
        self.nombre_completo = nombre_completo
        self.email = email
        self.password_hash = password_hash
        self.fecha_creacion = fecha_creacion
        self.ultimo_acceso = ultimo_acceso
        self.activo = activo
        self.es_admin = es_admin
        self.es_demo = es_demo
        self.vinculado_a_empleado_id = vinculado_a_empleado_id
    
    def get_id(self):
        """Método requerido por Flask-Login"""
        return str(self.id)
    
    @property
    def is_active(self):
        """Método requerido por Flask-Login"""
        return self.activo
    
    @property
    def is_authenticated(self):
        """Método requerido por Flask-Login"""
        return True
    
    @property
    def is_anonymous(self):
        """Método requerido por Flask-Login"""
        return False
    
    @staticmethod
    @db_error_handler()
    def obtener_por_id(user_id):
        """Recupera un usuario por su ID"""
        query = """
            SELECT id, numero_empleado, nombre_completo, email,
                   password_hash, fecha_creacion, ultimo_acceso,
                   activo, es_admin, es_demo, vinculado_a_empleado_id
            FROM empleados
            WHERE id = %s
        """
        result = execute_query(query, (user_id,), fetchone=True)

        if result:
            return Usuario(
                id=result['id'],
                numero_empleado=result['numero_empleado'],
                nombre_completo=result['nombre_completo'],
                email=result['email'],
                password_hash=result['password_hash'],
                fecha_creacion=result['fecha_creacion'],
                ultimo_acceso=result['ultimo_acceso'],
                activo=result['activo'],
                es_admin=result['es_admin'],
                es_demo=result.get('es_demo', False),
                vinculado_a_empleado_id=result.get('vinculado_a_empleado_id')
            )
        return None
    
    @staticmethod
    @db_error_handler()
    def obtener_por_numero_empleado(numero_empleado):
        """Recupera un usuario por su número de empleado"""
        query = """
            SELECT id, numero_empleado, nombre_completo, email,
                   password_hash, fecha_creacion, ultimo_acceso,
                   activo, es_admin, es_demo, vinculado_a_empleado_id
            FROM empleados
            WHERE numero_empleado = %s
        """
        result = execute_query(query, (numero_empleado,), fetchone=True)

        if result:
            return Usuario(
                id=result['id'],
                numero_empleado=result['numero_empleado'],
                nombre_completo=result['nombre_completo'],
                email=result['email'],
                password_hash=result['password_hash'],
                fecha_creacion=result['fecha_creacion'],
                ultimo_acceso=result['ultimo_acceso'],
                activo=result['activo'],
                es_admin=result['es_admin'],
                es_demo=result.get('es_demo', False),
                vinculado_a_empleado_id=result.get('vinculado_a_empleado_id')
            )
        return None
    
    @staticmethod
    @db_error_handler()
    def crear(numero_empleado, nombre_completo, password, email=None, es_admin=False,
              es_demo=False, vinculado_a_empleado_id=None):
        """Crea un nuevo usuario en la base de datos"""
        # Generar hash de la contraseña
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        query = """
            INSERT INTO empleados (numero_empleado, nombre_completo, email,
                                 password_hash, es_admin, es_demo, vinculado_a_empleado_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(query, (numero_empleado, nombre_completo, email, password_hash,
                             es_admin, es_demo, vinculado_a_empleado_id), commit=True)

        # Obtener el ID del usuario recién creado
        query = "SELECT LAST_INSERT_ID() as id"
        result = execute_query(query, fetchone=True)
        return result['id'] if result else None
    
    def verificar_password(self, password):
        """Verifica si la contraseña proporcionada coincide con el hash almacenado"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    @db_error_handler()
    def actualizar_ultimo_acceso(self):
        """Actualiza la marca de tiempo del último acceso"""
        query = """
            UPDATE empleados 
            SET ultimo_acceso = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        execute_query(query, (self.id,), commit=True)
        self.ultimo_acceso = datetime.now()
        
    @staticmethod
    @db_error_handler()
    def listar_todos(solo_activos=True):
        """Lista todos los usuarios, opcionalmente filtrando solo los activos"""
        query = """
            SELECT id, numero_empleado, nombre_completo, email,
                   fecha_creacion, ultimo_acceso, activo, es_admin,
                   es_demo, vinculado_a_empleado_id
            FROM empleados
        """
        if solo_activos:
            query += " WHERE activo = 1"

        return execute_query(query)
    
    @db_error_handler()
    def cambiar_estado(self, activo):
        """Cambia el estado de activación del usuario"""
        query = """
            UPDATE empleados
            SET activo = %s
            WHERE id = %s
        """
        execute_query(query, (1 if activo else 0, self.id), commit=True)
        self.activo = activo
        return True
        
    @staticmethod
    def get_db_connection():
        """Helper para acceder a la conexión de base de datos"""
        return get_db_connection()