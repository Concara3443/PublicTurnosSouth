#!/usr/bin/env python
"""
Sincronizador Independiente de Turnos
Ejecuta solo la sincronización automática sin la aplicación web
"""

import sys
import os

# Añadir el directorio de la aplicación al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'web'))

from auto_sync_manager import AutoSyncManager, signal_handler
import signal
import time
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("standalone_sync.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("StandaloneSync")

def main():
    """Función principal para ejecutar solo el sincronizador"""
    logger.info("🚀 Iniciando sincronizador independiente de turnos")
    
    # Crear gestor de auto-sync
    auto_sync_manager = AutoSyncManager()
    
    # Registrar manejadores de señales para parada limpia
    def cleanup(signum, frame):
        logger.info("🛑 Señal de parada recibida")
        auto_sync_manager.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        # Iniciar sincronización automática
        auto_sync_manager.start()
        
        logger.info("""
        =================================================================
        🔄 Sincronizador de turnos ejecutándose en modo independiente
        
        - Se ejecuta cada hora
        - Procesa usuarios uno por uno
        - Logs en: standalone_sync.log
        - Para detener: Ctrl+C
        =================================================================
        """)
        
        # Mantener el proceso vivo y mostrar estadísticas periódicamente
        last_stats_time = time.time()
        
        while True:
            time.sleep(30)  # Verificar cada 30 segundos
            
            # Mostrar estadísticas cada 5 minutos
            current_time = time.time()
            if current_time - last_stats_time >= 300:  # 5 minutos
                stats = auto_sync_manager.get_stats()
                if stats['cycle_count'] > 0:
                    logger.info(f"📊 Estadísticas: "
                              f"Ciclos: {stats['cycle_count']}, "
                              f"Usuarios sincronizados: {stats['total_users_synced']}, "
                              f"Errores: {stats['total_errors']}")
                    
                    if stats['current_user']:
                        logger.info(f"🔄 Sincronizando actualmente: {stats['current_user']}")
                    
                last_stats_time = current_time
                
    except KeyboardInterrupt:
        logger.info("👋 Deteniendo por interrupción del usuario")
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}")
    finally:
        auto_sync_manager.stop()
        logger.info("✅ Sincronizador detenido")

if __name__ == "__main__":
    main()