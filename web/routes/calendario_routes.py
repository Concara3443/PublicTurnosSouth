from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
import calendar
import json
from routes import calendario_bp
from database import get_db_connection
from calculadora import compute_salaries_for_days
from config import MONTH_TRANSLATION

# Función auxiliar para obtener turnos de un usuario específico
def get_turnos_by_month_and_user(year, month, empleado_id):
    """
    Obtiene todos los turnos y ausencias de un usuario para un mes, ajustando para incluir semanas completas
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year+1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month+1, 1) - timedelta(days=1)

    # Ajustar para incluir semanas completas
    first_weekday = start_date.weekday()  # 0=Lunes, 6=Domingo
    last_weekday = end_date.weekday()
    adjusted_start_date = start_date - timedelta(days=first_weekday)
    adjusted_end_date = end_date + timedelta(days=(6 - last_weekday))

    try:
        # Buscar en la tabla turnos_empleado
        cursor.execute("""
            SELECT id, dia, turno, ausencias
            FROM turnos_empleado
            WHERE dia >= %s AND dia <= %s AND activo=1 AND empleado_id=%s
        """, (adjusted_start_date.strftime("%Y-%m-%d"), adjusted_end_date.strftime("%Y-%m-%d"), empleado_id))
        
        rows = cursor.fetchall()
        
        return rows
    except Exception as e:
        print(f"Error al obtener turnos: {e}")
        return []
    finally:
        cursor.close()
        conn.close()
        
@calendario_bp.route("/")
@login_required
def home():
    """
    Ruta principal que redirecciona al calendario del mes actual
    """
    today = datetime.now()
    return redirect(url_for("calendario.calendar_view", year=today.year, month=today.month))

@calendario_bp.route("/calendar/<int:year>/<int:month>")
@login_required
def calendar_view(year, month):
    """
    Vista de calendario mensual con semanas completas
    """
    # Obtener turnos del usuario actual
    rows = get_turnos_by_month_and_user(year, month, current_user.id)
    
    # Obtener el primer y último día del mes
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year+1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month+1, 1) - timedelta(days=1)
    
    # Ajustar para incluir semanas completas
    first_weekday = start_date.weekday()  # 0=Lunes, 6=Domingo
    last_weekday = end_date.weekday()
    adjusted_start_date = start_date - timedelta(days=first_weekday)
    adjusted_end_date = end_date + timedelta(days=(6 - last_weekday))
    
    # Calcular salarios para el rango completo, agrupados por día
    salary_info = compute_salaries_for_days(rows)
    
    # Agrupar por día y calcular horas para cada día
    daily_map = {}
    has_any_shifts = False
    
    for s in salary_info:
        day_str = s["date"]
        shifts = s["shifts"]
        total_hours = 0
        
        # Calcular horas totales del día
        for shift in shifts:
            inicio = datetime.fromisoformat(shift["start"].replace("Z", "+00:00"))
            fin = datetime.fromisoformat(shift["end"].replace("Z", "+00:00"))
            hours = (fin - inicio).total_seconds() / 3600
            total_hours += hours
        
        daily_map[day_str] = {
            "total": s["total"], 
            "shifts": shifts,
            "hours": total_hours,
            "absences": []
        }
        
        # Verificar si hay al menos un turno
        if shifts:
            has_any_shifts = True
            
    # Procesar ausencias
    for row in rows:
        if row['ausencias']:
            day_str = row['dia'].strftime("%Y-%m-%d")
            absences = json.loads(row['ausencias'])
            if day_str in daily_map:
                daily_map[day_str]["absences"].extend(absences)
            else:
                daily_map[day_str] = {"total": 0, "shifts": [], "hours": 0, "absences": absences}

    # Agregar días sin turno
    current = adjusted_start_date
    while current <= adjusted_end_date:
        ds = current.strftime("%Y-%m-%d")
        if ds not in daily_map:
            daily_map[ds] = {"total": 0, "shifts": [], "hours": 0, "absences": []}
        current += timedelta(days=1)
    
    # Calcular totales semanales de salario y horas
    weekly_map = {}
    weekly_hours_map = {}
    current = adjusted_start_date
    while current <= adjusted_end_date:
        iso_week = current.isocalendar()[1]
        weekly_map.setdefault(iso_week, 0)
        weekly_hours_map.setdefault(iso_week, 0)
        
        ds = current.strftime("%Y-%m-%d")
        weekly_map[iso_week] += daily_map[ds]["total"]
        weekly_hours_map[iso_week] += daily_map[ds]["hours"]
        
        current += timedelta(days=1)
        
    # Calcular el total mensual y horas mensuales (solo para los días del mes actual)
    monthly_total = 0
    monthly_hours = 0
    for ds, details in daily_map.items():
        if datetime.strptime(ds, "%Y-%m-%d").month == month:
            monthly_total += details["total"]
            monthly_hours += details["hours"]
    
    # Generar semanas para la tabla
    weeks = []
    current = adjusted_start_date
    while current <= adjusted_end_date:
        week = []
        for _ in range(7):  # Una semana tiene 7 días
            week.append(current)
            current += timedelta(days=1)
        weeks.append(week)
    
    # Usar calendar.month_name para obtener el nombre del mes en inglés
    month_name_eng = calendar.month_name[month]
    # Traducir al español usando el diccionario de traducción
    month_name = MONTH_TRANSLATION.get(month_name_eng, month_name_eng)
    
    # Obtener el día actual para resaltarlo
    today = datetime.now().date()
    
    # Datos para la plantilla
    context = {
        'year': year,
        'month': month,
        'month_name': month_name,
        'weeks': weeks,
        'daily_map': daily_map,
        'weekly_map': weekly_map,
        'weekly_hours_map': weekly_hours_map,
        'monthly_total': monthly_total,
        'monthly_hours': monthly_hours,
        'has_any_shifts': has_any_shifts,
        'today': today  # Añadir el día actual al contexto
    }
    
    return render_template('calendar.html', **context)