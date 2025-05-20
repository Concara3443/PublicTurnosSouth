# TurnosIbe

Este proyecto automatiza la gestión de turnos y la creación de eventos en Google Calendar, además de proporcionar información meteorológica relevante para los turnos.

## Características

- **Autenticación**: Se conecta a un sistema externo para obtener los turnos mediante autenticación.
- **Google Calendar**: Crea eventos automáticamente en Google Calendar para cada turno.
- **Información meteorológica**: Obtiene la probabilidad de precipitación para los turnos desde AccuWeather.
- **Configuración mediante `.env`**: Las credenciales y configuraciones sensibles se gestionan a través de un archivo `.env`.

## Requisitos

- Python 3.8 o superior.
- Dependencias listadas en [`requirements.txt`](requirements.txt).

## Instalación

1. Clona este repositorio:

    ```bash
    git clone https://github.com/tu_usuario/TurnosIbe.git
    cd TurnosIbe
    ```

2. Crea un entorno virtual y actívalo:

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # En Windows: .venv\Scripts\activate
    ```

3. Instala las dependencias:

    ```bash
    pip install -r requirements.txt
    ```

4. Crea un archivo `.env` basado en el archivo de ejemplo `.env.example`:

    ```bash
    cp .env.example .env
    ```

5. Rellena las variables necesarias en el archivo `.env`.

## Uso

Ejecuta el script principal:

```bash
python index.py
```

Esto obtendrá los turnos de la próxima semana, creará eventos en Google Calendar y mostrará información meteorológica relevante.

## Configuración

El archivo `.env` debe contener las siguientes variables:

### Google Calendar:

- `GOOGLE_CALENDAR_SCOPES`: Alcance de la API de Google Calendar.
- `GOOGLE_CALENDAR_ID`: ID del calendario donde se crearán los eventos.

### AccuWeather:

- `ACCUWEATHER_API_KEY`: Clave de API de AccuWeather.

### Autenticación:

- `AUTH_URL`: URL para autenticación.
- `ROSTER_URL`: URL para obtener los turnos.
- `USERNAME`: Nombre de usuario para autenticación.
- `PASSWORD`: Contraseña para autenticación.
- `SITE_ID`: ID del sitio.
- `CVATION_TENANTID`: ID del tenant.

## Archivos importantes

- `index.py`: Script principal que gestiona la lógica de turnos, eventos y meteorología.
- `test.py`: Script para pruebas.
- `requirements.txt`: Lista de dependencias necesarias.
- `.env.example`: Ejemplo de archivo de configuración.

## Notas

- Asegúrate de no compartir el archivo `.env` ni las credenciales sensibles.
- El archivo `.gitignore` ya está configurado para excluir archivos sensibles como `.env` y `token.json`.

## Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo `LICENSE` para más detalles.