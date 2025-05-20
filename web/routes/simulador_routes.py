from flask import render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta
from flask_login import login_required, current_user
from routes import simulador_bp
from calculadora import calcular_nomina_desde_json
from config import DIAS_FESTIVOS, TARIFAS, MONTH_TRANSLATION

@simulador_bp.route("/simulador", methods=["GET", "POST"])
@login_required
def simulador():
    """
    Simulador de turnos para calcular el sueldo
    """
    if request.method == "GET":
        context = {
            'today': datetime.now().strftime('%Y-%m-%d')
        }
        return render_template('simulador_form.html', **context)
    else:
        # Procesar formulario POST
        day_input = request.form.get("day_date")
        if not day_input:
            flash("No se proporcionó un día.", "danger")
            return redirect(url_for("simulador.simulador"))

        shifts = []
        for i in range(1, 4):
            start_key = f"start_time_{i}"
            end_key = f"end_time_{i}"
            start_val = request.form.get(start_key)
            end_val = request.form.get(end_key)
            
            if start_val and end_val:
                try:
                    dt_start = datetime.fromisoformat(f"{day_input}T{start_val}")
                    dt_end = datetime.fromisoformat(f"{day_input}T{end_val}")
                    
                    # Si la hora de fin es menor que la de inicio, asumir que es del día siguiente
                    if dt_end < dt_start:
                        dt_end = dt_end + timedelta(days=1)
                        
                    if dt_end > dt_start:
                        iso_start = dt_start.isoformat() + "Z"
                        iso_end = dt_end.isoformat() + "Z"
                        shifts.append({"start": iso_start, "end": iso_end})
                except Exception as e:
                    flash(f"Error con el formato de hora: {str(e)}", "danger")
                    return redirect(url_for("simulador.simulador"))

        if not shifts:
            flash("No se proporcionó ningún turno válido.", "danger")
            return redirect(url_for("simulador.simulador"))

        # Calcular nómina para los turnos simulados
        day_json = [{"shifts": shifts}]
        total_day, detalles = calcular_nomina_desde_json(day_json, DIAS_FESTIVOS)
        
        # Datos para la plantilla
        context = {
            'day_date': datetime.strptime(day_input, "%Y-%m-%d").date(),
            'shifts': shifts,
            'total_day': total_day,
            'detalles': detalles,
            'tarifas': TARIFAS,
            'month_translation': MONTH_TRANSLATION,
            'dias_festivos': DIAS_FESTIVOS
        }
        
        return render_template('simulador_result.html', **context)