import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la base de datos
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Puerto de la aplicación
APP_PORT = 5680

# Definir días festivos
DIAS_FESTIVOS = [
    "2025-01-01", "2025-01-06", "2025-04-18", "2025-04-21", "2025-05-01",
    "2025-06-09", "2025-06-24", "2025-08-15", "2025-09-11", "2025-09-29",
    "2025-11-01", "2025-12-06", "2025-12-08", "2025-12-25", "2025-12-26"
]

# Tarifas y pluses
TARIFAS = {
    "precio_hora": 7.48,
    "plus_madrugue": 6.43,      # €/h para turno de mañana (04:00–06:55)
    "plus_festividad": 2.85,     # €/h para días festivos
    "plus_domingo": 2.80,        # €/h para domingo
    "plus_nocturnidad": 1.61,    # €/h para turno de noche (22:00–06:00)
    "plus_jornada_partida": 11.34,
    "plus_transporte": 2.83,
    "dieta_comida": 6.43,
    "dieta_cena": 6.43
}

# Traducción de meses
MONTH_TRANSLATION = {
    "January": "Enero", 
    "February": "Febrero", 
    "March": "Marzo", 
    "April": "Abril",
    "May": "Mayo", 
    "June": "Junio", 
    "July": "Julio", 
    "August": "Agosto",
    "September": "Septiembre", 
    "October": "Octubre", 
    "November": "Noviembre", 
    "December": "Diciembre"
}

# Información de la empresa
COMPANY_INFO = {
    "nombre": "SOUTH EUROPE GROUND SERVICES",
    "domicilio": "AV de la Hispanidad 6",
    "cif": "B70717210"
}

# Información del empleado
EMPLOYEE_INFO = {
    "nombre": "GUILLERMO CORTES MESAS",
    "dni": "73433573R",
    "numero": "022428",
    "departamento": "OPERACIONES HANDLING"
}