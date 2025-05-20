from flask import render_template, request, redirect, url_for, flash
from datetime import datetime, date, timedelta
import json
from flask_login import login_required, current_user
from routes import detalle_bp
from database import get_turnos_by_day, get_turnos_by_range, parse_turno_json, get_db_connection
from calculadora import calcular_nomina_desde_json, compute_salaries_for_days
from config import DIAS_FESTIVOS, TARIFAS

# Función auxiliar para obtener turnos de usuario específico
def get_turnos_by_day_and_user(day_str, empleado_id):
    """Obtiene los turnos de un día específico para un usuario específico"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, dia, turno 
                FROM turnos_empleado 
                WHERE dia = %s AND activo=1 AND empleado_id=%s
            """, (day_str, empleado_id))
            
            return cursor.fetchall()
    finally:
        conn.close()

# Función auxiliar para obtener turnos en un rango para un usuario específico
def get_turnos_by_range_and_user(start_date, end_date, empleado_id):
    """Obtiene los turnos en un rango para un usuario específico"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Convertir fechas a string si son objetos date
            if isinstance(start_date, date):
                start_str = start_date.strftime("%Y-%m-%d")
            else:
                start_str = start_date
                
            if isinstance(end_date, date):
                end_str = end_date.strftime("%Y-%m-%d")
            else:
                end_str = end_date

            cursor.execute("""
                SELECT id, dia, turno
                FROM turnos_empleado
                WHERE dia >= %s AND dia <= %s AND activo=1 AND empleado_id=%s
            """, (start_str, end_str, empleado_id))
            
            return cursor.fetchall()
    finally:
        conn.close()

@detalle_bp.route("/day/<year>/<month>/<day>")
@login_required
def day_detail(year, month, day):
    """
    Detalle de un día específico, mostrando el desglose de cada turno
    """
    try:
        day_date = date(int(year), int(month), int(day))
    except ValueError:
        flash("Fecha incorrecta", "danger")
        return redirect(url_for('calendario.home'))
        
    day_str = day_date.strftime("%Y-%m-%d")
    
    # Obtener turnos del usuario actual
    rows = get_turnos_by_day_and_user(day_str, current_user.id)
    
    # Preparar turnos para la plantilla
    turnos_desglose = []
    turno_json_list = []
    
    if rows:
        for r in rows:
            turno_data = r["turno"]
            if turno_data is None:
                continue
                
            try:
                turnos = json.loads(turno_data) if isinstance(turno_data, str) else turno_data
            except Exception as e:
                turnos = []
                
            if not turnos:
                continue
                
            turno_json_list.extend(turnos)
            jornada_partida = len(turnos) > 1
            
            for idx, turno in enumerate(turnos, start=1):
                # Datos básicos del turno
                inicio = datetime.fromisoformat(turno["start"].replace("Z", "+00:00"))
                fin = datetime.fromisoformat(turno["end"].replace("Z", "+00:00"))
                
                # Calcular horas y sueldo base
                total_horas = (fin - inicio).total_seconds() / 3600
                sueldo_base = total_horas * TARIFAS["precio_hora"]
                
                # Contadores de pluses
                contadores = {
                    'madrugue': 0,
                    'nocturnidad': 0,
                    'festividad': 0,
                    'domingo': 0
                }
                
                # Horas por tipo de plus
                hora_iter = inicio
                while hora_iter < fin:
                    current_date = hora_iter.strftime('%Y-%m-%d')
                    
                    if current_date in DIAS_FESTIVOS:
                        contadores['festividad'] += 1
                    if hora_iter.weekday() == 6:
                        contadores['domingo'] += 1
                        
                    # Plus madrugue/nocturnidad
                    if 4 <= hora_iter.hour < 7:
                        contadores['madrugue'] += 1
                    elif hora_iter.hour >= 22 or hora_iter.hour < 4:
                        contadores['nocturnidad'] += 1
                        
                    hora_iter += timedelta(hours=1)
                
                # Calcular importes de pluses horarios
                plus_importes = {
                    'madrugue': contadores['madrugue'] * TARIFAS["plus_madrugue"],
                    'nocturnidad': contadores['nocturnidad'] * TARIFAS["plus_nocturnidad"],
                    'festividad': contadores['festividad'] * TARIFAS["plus_festividad"],
                    'domingo': contadores['domingo'] * TARIFAS["plus_domingo"]
                }
                
                # Pluses fijos
                plus_fijos = {}
                if idx == 1 and jornada_partida:
                    plus_fijos['jornada_partida'] = TARIFAS["plus_jornada_partida"]
                if idx == 1:
                    plus_fijos['transporte'] = TARIFAS["plus_transporte"]
                
                # Dietas
                dietas = {}
                if inicio.hour <= 14 and fin.hour >= 16 and total_horas >= 6:
                    dietas['comida'] = TARIFAS["dieta_comida"]
                if inicio.hour <= 21 and fin.hour >= 23 and total_horas >= 6:
                    dietas['cena'] = TARIFAS["dieta_cena"]
                
                # Total del turno
                total_pluses = sum(plus_importes.values()) + sum(plus_fijos.values())
                total_dietas = sum(dietas.values())
                total_turno = sueldo_base + total_pluses + total_dietas
                
                # Guardar el desglose para la plantilla
                turno_desglose = {
                    'idx': idx,
                    'inicio': inicio,
                    'fin': fin, 
                    'total_horas': total_horas,
                    'sueldo_base': sueldo_base,
                    'contadores': contadores,
                    'plus_importes': plus_importes,
                    'plus_fijos': plus_fijos,
                    'dietas': dietas,
                    'total_pluses': total_pluses,
                    'total_dietas': total_dietas,
                    'total_turno': total_turno
                }
                
                turnos_desglose.append(turno_desglose)
    
    # Calcular el total del día
    day_json = [{"shifts": turno_json_list}]
    day_total, _ = calcular_nomina_desde_json(day_json, DIAS_FESTIVOS)
    
    # Datos para la plantilla
    context = {
        'day_date': day_date,
        'turnos_desglose': turnos_desglose,
        'day_total': day_total,
        'tarifas': TARIFAS
    }
    
    return render_template('day_detail.html', **context)

@detalle_bp.route("/rango_form")
@login_required
def rango_form():
    """
    Formulario para seleccionar un rango de fechas
    """
    return render_template('rango_form.html')

@detalle_bp.route("/rango")
@login_required
def rango_view():
    """
    Muestra los salarios en un rango de fechas específico
    """
    # Obtener las fechas del rango
    start_str = request.args.get("start")
    end_str = request.args.get("end")
    
    if not start_str or not end_str:
        flash("Proporciona fechas de inicio y fin", "danger")
        return redirect(url_for('detalle.rango_form'))
    
    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
    except Exception as e:
        flash("Formato de fecha incorrecto. Use AAAA-MM-DD", "danger")
        return redirect(url_for('detalle.rango_form'))
    
    # Obtener turnos en el rango de fechas para el usuario actual
    rows = get_turnos_by_range_and_user(start_date, end_date, current_user.id)
    
    # Computar salarios
    salary_info = compute_salaries_for_days(rows)
    
    # Ordenar por fecha
    salary_info.sort(key=lambda x: x["date"])
    
    # Datos para la plantilla
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'salary_info': salary_info,
        'total_sum': sum(item["total"] for item in salary_info)
    }
    
    return render_template('rango.html', **context)