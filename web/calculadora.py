from datetime import datetime, date, timedelta
import json
from database import parse_turno_json
from config import DIAS_FESTIVOS, TARIFAS

def calcular_nomina_desde_json(day_json, dias_festivos, start_date=None, end_date=None):
    """
    Calcula la nómina para un día específico, incluyendo todos los conceptos
    
    Args:
        day_json: JSON con los turnos del día
        dias_festivos: Lista de días festivos
        start_date: Fecha de inicio del rango (opcional)
        end_date: Fecha fin del rango (opcional)
    
    Returns:
        tuple: (total del día, detalles por concepto)
    """
    precio_medio_hora = TARIFAS["precio_hora"]
    plus_madrugue = TARIFAS["plus_madrugue"]
    plus_festividad = TARIFAS["plus_festividad"]
    plus_domingo = TARIFAS["plus_domingo"]
    plus_nocturnidad = TARIFAS["plus_nocturnidad"]
    plus_jornada_partida = TARIFAS["plus_jornada_partida"]
    plus_transporte = TARIFAS["plus_transporte"]
    dieta_comida = TARIFAS["dieta_comida"]
    dieta_cena = TARIFAS["dieta_cena"]

    shifts = day_json[0].get("shifts", [])
    total_day = 0.0
    
    # Detalles para cada concepto de nómina
    detalles = {
        "SE001": {"nombre": "Sueldo Base", "total": 0, "horas": 0, "tarifa": precio_medio_hora, "dias": []},
        "SE126": {"nombre": "Plus de Madrugue", "total": 0, "horas": 0, "tarifa": plus_madrugue, "dias": []},
        "SE106": {"nombre": "Plus Nocturnidad", "total": 0, "horas": 0, "tarifa": plus_nocturnidad, "dias": []},
        "SE013": {"nombre": "Plus Jornada Partida", "total": 0, "unidades": 0, "tarifa": plus_jornada_partida, "dias": []},
        "SE023": {"nombre": "Plus Domingo", "total": 0, "horas": 0, "tarifa": plus_domingo, "dias": []},
        "festividad": {"nombre": "Plus Festividad", "total": 0, "horas": 0, "tarifa": plus_festividad, "dias": []},
        "SE055": {"nombre": "Gastos Transporte", "total": 0, "unidades": 0, "tarifa": plus_transporte, "dias": []},
        "comida": {"nombre": "Dieta Comida", "total": 0, "unidades": 0, "tarifa": dieta_comida, "dias": []},
        "cena": {"nombre": "Dieta Cena", "total": 0, "unidades": 0, "tarifa": dieta_cena, "dias": []}
    }
    
    for idx, turno in enumerate(shifts, start=1):
        inicio = datetime.fromisoformat(turno["start"].replace("Z", "+00:00"))
        fin = datetime.fromisoformat(turno["end"].replace("Z", "+00:00"))
        
        # Registrar el día del turno
        fecha_turno = inicio.strftime("%Y-%m-%d")
        
        # Filtrar por rango de fechas si se especifican
        if start_date and end_date:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                
            fecha_turno_dt = inicio.date()
            if fecha_turno_dt < start_date or fecha_turno_dt > end_date:
                continue
                
        total_horas = (fin - inicio).total_seconds() / 3600
        sueldo_base = total_horas * precio_medio_hora
        
        # Registrar sueldo base
        detalles["SE001"]["total"] += sueldo_base
        detalles["SE001"]["horas"] += total_horas
        if fecha_turno not in detalles["SE001"]["dias"]:
            detalles["SE001"]["dias"].append(fecha_turno)
        
        # Inicializar contadores de pluses
        count_madrugue = 0
        count_nocturnidad = 0
        count_festividad = 0
        count_domingo = 0
        
        # Calcular horas para cada plus
        hora_iter = inicio
        while hora_iter < fin:
            current_date = hora_iter.strftime('%Y-%m-%d')
            
            # Verificar el día de la semana y si es festivo
            if current_date in dias_festivos:
                count_festividad += 1
                if current_date not in detalles["festividad"]["dias"]:
                    detalles["festividad"]["dias"].append(current_date)
                    
            if hora_iter.weekday() == 6:  # Domingo
                count_domingo += 1
                if current_date not in detalles["SE023"]["dias"]:
                    detalles["SE023"]["dias"].append(current_date)
            
            # Lógica para plus de madrugue y nocturnidad
            if 4 <= hora_iter.hour < 7:
                count_madrugue += 1
                if current_date not in detalles["SE126"]["dias"]:
                    detalles["SE126"]["dias"].append(current_date)
            elif hora_iter.hour >= 22 or hora_iter.hour < 4:
                count_nocturnidad += 1
                if current_date not in detalles["SE106"]["dias"]:
                    detalles["SE106"]["dias"].append(current_date)
                
            hora_iter += timedelta(hours=1)
        
        # Calcular pluses por horas específicas
        plus_madrugue_total = plus_madrugue * count_madrugue
        detalles["SE126"]["total"] += plus_madrugue_total
        detalles["SE126"]["horas"] += count_madrugue
        
        plus_nocturnidad_total = plus_nocturnidad * count_nocturnidad
        detalles["SE106"]["total"] += plus_nocturnidad_total
        detalles["SE106"]["horas"] += count_nocturnidad
            
        plus_festividad_total = plus_festividad * count_festividad
        detalles["festividad"]["total"] += plus_festividad_total
        detalles["festividad"]["horas"] += count_festividad
        
        plus_domingo_total = plus_domingo * count_domingo
        detalles["SE023"]["total"] += plus_domingo_total
        detalles["SE023"]["horas"] += count_domingo
        
        # Calcular pluses fijos
        plus_fijos = 0.0
        if idx == 1 and len(shifts) > 1:
            detalles["SE013"]["total"] += plus_jornada_partida
            detalles["SE013"]["unidades"] += 1
            if fecha_turno not in detalles["SE013"]["dias"]:
                detalles["SE013"]["dias"].append(fecha_turno)
            plus_fijos += plus_jornada_partida
                
        if idx == 1:
            detalles["SE055"]["total"] += plus_transporte
            detalles["SE055"]["unidades"] += 1
            if fecha_turno not in detalles["SE055"]["dias"]:
                detalles["SE055"]["dias"].append(fecha_turno)
            plus_fijos += plus_transporte
        
        # Calcular dietas
        dietas = 0.0
        if inicio.hour <= 14 and fin.hour >= 16 and total_horas >= 6:
            detalles["comida"]["total"] += dieta_comida
            detalles["comida"]["unidades"] += 1
            if fecha_turno not in detalles["comida"]["dias"]:
                detalles["comida"]["dias"].append(fecha_turno)
            dietas += dieta_comida
                
        if inicio.hour <= 21 and fin.hour >= 23 and total_horas >= 6:
            detalles["cena"]["total"] += dieta_cena
            detalles["cena"]["unidades"] += 1
            if fecha_turno not in detalles["cena"]["dias"]:
                detalles["cena"]["dias"].append(fecha_turno)
            dietas += dieta_cena
        
        # Sumar total del turno
        total_turno = sueldo_base + plus_madrugue_total + plus_nocturnidad_total + \
                      plus_festividad_total + plus_domingo_total + plus_fijos + dietas
        total_day += total_turno
        
    return total_day, detalles

def compute_salaries_for_days(rows, pluses_range_start=None, pluses_range_end=None):
    """
    Calcula los salarios para cada día, agrupando los turnos por día
    Con opción de especificar un rango para los pluses (del 16 al 15)
    
    Args:
        rows: Filas de turnos de la base de datos
        pluses_range_start: Fecha inicio para calcular pluses (opcional)
        pluses_range_end: Fecha fin para calcular pluses (opcional)
    
    Returns:
        list: Lista de diccionarios con resultados por día
    """
    grouped = {}
    for r in rows:
        dia_value = r["dia"]
        if isinstance(dia_value, date):
            dia = dia_value.strftime("%Y-%m-%d")
        else:
            dia = str(dia_value)
            
        shift_list = parse_turno_json(r["turno"])
            
        if dia not in grouped:
            grouped[dia] = []
        grouped[dia].extend(shift_list)
    
    # Calcular el salario para cada día
    results = []
    for day_str, turnos_list in grouped.items():
        day_json = [{"shifts": turnos_list}]
        day_total, day_detalles = calcular_nomina_desde_json(day_json, DIAS_FESTIVOS)
        
        # Verificar si este día está dentro del rango para pluses
        incluir_pluses = True
        if pluses_range_start and pluses_range_end:
            day_date = datetime.strptime(day_str, "%Y-%m-%d").date()
            if not (pluses_range_start <= day_date <= pluses_range_end):
                # Eliminar valores de pluses para días fuera del rango
                for key in ["SE126", "SE106", "SE013", "SE023", "festividad", "SE055", "comida", "cena"]:
                    day_detalles[key]["total"] = 0
                    day_detalles[key]["horas"] = 0
                    day_detalles[key]["dias"] = []
                    if "unidades" in day_detalles[key]:
                        day_detalles[key]["unidades"] = 0
                incluir_pluses = False
        
        # Recalcular el total si es necesario
        if not incluir_pluses:
            day_total = day_detalles["SE001"]["total"]  # Solo sueldo base
            
        results.append({
            "date": day_str,
            "shifts": turnos_list,
            "total": day_total,
            "detalles": day_detalles
        })
    
    return results

def compute_salaries_for_period(start_date, end_date):
    """
    Calcula los salarios para un periodo de nómina especificado
    Con pluses calculados del 16 del mes anterior al 15 del mes actual
    
    Args:
        start_date: Fecha inicial del periodo
        end_date: Fecha final del periodo
    
    Returns:
        dict: Datos de nómina organizados por mes
    """
    from database import get_turnos_by_range
    
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
    
    # Obtener todos los turnos en el rango completo
    rows = get_turnos_by_range(start_date, end_date)
    
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