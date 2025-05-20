from database import execute_query
class CalendarioConfig:
    """Clase para manejar la configuración de Google Calendar por usuario"""

    def __init__(self, id=None, empleado_id=None, google_calendar_id=None, 
                 token_json=None, sincronizacion_activa=True, ultima_sincronizacion=None):
        self.id = id
        self.empleado_id = empleado_id
        self.google_calendar_id = google_calendar_id
        self.token_json = token_json
        self.sincronizacion_activa = sincronizacion_activa
        self.ultima_sincronizacion = ultima_sincronizacion

    @staticmethod
    def obtener_por_empleado_id(empleado_id):
        """Recupera la configuración de calendario de un empleado por su ID"""
        query = """
            SELECT id, empleado_id, google_calendar_id, token_json, 
                   sincronizacion_activa, ultima_sincronizacion
            FROM calendario_config
            WHERE empleado_id = %s
        """
        result = execute_query(query, (empleado_id,), fetchone=True)
        if result:
            return CalendarioConfig(
                id=result['id'],
                empleado_id=result['empleado_id'],
                google_calendar_id=result['google_calendar_id'],
                token_json=result['token_json'],
                sincronizacion_activa=result['sincronizacion_activa'],
                ultima_sincronizacion=result['ultima_sincronizacion']
            )
        return None

    @staticmethod
    def crear_o_actualizar(empleado_id, google_calendar_id, token_json=None, 
                         sincronizacion_activa=True):
        """Crea o actualiza la configuración de calendario de un empleado"""
        select_query = "SELECT id FROM calendario_config WHERE empleado_id = %s"
        existing = execute_query(select_query, (empleado_id,), fetchone=True)

        if existing:
            query = """
                UPDATE calendario_config
                SET google_calendar_id = %s,
                    sincronizacion_activa = %s
            """
            params = [google_calendar_id, sincronizacion_activa]

            if token_json is not None:
                query += ", token_json = %s"
                params.append(token_json)

            query += " WHERE empleado_id = %s"
            params.append(empleado_id)

            execute_query(query, params, commit=True)
            config_id = existing['id']
        else:
            insert_query = """
                INSERT INTO calendario_config (empleado_id, google_calendar_id, 
                                              token_json, sincronizacion_activa)
                VALUES (%s, %s, %s, %s)
            """
            params = (empleado_id, google_calendar_id, token_json, sincronizacion_activa)
            execute_query(insert_query, params, commit=True)
            # Si necesitas el id, deberías modificar execute_query para retornarlo
            config_id = None

        return config_id

    def actualizar_ultima_sincronizacion(self):
        """Actualiza la marca de tiempo de la última sincronización"""
        query = """
            UPDATE calendario_config 
            SET ultima_sincronizacion = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        execute_query(query, (self.id,), commit=True)
