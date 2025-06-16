# web/routes/auto_sync_routes.py
"""
Rutas para controlar y monitorear la sincronización automática
"""

from flask import Blueprint, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from routes.admin_routes import admin_required

# Crear blueprint
auto_sync_bp = Blueprint('auto_sync', __name__)

# Importar el gestor de auto-sync (se inicializará cuando esté disponible)
auto_sync_manager = None

def init_auto_sync_manager(manager):
    """Inicializa el gestor de auto-sync"""
    global auto_sync_manager
    auto_sync_manager = manager

def get_auto_sync_manager():
    """Obtiene el manager de auto-sync de forma segura"""
    global auto_sync_manager
    # Si no está inicializado, intentar obtenerlo de app.py
    if not auto_sync_manager:
        try:
            from app import get_auto_sync_manager as get_manager
            auto_sync_manager = get_manager()
        except ImportError:
            pass
    return auto_sync_manager

@auto_sync_bp.route('/admin/auto-sync')
@admin_required
def panel_auto_sync():
    """Panel de control de sincronización automática"""
    manager = get_auto_sync_manager()
    if not manager:
        flash('El sistema de sincronización automática no está disponible.', 'warning')
        return redirect(url_for('admin.panel'))
    
    stats = manager.get_stats()
    is_running = manager.running
    
    return render_template('admin/auto_sync_panel.html', 
                         stats=stats, 
                         is_running=is_running)

@auto_sync_bp.route('/admin/auto-sync/start', methods=['POST'])
@admin_required
def start_auto_sync():
    """Inicia la sincronización automática"""
    manager = get_auto_sync_manager()
    if not manager:
        flash('El sistema de sincronización automática no está disponible.', 'danger')
        return redirect(url_for('admin.panel'))
    
    try:
        manager.start()
        flash('Sincronización automática iniciada correctamente.', 'success')
    except Exception as e:
        flash(f'Error al iniciar sincronización automática: {str(e)}', 'danger')
    
    return redirect(url_for('auto_sync.panel_auto_sync'))

@auto_sync_bp.route('/admin/auto-sync/stop', methods=['POST'])
@admin_required
def stop_auto_sync():
    """Detiene la sincronización automática"""
    manager = get_auto_sync_manager()
    if not manager:
        flash('El sistema de sincronización automática no está disponible.', 'danger')
        return redirect(url_for('admin.panel'))
    
    try:
        manager.stop()
        flash('Sincronización automática detenida correctamente.', 'success')
    except Exception as e:
        flash(f'Error al detener sincronización automática: {str(e)}', 'danger')
    
    return redirect(url_for('auto_sync.panel_auto_sync'))

@auto_sync_bp.route('/api/auto-sync/status')
@login_required
def status_auto_sync():
    """API para obtener el estado de la sincronización automática"""
    manager = get_auto_sync_manager()
    if not manager:
        return jsonify({
            'available': False,
            'error': 'Sistema no disponible'
        })
    
    stats = manager.get_stats()
    
    return jsonify({
        'available': True,
        'running': manager.running,
        'stats': {
            'cycle_count': stats['cycle_count'],
            'total_users_synced': stats['total_users_synced'],
            'total_errors': stats['total_errors'],
            'last_cycle_start': stats['last_cycle_start'].isoformat() if stats['last_cycle_start'] else None,
            'last_cycle_end': stats['last_cycle_end'].isoformat() if stats['last_cycle_end'] else None,
            'current_user': stats['current_user']
        }
    })

@auto_sync_bp.route('/api/auto-sync/logs')
@admin_required
def logs_auto_sync():
    """API para obtener los logs de sincronización automática"""
    try:
        # Leer las últimas 100 líneas del log
        import os
        log_file = "auto_sync.log"
        
        if not os.path.exists(log_file):
            return jsonify({'logs': []})
        
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Obtener las últimas 100 líneas
            recent_lines = lines[-100:] if len(lines) > 100 else lines
            
        return jsonify({
            'logs': [line.strip() for line in recent_lines],
            'total_lines': len(lines)
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Error al leer logs: {str(e)}',
            'logs': []
        })