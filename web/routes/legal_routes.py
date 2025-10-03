from flask import Blueprint, render_template

# Crear el blueprint de páginas legales
legal_bp = Blueprint('legal', __name__)

@legal_bp.route('/legal/cookies')
def cookies():
    """Página de política de cookies"""
    return render_template('legal/aviso_cookies.html')

@legal_bp.route('/legal/privacy')
def privacy():
    """Página de política de privacidad"""
    return render_template('legal/politica_privacidad.html')

@legal_bp.route('/legal/terms')
def terms():
    """Página de condiciones de servicio"""
    return render_template('legal/condiciones_servicio.html')
