from database import execute_query

class EmpleadoWhitelist:
    """Clase para gestionar la lista blanca de empleados que pueden registrarse"""

    @staticmethod
    def agregar(numero_empleado, nombre_completo=None, email=None):
        """Agrega un empleado a la lista blanca"""
        try:
            # Verificar si ya existe
            query_select = "SELECT id FROM empleados_whitelist WHERE numero_empleado = %s"
            existe = execute_query(query_select, (numero_empleado,), fetchone=True)
            if existe:
                # Ya existe, actualizamos los datos
                query_update = """
                    UPDATE empleados_whitelist
                    SET nombre_completo = %s, email = %s, registrado = 0
                    WHERE numero_empleado = %s
                """
                execute_query(query_update, (nombre_completo, email, numero_empleado), commit=True)
            else:
                # No existe, lo insertamos
                query_insert = """
                    INSERT INTO empleados_whitelist
                    (numero_empleado, nombre_completo, email)
                    VALUES (%s, %s, %s)
                """
                execute_query(query_insert, (numero_empleado, nombre_completo, email), commit=True)
            return True
        except Exception as e:
            print(f"Error al agregar empleado a la lista blanca: {e}")
            return False

    @staticmethod
    def eliminar(numero_empleado):
        """Elimina un empleado de la lista blanca"""
        try:
            query = "DELETE FROM empleados_whitelist WHERE numero_empleado = %s"
            execute_query(query, (numero_empleado,), commit=True)
            return True
        except Exception as e:
            print(f"Error al eliminar empleado de la lista blanca: {e}")
            return False

    @staticmethod
    def verificar(numero_empleado):
        """Verifica si un empleado está en la lista blanca y no se ha registrado"""
        query = """
            SELECT id, nombre_completo, email, registrado
            FROM empleados_whitelist
            WHERE numero_empleado = %s
        """
        empleado = execute_query(query, (numero_empleado,), fetchone=True)
        if empleado and not empleado['registrado']:
            return {
                'id': empleado['id'],
                'nombre_completo': empleado['nombre_completo'],
                'email': empleado['email']
            }
        return None

    @staticmethod
    def marcar_como_registrado(numero_empleado):
        """Marca un empleado como registrado"""
        try:
            query = """
                UPDATE empleados_whitelist
                SET registrado = 1, fecha_registro = CURRENT_TIMESTAMP
                WHERE numero_empleado = %s
            """
            execute_query(query, (numero_empleado,), commit=True)
            return True
        except Exception as e:
            print(f"Error al marcar empleado como registrado: {e}")
            return False

    @staticmethod
    def listar_todos():
        """Lista todos los empleados en la lista blanca"""
        query = """
            SELECT id, numero_empleado, nombre_completo, email, 
                   fecha_creacion, fecha_registro, registrado
            FROM empleados_whitelist
            ORDER BY fecha_creacion DESC
        """
        return execute_query(query)
