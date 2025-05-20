from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Optional

class LoginForm(FlaskForm):
    """Formulario de inicio de sesión"""
    numero_empleado = StringField('Número de Empleado', validators=[
        DataRequired(message='Este campo es obligatorio'),
        Length(min=3, max=20, message='El número de empleado debe tener entre 3 y 20 caracteres')
    ])
    password = PasswordField('Contraseña', validators=[
        DataRequired(message='Este campo es obligatorio')
    ])
    remember = BooleanField('Recordar mis datos')
    submit = SubmitField('Iniciar Sesión')

class UserForm(FlaskForm):
    """Formulario para crear/editar usuarios"""
    numero_empleado = StringField('Número de Empleado', validators=[
        DataRequired(message='Este campo es obligatorio'),
        Length(min=3, max=20, message='El número de empleado debe tener entre 3 y 20 caracteres')
    ])
    nombre_completo = StringField('Nombre Completo', validators=[
        DataRequired(message='Este campo es obligatorio'),
        Length(min=3, max=100, message='El nombre debe tener entre 3 y 100 caracteres')
    ])
    email = StringField('Correo Electrónico', validators=[
        Optional(),
        Email(message='Ingresa un correo electrónico válido')
    ])
    password = PasswordField('Contraseña', validators=[
        Length(min=6, message='La contraseña debe tener al menos 6 caracteres')
    ])
    es_admin = BooleanField('Es Administrador')
    submit = SubmitField('Guardar')

class CredencialesSitaForm(FlaskForm):
    """Formulario para configurar credenciales de SITA"""
    sita_username = StringField('Usuario SITA', validators=[
        DataRequired(message='Este campo es obligatorio')
    ])
    sita_password = PasswordField('Contraseña SITA', validators=[
        DataRequired(message='Este campo es obligatorio')
    ])
    roster_url = StringField('URL del Roster', validators=[
        DataRequired(message='Este campo es obligatorio')
    ])
    site_id = StringField('Site ID', validators=[
        DataRequired(message='Este campo es obligatorio')
    ])
    cvation_tenantid = StringField('Cvation Tenant ID', validators=[
        DataRequired(message='Este campo es obligatorio')
    ])
    submit = SubmitField('Guardar Credenciales')

class CalendarioConfigForm(FlaskForm):
    """Formulario para configurar Google Calendar"""
    google_calendar_id = StringField('ID de Google Calendar', validators=[
        DataRequired(message='Este campo es obligatorio')
    ])
    sincronizacion_activa = BooleanField('Sincronización Activa')
    submit = SubmitField('Guardar Configuración')