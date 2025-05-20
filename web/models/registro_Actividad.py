from database import execute_query

class RegistroActividad:
    """Clase para gestionar el registro de actividades en el sistema"""
    
    TIPO_LOGIN = 'login'
    TIPO_SINCRONIZACION = 'sincronizacion'
    TIPO_ERROR_SITA = 'error_sita'
    TIPO_ERROR_GOOGLE = 'error_google'
    TIPO_ADMIN_ACCION = 'admin_accion'
    
    @staticmethod
    def registrar(empleado_id, tipo_actividad, descripcion, ip_address=None):
        """Registra una nueva actividad en el sistema"""
        query = """
            INSERT INTO registro_actividad (empleado_id, tipo_actividad, 
                                            descripcion, ip_address)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        params = (empleado_id, tipo_actividad, descripcion, ip_address)
        result = execute_query(query, params, fetchone=True, commit=True)
        return result[0] if result else None

    @staticmethod
    def obtener_por_empleado(empleado_id, limite=100):
        """Obtiene las últimas actividades de un empleado"""
        query = """
            SELECT id, empleado_id, tipo_actividad, descripcion, 
                   ip_address, fecha
            FROM registro_actividad
            WHERE empleado_id = %s
            ORDER BY fecha DESC
            LIMIT %s
        """
        params = (empleado_id, limite)
        return execute_query(query, params)

    @staticmethod
    def obtener_ultimos_errores(limite=50):
        """Obtiene los últimos errores registrados en el sistema"""
        query = """
            SELECT ra.id, ra.empleado_id, ra.tipo_actividad, ra.descripcion, 
                   ra.ip_address, ra.fecha, e.numero_empleado, e.nombre_completo
            FROM registro_actividad ra
            JOIN empleados e ON ra.empleado_id = e.id
            WHERE ra.tipo_actividad IN ('error_sita', 'error_google')
            ORDER BY ra.fecha DESC
            LIMIT %s
        """
        params = (limite,)
        return execute_query(query, params)
