from flask import jsonify
from datetime import date, timedelta
from routes import api_bp
from database import get_turnos_by_range
from calculadora import compute_salaries_for_period

@api_bp.route("/api/detalle_concepto/<concepto_id>/<int:mes>/<int:anio>")
def detalle_concepto(concepto_id, mes, anio):
    """
    API para obtener los detalles de un concepto de nómina
    """
    # Calcular rango del mes
    first_day = date(anio, mes, 1)
    if mes == 12:
        last_day = date(anio+1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(anio, mes+1, 1) - timedelta(days=1)
        
    # Calcular rango de pluses (del 16 del mes anterior al 15 del mes actual)
    if mes == 1:
        plus_start = date(anio-1, 12, 16)
    else:
        plus_start = date(anio, mes-1, 16)
    plus_end = date(anio, mes, 15)
    
    # Calcular nómina
    month_data = compute_salaries_for_period(first_day, last_day)
    
    # Verificar si el mes existe en los datos
    month_key = (anio, mes)
    if month_key not in month_data:
        return jsonify({"error": "No hay datos para el periodo solicitado"}), 404
    
    # Verificar si el concepto existe
    if concepto_id not in month_data[month_key]["conceptos"]:
        return jsonify({"error": "Concepto no encontrado"}), 404
    
    concepto = month_data[month_key]["conceptos"][concepto_id]
    
    # Preparar respuesta
    respuesta = {
        "concepto": concepto["nombre"],
        "total": concepto["total"],
        "valor": concepto.get("tarifa", 0),
        "dias": concepto["dias"]
    }
    
    return jsonify(respuesta)