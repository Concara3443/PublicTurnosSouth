#!/usr/bin/env python
import os
import sys
import bcrypt
import getpass
import pymysql
from dotenv import load_dotenv

# Añadir el directorio raíz al path
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Cargar variables de entorno
load_dotenv()

# Configuración de base de datos
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

def crear_tablas():
    """Crea las tablas necesarias para el sistema de usuarios"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Crear tabla de empleados
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id INT AUTO_INCREMENT PRIMARY KEY,
            numero_empleado VARCHAR(20) NOT NULL UNIQUE,
            nombre_completo VARCHAR(100) NOT NULL,
            email VARCHAR(100),
            password_hash VARCHAR(255) NOT NULL,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultimo_acceso TIMESTAMP NULL,
            activo TINYINT(1) DEFAULT 1,
            es_admin TINYINT(1) DEFAULT 0,
            INDEX idx_numero_empleado (numero_empleado),
            INDEX idx_activo (activo)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        
        # Crear tabla para la lista blanca de empleados
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS empleados_whitelist (
            id INT AUTO_INCREMENT PRIMARY KEY,
            numero_empleado VARCHAR(20) NOT NULL UNIQUE,
            nombre_completo VARCHAR(100),
            email VARCHAR(100),
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_registro TIMESTAMP NULL,
            registrado TINYINT(1) DEFAULT 0,
            INDEX idx_numero_empleado (numero_empleado),
            INDEX idx_registrado (registrado)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        
        # Crear tabla de turnos para empleados
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS turnos_empleado (
            id INT AUTO_INCREMENT PRIMARY KEY,
            empleado_id INT NOT NULL,
            dia DATETIME NOT NULL,
            turno JSON NULL,
            activo TINYINT(1) DEFAULT 1,
            google_event_ids JSON NULL,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE,
            INDEX idx_empleado_dia (empleado_id, dia),
            INDEX idx_dia (dia),
            INDEX idx_activo (activo)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        
        # Crear tabla para credenciales SITA
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS credenciales_sita (
            id INT AUTO_INCREMENT PRIMARY KEY,
            empleado_id INT NOT NULL,
            sita_username VARCHAR(20) NOT NULL,
            sita_password_encrypted TEXT NOT NULL,
            site_id VARCHAR(100) NOT NULL,
            cvation_tenantid VARCHAR(100) NOT NULL,
            roster_url TEXT NOT NULL,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE,
            UNIQUE INDEX idx_empleado_id (empleado_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        
        # Commit cambios
        conn.commit()
        print("✅ Tablas creadas correctamente.")
    except Exception as e:
        print(f"❌ Error al crear tablas: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def crear_usuario_admin():
    """Crea un usuario administrador"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Verificar si ya existe un admin
        cursor.execute("SELECT COUNT(*) FROM empleados WHERE es_admin = 1")
        if cursor.fetchone()[0] > 0:
            print("ℹ️ Ya existe un usuario administrador.")
            return
        
        # Pedir datos del nuevo administrador
        print("\n--- Creación de Usuario Administrador ---")
        numero_empleado = input("Número de empleado: ")
        nombre_completo = input("Nombre completo: ")
        email = input("Email (opcional): ")
        
        while True:
            password = getpass.getpass("Contraseña: ")
            confirm = getpass.getpass("Confirmar contraseña: ")
            
            if password == confirm:
                break
            print("❌ Las contraseñas no coinciden. Inténtalo de nuevo.")
        
        # Generar hash de la contraseña
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Insertar usuario admin
        cursor.execute("""
        INSERT INTO empleados 
            (numero_empleado, nombre_completo, email, password_hash, es_admin) 
        VALUES 
            (%s, %s, %s, %s, 1)
        """, (numero_empleado, nombre_completo, email, password_hash))
        
        # Commit cambios
        conn.commit()
        print(f"✅ Usuario administrador '{numero_empleado}' creado correctamente.")
    except Exception as e:
        print(f"❌ Error al crear usuario administrador: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def migrar_datos_existentes():
    """Migra datos de la tabla turnos original a turnos_empleado"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Verificar si hay un usuario administrador
        cursor.execute("SELECT id FROM empleados WHERE es_admin = 1 LIMIT 1")
        admin = cursor.fetchone()
        
        if not admin:
            print("❌ No se puede migrar datos sin un usuario admin. Crea uno primero.")
            return
        
        admin_id = admin[0]
        
        # Verificar si ya hay datos en turnos_empleado
        cursor.execute("SELECT COUNT(*) FROM turnos_empleado")
        if cursor.fetchone()[0] > 0:
            answer = input("Ya existen datos en turnos_empleado. ¿Quieres continuar? (s/n): ")
            if answer.lower() != 's':
                return
        
        # Comprobar si existe la tabla turnos
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = 'turnos'
        """, (DB_CONFIG['database'],))
        
        if cursor.fetchone()[0] == 0:
            print("ℹ️ La tabla turnos no existe, no hay datos que migrar.")
            return
        
        # Obtener datos de la tabla turnos
        cursor.execute("SELECT id, dia, turno, activo, google_event_ids FROM turnos WHERE activo = 1")
        turnos = cursor.fetchall()
        
        if not turnos:
            print("ℹ️ No hay turnos activos para migrar.")
            return
        
        # Insertar en turnos_empleado
        for turno in turnos:
            cursor.execute("""
            INSERT INTO turnos_empleado 
                (empleado_id, dia, turno, activo, google_event_ids) 
            VALUES 
                (%s, %s, %s, %s, %s)
            """, (admin_id, turno[1], turno[2], turno[3], turno[4]))
        
        # Commit cambios
        conn.commit()
        print(f"✅ Se migraron {len(turnos)} turnos al usuario administrador.")
    except Exception as e:
        print(f"❌ Error al migrar datos: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def main():
    """Función principal"""
    print("=== Configuración de Sistema de Usuarios ===")
    
    # Crear tablas
    crear_tablas()
    
    # Crear usuario administrador
    crear_usuario_admin()
    
    # Migrar datos existentes
    migrar_datos_existentes()
    
    print("\n✅ Configuración completada.")

if __name__ == "__main__":
    main()