from flask import render_template, request, redirect, url_for, flash
from datetime import datetime, date, timedelta
import calendar
from flask_login import login_required, current_user
from routes import nomina_bp
from calculadora import compute_salaries_for_period
from database import execute_query, get_turnos_by_range
from config import MONTH_TRANSLATION, COMPANY_INFO, EMPLOYEE_INFO

# Función auxiliar para obtener turnos en un rango para un usuario específico
def get_turnos_by_range_and_user(start_date, end_date, empleado_id):
    """Obtiene los turnos en un rango para un usuario específico"""
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
        FROM turnos_empleado
        WHERE dia >= %s AND dia <= %s AND activo=1 AND empleado_id=%s
    """
    params = (start_str, end_str, empleado_id)
    return execute_query(query, params)
def compute_salaries_for_period_by_user(start_date, end_date, empleado_id):
    """
    Calcula los salarios para un periodo de nómina especificado y un usuario específico
    Con pluses calculados del 16 del mes anterior al 15 del mes actual
    """
    # Convertir a objetos date si son strings
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    # Determinar el rango para los pluses
    # Pluses del 16 del mes anterior al 15 del mes actual para cada mes
    months_in_range = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.day <= 15:  # Primera mitad del mes
            pluses_start = date(current_date.year - 1 if current_date.month == 1 else current_date.year,
                               12 if current_date.month == 1 else current_date.month - 1, 16)
            pluses_end = date(current_date.year, current_date.month, 15)
        else:  # Segunda mitad del mes
            pluses_start = date(current_date.year, current_date.month, 16)
            next_month = current_date.month + 1
            next_year = current_date.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            pluses_end = date(next_year, next_month, 15)
        
        month_key = (current_date.year, current_date.month)
        if month_key not in [m[0] for m in months_in_range]:
            months_in_range.append((month_key, pluses_start, pluses_end))
        
        # Avanzar al siguiente día
        current_date += timedelta(days=1)
    
    # Obtener todos los turnos en el rango completo para el usuario específico
    rows = get_turnos_by_range_and_user(start_date, end_date, empleado_id)
    
    # Agrupar turnos por mes
    turnos_por_mes = {}
    for r in rows:
        dia_value = r["dia"]
        if isinstance(dia_value, date):
            dia_date = dia_value
        else:
            dia_date = datetime.strptime(str(dia_value), "%Y-%m-%d").date()
        
        month_key = (dia_date.year, dia_date.month)
        if month_key not in turnos_por_mes:
            turnos_por_mes[month_key] = []
        
        turnos_por_mes[month_key].append(r)
    
    # Calcular salarios para cada mes con sus reglas de pluses específicas
    from calculadora import compute_salaries_for_days, TARIFAS, DIAS_FESTIVOS
    
    results_by_month = {}
    
    for month_key, plus_start, plus_end in months_in_range:
        if month_key in turnos_por_mes:
            # Filtrar días que están dentro del rango de fechas solicitado
            month_rows = turnos_por_mes[month_key]
            
            # Calcular salarios para este mes con reglas de pluses
            month_days = compute_salaries_for_days(month_rows, plus_start, plus_end)
            
            # Agrupar por conceptos
            total_conceptos = {
                "SE001": {"nombre": "Sueldo Base", "total": 0, "horas": 0, "tarifa": TARIFAS["precio_hora"], "dias": []},
                "SE126": {"nombre": "Plus de Madrugue", "total": 0, "horas": 0, "tarifa": TARIFAS["plus_madrugue"], "dias": []},
                "SE106": {"nombre": "Plus Nocturnidad", "total": 0, "horas": 0, "tarifa": TARIFAS["plus_nocturnidad"], "dias": []},
                "SE013": {"nombre": "Plus Jornada Partida", "total": 0, "unidades": 0, "tarifa": TARIFAS["plus_jornada_partida"], "dias": []},
                "SE023": {"nombre": "Plus Domingo", "total": 0, "horas": 0, "tarifa": TARIFAS["plus_domingo"], "dias": []},
                "festividad": {"nombre": "Plus Festividad", "total": 0, "horas": 0, "tarifa": TARIFAS["plus_festividad"], "dias": []},
                "SE055": {"nombre": "Gastos Transporte", "total": 0, "unidades": 0, "tarifa": TARIFAS["plus_transporte"], "dias": []},
                "comida": {"nombre": "Dieta Comida", "total": 0, "unidades": 0, "tarifa": TARIFAS["dieta_comida"], "dias": []},
                "cena": {"nombre": "Dieta Cena", "total": 0, "unidades": 0, "tarifa": TARIFAS["dieta_cena"], "dias": []}
            }
            
            for day_data in month_days:
                for concepto, detalles in day_data["detalles"].items():
                    total_conceptos[concepto]["total"] += detalles["total"]
                    
                    # Verificar si la clave existe antes de sumar
                    if "horas" in detalles and "horas" in total_conceptos[concepto]:
                        total_conceptos[concepto]["horas"] += detalles["horas"]
                    
                    if "unidades" in detalles and "unidades" in total_conceptos[concepto]:
                        total_conceptos[concepto]["unidades"] += detalles["unidades"]
                    
                    for dia in detalles["dias"]:
                        if dia not in total_conceptos[concepto]["dias"]:
                            total_conceptos[concepto]["dias"].append(dia)
            
            # Calcular total del mes
            total_salary = sum(day["total"] for day in month_days)
            
            results_by_month[month_key] = {
                "days": month_days,
                "total_salary": total_salary,
                "conceptos": total_conceptos,
                "pluses_range": (plus_start, plus_end)
            }
    
    return results_by_month

@nomina_bp.route("/nomina_form")
@login_required
def nomina_form():
    """
    Formulario para seleccionar el rango de fechas de nómina
    """
    today = datetime.now()
    default_end_date = today.strftime("%Y-%m-%d")
    
    # Calcular una fecha predeterminada para inicio (ejemplo: 25 del mes anterior)
    if today.month == 1:
        default_start_month = 12
        default_start_year = today.year - 1
    else:
        default_start_month = today.month - 1
        default_start_year = today.year
        
    # Si hoy es antes del día 25, mostrar desde el 25 del mes -2
    if today.day < 25:
        if default_start_month == 1:
            default_start_month = 11
            default_start_year -= 1
        else:
            default_start_month -= 1
            
    # Asegurarse de que el día sea válido (el 25 o el último día del mes)
    try:
        default_start_date = date(default_start_year, default_start_month, 25)
    except ValueError:
        last_day = calendar.monthrange(default_start_year, default_start_month)[1]
        default_start_date = date(default_start_year, default_start_month, last_day)
        
    default_start = default_start_date.strftime("%Y-%m-%d")
    
    context = {
        'default_start': default_start,
        'default_end': default_end_date
    }
    
    return render_template('nomina_form.html', **context)

@nomina_bp.route("/nomina")
@login_required
def nomina_view():
    """
    Vista de nómina personalizada basada en un rango de fechas
    """
    # Obtener rango de fechas
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    
    if not start_date_str or not end_date_str:
        return redirect(url_for("nomina.nomina_form"))
    
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Formato de fecha inválido. Use YYYY-MM-DD.", "danger")
        return redirect(url_for("nomina.nomina_form"))
    
    # Calcular salario para el rango, organizado por mes
    nomina_data = compute_salaries_for_period_by_user(start_date, end_date, current_user.id)
    
    if not nomina_data:
        context = {
            'start_date': start_date_str,
            'end_date': end_date_str
        }
        return render_template('nomina_empty.html', **context)
    
    # Procesar fechas para cada mes en la nómina
    processed_data = {}
    total_general = 0
    
    for month_key, month_info in nomina_data.items():
        year, month = month_key
        
        # Calcular fechas de inicio y fin para este mes
        first_day_month = date(year, month, 1)
        if month == 12:
            last_day_month = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day_month = date(year, month + 1, 1) - timedelta(days=1)
        
        # Calcular período de liquidación
        start_period = max(first_day_month, start_date)
        end_period = min(last_day_month, end_date)
        
        # Obtener nombre del mes en español
        month_name_eng = calendar.month_name[month]
        month_name = MONTH_TRANSLATION.get(month_name_eng, month_name_eng)
        
        # Calcular rango de pluses
        pluses_start, pluses_end = month_info["pluses_range"]
        
        # Formatear fechas
        pluses_start_str = pluses_start.strftime('%d de %B de %Y')
        pluses_end_str = pluses_end.strftime('%d de %B de %Y')
        periodo_str = start_period.strftime('%d de %B de %Y') + ' al ' + end_period.strftime('%d de %B de %Y')
        
        # Traducir los meses en las fechas
        for eng, esp in MONTH_TRANSLATION.items():
            pluses_start_str = pluses_start_str.replace(eng, esp)
            pluses_end_str = pluses_end_str.replace(eng, esp)
            periodo_str = periodo_str.replace(eng, esp)
        
        # Determinar el tipo de nómina
        current_month = datetime.now().month
        current_year = datetime.now().year
        if month < current_month or (month == current_month and end_period.day < 15):
            tipo_nomina = 'Atrasos'
        else:
            tipo_nomina = 'Nómina Mensual'
        
        # Calcular el total devengado
        total_devengado = sum(concepto["total"] for concepto in month_info["conceptos"].values() if concepto["total"] > 0)
        
        # Calcular deducciones simuladas
        irpf_rate = 0.02
        irpf_amount = total_devengado * irpf_rate
        
        ss_cc_rate = 0.047
        ss_cc_base = total_devengado * 1.15
        ss_cc_amount = ss_cc_base * ss_cc_rate
        
        ss_d_rate = 0.0155
        ss_d_amount = ss_cc_base * ss_d_rate
        
        ss_fp_rate = 0.001
        ss_fp_amount = ss_cc_base * ss_fp_rate
        
        ss_mei_rate = 0.0013
        ss_mei_amount = ss_cc_base * ss_mei_rate
        
        total_deducciones = irpf_amount + ss_cc_amount + ss_d_amount + ss_fp_amount + ss_mei_amount
        liquido_percibir = total_devengado - total_deducciones
        
        total_general += liquido_percibir
        
        # Guardar los datos procesados
        processed_data[month_key] = {
            "data": month_info,
            "month_name": month_name,
            "periodo_str": periodo_str,
            "pluses_start_str": pluses_start_str,
            "pluses_end_str": pluses_end_str,
            "tipo_nomina": tipo_nomina,
            "total_devengado": total_devengado,
            "irpf_rate": irpf_rate,
            "irpf_amount": irpf_amount,
            "ss_cc_rate": ss_cc_rate,
            "ss_cc_base": ss_cc_base,
            "ss_cc_amount": ss_cc_amount,
            "ss_d_rate": ss_d_rate,
            "ss_d_amount": ss_d_amount,
            "ss_fp_rate": ss_fp_rate,
            "ss_fp_amount": ss_fp_amount,
            "ss_mei_rate": ss_mei_rate,
            "ss_mei_amount": ss_mei_amount,
            "total_deducciones": total_deducciones,
            "liquido_percibir": liquido_percibir
        }
    
    # Fecha actual en español
    fecha_actual = datetime.now().strftime('%d de %B de %Y')
    for eng, esp in MONTH_TRANSLATION.items():
        fecha_actual = fecha_actual.replace(eng, esp)
    
    # Personalizar la información del empleado para el usuario actual
    employee_info = {
        "nombre": current_user.nombre_completo,
        "dni": "",  # No tenemos este dato en la tabla usuarios
        "numero": current_user.numero_empleado,
        "departamento": "OPERACIONES HANDLING"  # Mantenemos el departamento por defecto
    }
    
    # Datos para la plantilla
    context = {
        'start_date': start_date_str,
        'end_date': end_date_str,
        'nomina_data': processed_data,
        'company_info': COMPANY_INFO,
        'employee_info': employee_info,  # Usamos la info personalizada
        'total_general': total_general,
        'fecha_actual': fecha_actual
    }
    
    return render_template('nomina_simplified.html', **context)