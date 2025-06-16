#!/usr/bin/env python
"""
Sistema de Sincronización Automática de Turnos
Sincroniza todos los usuarios automáticamente cada hora
"""

import threading
import time
import logging
import traceback
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import signal
import sys
import os

# Importar módulos de la aplicación
from database import get_db_connection, execute_query, close_db_connection
from models.credencial_sita import CredencialSita
from routes.sincronizacion_routes import obtener_turnos_sita, insertar_turnos_en_bd

# Configurar logging específico para el sincronizador
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_sync.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AutoSyncTurnos")

class AutoSyncManager:
    """Gestor de sincronización automática de turnos"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.stats = {
            'cycle_count': 0,
            'total_users_synced': 0,
            'total_errors': 0,
            'last_cycle_start': None,
            'last_cycle_end': None,
            'current_user': None
        }
        
    def start(self):
        """Inicia el proceso de sincronización automática"""
        if self.running:
            logger.warning("El sincronizador automático ya está en ejecución")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.thread.start()
        logger.info("🚀 Sincronizador automático iniciado")
        
    def stop(self):
        """Detiene el proceso de sincronización automática"""
        if not self.running:
            return
            
        self.running = False
        if self.thread and self.thread.is_alive():
            logger.info("⏹️ Deteniendo sincronizador automático...")
            self.thread.join(timeout=30)
        logger.info("✅ Sincronizador automático detenido")
        
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del sincronizador"""
        return self.stats.copy()
        
    def _sync_loop(self):
        """Bucle principal de sincronización"""
        logger.info("🔄 Iniciando bucle de sincronización automática")
        
        while self.running:
            try:
                cycle_start = datetime.now()
                self.stats['cycle_count'] += 1
                self.stats['last_cycle_start'] = cycle_start
                
                logger.info(f"📅 Iniciando ciclo de sincronización #{self.stats['cycle_count']}")
                
                # Obtener usuarios activos con credenciales SITA
                users = self._get_active_users_with_credentials()
                
                if not users:
                    logger.warning("⚠️ No se encontraron usuarios activos con credenciales SITA")
                else:
                    logger.info(f"👥 Sincronizando {len(users)} usuarios")
                    
                    # Sincronizar cada usuario secuencialmente
                    for user in users:
                        if not self.running:  # Verificar si se debe detener
                            break
                            
                        self.stats['current_user'] = f"{user['nombre_completo']} ({user['numero_empleado']})"
                        success = self._sync_user_with_retries(user)
                        
                        if success:
                            self.stats['total_users_synced'] += 1
                        else:
                            self.stats['total_errors'] += 1
                            
                        # Pequeña pausa entre usuarios para no sobrecargar
                        if self.running:
                            time.sleep(5)
                
                self.stats['last_cycle_end'] = datetime.now()
                self.stats['current_user'] = None
                
                cycle_duration = (self.stats['last_cycle_end'] - cycle_start).total_seconds()
                logger.info(f"✅ Ciclo #{self.stats['cycle_count']} completado en {cycle_duration:.1f}s")
                
                # Esperar 1 hora antes del siguiente ciclo
                if self.running:
                    logger.info("⏰ Esperando 1 hora hasta el próximo ciclo...")
                    self._wait_with_interruption(3600)  # 1 hora = 3600 segundos
                    
            except Exception as e:
                logger.error(f"❌ Error crítico en el bucle de sincronización: {e}")
                logger.error(traceback.format_exc())
                self.stats['total_errors'] += 1
                
                # Esperar un poco antes de reintentar
                if self.running:
                    logger.info("⏳ Esperando 5 minutos antes de reintentar...")
                    self._wait_with_interruption(300)  # 5 minutos
                    
        logger.info("🏁 Bucle de sincronización terminado")
        
    def _wait_with_interruption(self, seconds: int):
        """Espera con capacidad de interrupción"""
        start_time = time.time()
        while self.running and (time.time() - start_time) < seconds:
            time.sleep(1)
            
    def _get_active_users_with_credentials(self) -> List[Dict]:
        """Obtiene usuarios activos que tienen credenciales SITA configuradas"""
        try:
            query = """
                SELECT e.id, e.numero_empleado, e.nombre_completo, e.email,
                       c.sita_username, c.site_id, c.cvation_tenantid, c.roster_url
                FROM empleados e
                INNER JOIN credenciales_sita c ON e.id = c.empleado_id
                WHERE e.activo = 1
                ORDER BY e.id
            """
            
            users = execute_query(query)
            logger.info(f"📊 Encontrados {len(users)} usuarios activos con credenciales SITA")
            return users
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo usuarios: {e}")
            return []
            
    def _sync_user_with_retries(self, user: Dict) -> bool:
        """Sincroniza un usuario con lógica de reintentos para timeouts"""
        user_id = user['id']
        user_name = f"{user['nombre_completo']} ({user['numero_empleado']})"
        
        max_retries = 5
        retry_delay = 30  # 30 segundos entre reintentos
        
        for attempt in range(1, max_retries + 1):
            if not self.running:
                return False
                
            try:
                logger.info(f"🔄 [{attempt}/{max_retries}] Sincronizando: {user_name}")
                
                # Obtener credenciales completas del usuario
                credenciales = CredencialSita.obtener_por_empleado(user_id)
                if not credenciales:
                    logger.error(f"❌ No se encontraron credenciales para {user_name}")
                    return False
                
                # Marcar sincronización en progreso
                self._set_sync_status(user_id, True, None)
                
                # Realizar sincronización
                turnos = obtener_turnos_sita(credenciales)
                if turnos:
                    updated_days = insertar_turnos_en_bd(user_id, turnos)
                    logger.info(f"✅ {user_name}: {updated_days} días actualizados")
                else:
                    logger.warning(f"⚠️ {user_name}: No se encontraron turnos")
                
                # Marcar sincronización completada
                self._set_sync_status(user_id, False, None)
                return True
                
            except requests.exceptions.ReadTimeout as e:
                error_msg = f"Timeout de lectura (intento {attempt}/{max_retries})"
                logger.warning(f"⏰ {user_name}: {error_msg}")
                
                if attempt < max_retries:
                    logger.info(f"⏳ Esperando {retry_delay}s antes del siguiente intento...")
                    self._wait_with_interruption(retry_delay)
                else:
                    logger.error(f"❌ {user_name}: Máximo de reintentos alcanzado por timeout")
                    self._set_sync_status(user_id, False, "Timeout después de 5 intentos")
                    
            except requests.exceptions.ConnectTimeout as e:
                error_msg = f"Timeout de conexión (intento {attempt}/{max_retries})"
                logger.warning(f"⏰ {user_name}: {error_msg}")
                
                if attempt < max_retries:
                    logger.info(f"⏳ Esperando {retry_delay}s antes del siguiente intento...")
                    self._wait_with_interruption(retry_delay)
                else:
                    logger.error(f"❌ {user_name}: Máximo de reintentos alcanzado por timeout de conexión")
                    self._set_sync_status(user_id, False, "Timeout de conexión después de 5 intentos")
                    
            except requests.exceptions.ConnectionError as e:
                logger.error(f"❌ {user_name}: Error de conexión: {e}")
                self._set_sync_status(user_id, False, f"Error de conexión: {str(e)[:200]}")
                break  # No reintentar errores de conexión
                
            except Exception as e:
                logger.error(f"❌ {user_name}: Error inesperado: {e}")
                logger.error(traceback.format_exc())
                self._set_sync_status(user_id, False, f"Error: {str(e)[:200]}")
                break  # No reintentar otros errores
                
        return False
        
    def _set_sync_status(self, user_id: int, in_progress: bool, error_msg: Optional[str]):
        """Actualiza el estado de sincronización del usuario"""
        try:
            if in_progress:
                query = """
                    UPDATE empleados
                    SET sincronizacion_en_progreso = 1,
                        ultimo_error_sincronizacion = NULL
                    WHERE id = %s
                """
                execute_query(query, (user_id,), commit=True)
            else:
                query = """
                    UPDATE empleados
                    SET sincronizacion_en_progreso = 0,
                        ultima_sincronizacion = NOW(),
                        ultimo_error_sincronizacion = %s
                    WHERE id = %s
                """
                execute_query(query, (error_msg, user_id), commit=True)
                
        except Exception as e:
            logger.error(f"❌ Error actualizando estado de sincronización: {e}")


# Instancia global del gestor
auto_sync_manager = AutoSyncManager()

def start_auto_sync():
    """Función para iniciar la sincronización automática"""
    auto_sync_manager.start()

def stop_auto_sync():
    """Función para detener la sincronización automática"""
    auto_sync_manager.stop()

def get_auto_sync_stats():
    """Función para obtener estadísticas"""
    return auto_sync_manager.get_stats()

def signal_handler(signum, frame):
    """Manejador de señales para parada limpia"""
    logger.info("🛑 Señal de parada recibida")
    stop_auto_sync()
    sys.exit(0)

if __name__ == "__main__":
    # Registrar manejadores de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🚀 Iniciando sistema de sincronización automática")
    
    try:
        start_auto_sync()
        
        # Mantener el proceso principal vivo
        while True:
            time.sleep(60)  # Verificar cada minuto
            stats = get_auto_sync_stats()
            if stats['cycle_count'] > 0:
                logger.info(f"📊 Stats: Ciclos: {stats['cycle_count']}, "
                          f"Usuarios: {stats['total_users_synced']}, "
                          f"Errores: {stats['total_errors']}")
                          
    except KeyboardInterrupt:
        logger.info("👋 Deteniendo por interrupción del usuario")
    finally:
        stop_auto_sync()