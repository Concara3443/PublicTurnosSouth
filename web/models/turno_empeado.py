import json
from datetime import datetime, date, timedelta
from database import execute_query

class TurnoEmpleado:
    """Clase para gestionar los turnos de cada empleado"""

    def __init__(self, id=None, empleado_id=None, dia=None, turno=None, 
                 activo=True, google_event_ids=None, fecha_creacion=None,
                 fecha_actualizacion=None):
        self.id = id
        self.empleado_id = empleado_id
        self.dia = dia
        self.turno = turno
        self.activo = activo
        self.google_event_ids = google_event_ids
        self.fecha_creacion = fecha_creacion
        self.fecha_actualizacion = fecha_actualizacion

    @staticmethod
    def obtener_por_empleado_y_dia(empleado_id, dia):
        """Recupera los turnos de un empleado para un día específico"""
        if isinstance(dia, date):
            dia_str = dia.strftime("%Y-%m-%d")
        else:
            dia_str = dia

        query = """
            SELECT id, empleado_id, dia, turno, activo, google_event_ids, 
                   fecha_creacion, fecha_actualizacion
            FROM turnos_empleado
            WHERE empleado_id = %s AND dia = %s AND activo = 1
        """
        return execute_query(query, (empleado_id, dia_str))

    @staticmethod
    def obtener_por_empleado_y_rango(empleado_id, fecha_inicio, fecha_fin):
        """Recupera los turnos de un empleado para un rango de fechas"""
        if isinstance(fecha_inicio, date):
            fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
        else:
            fecha_inicio_str = fecha_inicio

        if isinstance(fecha_fin, date):
            fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")
        else:
            fecha_fin_str = fecha_fin

        query = """
            SELECT id, empleado_id, dia, turno, activo, google_event_ids, 
                   fecha_creacion, fecha_actualizacion
            FROM turnos_empleado
            WHERE empleado_id = %s AND dia >= %s AND dia <= %s AND activo = 1
        """
        return execute_query(query, (empleado_id, fecha_inicio_str, fecha_fin_str))

    @staticmethod
    def obtener_por_empleado_y_mes(empleado_id, año, mes):
        """Recupera los turnos de un empleado para un mes específico, ajustando para semanas completas"""
        inicio_mes = date(año, mes, 1)
        if mes == 12:
            fin_mes = date(año+1, 1, 1) - timedelta(days=1)
        else:
            fin_mes = date(año, mes+1, 1) - timedelta(days=1)

        primer_dia_semana = inicio_mes.weekday()  # 0=Lunes, 6=Domingo
        ultimo_dia_semana = fin_mes.weekday()

        inicio_ajustado = inicio_mes - timedelta(days=primer_dia_semana)  # Retroceder al lunes
        fin_ajustado = fin_mes + timedelta(days=(6 - ultimo_dia_semana))  # Avanzar al domingo

        query = """
            SELECT id, empleado_id, dia, turno, activo, google_event_ids, 
                   fecha_creacion, fecha_actualizacion
            FROM turnos_empleado
            WHERE empleado_id = %s AND dia >= %s AND dia <= %s AND activo = 1
        """
        return execute_query(query, (
            empleado_id, 
            inicio_ajustado.strftime("%Y-%m-%d"), 
            fin_ajustado.strftime("%Y-%m-%d")
        ))

    @staticmethod
    def desactivar_todos_por_empleado_y_dia(empleado_id, dia):
        """Desactiva todos los turnos activos de un empleado para un día específico"""
        if isinstance(dia, date):
            dia_str = dia.strftime("%Y-%m-%d")
        else:
            dia_str = dia

        query = """
            UPDATE turnos_empleado
            SET activo = 0
            WHERE empleado_id = %s AND dia = %s AND activo = 1
        """
        # execute_query no retorna rowcount, así que lo obtenemos manualmente
        # pero para mantener la interfaz, devolvemos None o podrías modificar execute_query para devolver rowcount en updates
        return execute_query(query, (empleado_id, dia_str), commit=True)

    @staticmethod
    def insertar_o_actualizar(empleado_id, dia, turnos_json=None, google_event_ids=None):
        """Inserta o actualiza los turnos de un empleado para un día específico"""
        if isinstance(dia, date):
            dia_str = dia.strftime("%Y-%m-%d")
        else:
            dia_str = dia

        # Primero desactivar todos los turnos activos para ese día
        TurnoEmpleado.desactivar_todos_por_empleado_y_dia(empleado_id, dia_str)

        # Convertir a string JSON si es un objeto
        if turnos_json is not None and not isinstance(turnos_json, str):
            turnos_json = json.dumps(turnos_json)

        if google_event_ids is not None and not isinstance(google_event_ids, str):
            google_event_ids = json.dumps(google_event_ids)

        query = """
            INSERT INTO turnos_empleado (empleado_id, dia, turno, 
                                         activo, google_event_ids)
            VALUES (%s, %s, %s, 1, %s)
        """
        # No hay un retorno directo de lastrowid en execute_query, así que podrías modificar execute_query para retornarlo si lo necesitas
        return execute_query(query, (empleado_id, dia_str, turnos_json, google_event_ids), commit=True)
