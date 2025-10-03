#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para configurar el modo demo en el sistema TurnosSouth
- Agrega columnas es_demo y vinculado_a_empleado_id a la tabla empleados
- Crea usuario DEMO vinculado al usuario real 022428
- Crea usuarios dummy para el panel de administración
"""

import sys
import os
import io

# Configurar encoding para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar el directorio web al path para importar módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web'))

from database import get_db_connection
import bcrypt

def setup_demo_mode():
    """Configura el modo demo en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        print("=" * 60)
        print("CONFIGURACIÓN DEL MODO DEMO - TurnosSouth")
        print("=" * 60)

        # 1. Agregar columnas a la tabla empleados si no existen
        print("\n1. Verificando estructura de la tabla empleados...")

        # Verificar si la columna es_demo existe
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'empleados'
            AND COLUMN_NAME = 'es_demo'
        """)
        result = cursor.fetchone()

        if result['count'] == 0:
            print("   - Agregando columna 'es_demo'...")
            cursor.execute("""
                ALTER TABLE empleados
                ADD COLUMN es_demo TINYINT(1) DEFAULT 0 NOT NULL
            """)
            print("   ✓ Columna 'es_demo' agregada")
        else:
            print("   ✓ Columna 'es_demo' ya existe")

        # Verificar si la columna vinculado_a_empleado_id existe
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'empleados'
            AND COLUMN_NAME = 'vinculado_a_empleado_id'
        """)
        result = cursor.fetchone()

        if result['count'] == 0:
            print("   - Agregando columna 'vinculado_a_empleado_id'...")
            cursor.execute("""
                ALTER TABLE empleados
                ADD COLUMN vinculado_a_empleado_id INT NULL,
                ADD CONSTRAINT fk_vinculado_empleado
                FOREIGN KEY (vinculado_a_empleado_id)
                REFERENCES empleados(id) ON DELETE SET NULL
            """)
            print("   ✓ Columna 'vinculado_a_empleado_id' agregada")
        else:
            print("   ✓ Columna 'vinculado_a_empleado_id' ya existe")

        conn.commit()

        # 2. Obtener ID del usuario 022428
        print("\n2. Buscando usuario real 022428...")
        cursor.execute("""
            SELECT id, nombre_completo
            FROM empleados
            WHERE numero_empleado = '022428'
        """)
        usuario_real = cursor.fetchone()

        if not usuario_real:
            print("   ✗ ERROR: No se encontró el usuario 022428")
            print("   Por favor, asegúrate de que el usuario existe antes de ejecutar este script.")
            return False

        usuario_real_id = usuario_real['id']
        print(f"   ✓ Usuario encontrado: {usuario_real['nombre_completo']} (ID: {usuario_real_id})")

        # 3. Crear o actualizar usuario DEMO
        print("\n3. Configurando usuario DEMO...")
        cursor.execute("""
            SELECT id FROM empleados WHERE numero_empleado = 'DEMO'
        """)
        demo_exists = cursor.fetchone()

        # Generar contraseña para el usuario DEMO (aunque el acceso será automático)
        demo_password = bcrypt.hashpw('demo123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        if demo_exists:
            print("   - Actualizando usuario DEMO existente...")
            cursor.execute("""
                UPDATE empleados
                SET vinculado_a_empleado_id = %s,
                    es_demo = 1,
                    es_admin = 1,
                    activo = 1,
                    nombre_completo = 'Usuario Demo (Portfolio)',
                    email = 'demo@turnosouth.local'
                WHERE numero_empleado = 'DEMO'
            """, (usuario_real_id,))
            print("   ✓ Usuario DEMO actualizado")
        else:
            print("   - Creando usuario DEMO...")
            cursor.execute("""
                INSERT INTO empleados
                (numero_empleado, nombre_completo, email, password_hash,
                 es_admin, es_demo, vinculado_a_empleado_id, activo)
                VALUES ('DEMO', 'Usuario Demo (Portfolio)', 'demo@turnosouth.local',
                        %s, 1, 1, %s, 1)
            """, (demo_password, usuario_real_id))
            print("   ✓ Usuario DEMO creado")

        conn.commit()

        # 4. Crear usuarios dummy para el panel admin
        print("\n4. Creando usuarios dummy para panel admin...")

        usuarios_dummy = [
            ('DEMO001', 'Ana García Martínez', 'ana.garcia@demo.local'),
            ('DEMO002', 'Carlos Rodríguez López', 'carlos.rodriguez@demo.local'),
            ('DEMO003', 'María Fernández Sánchez', 'maria.fernandez@demo.local'),
            ('DEMO004', 'Juan Pérez González', 'juan.perez@demo.local'),
            ('DEMO005', 'Laura Martín Díaz', 'laura.martin@demo.local'),
            ('DEMO006', 'David Torres Ruiz', 'david.torres@demo.local'),
        ]

        dummy_password = bcrypt.hashpw('dummy123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        for numero_emp, nombre, email in usuarios_dummy:
            cursor.execute("""
                SELECT id FROM empleados WHERE numero_empleado = %s
            """, (numero_emp,))
            exists = cursor.fetchone()

            if not exists:
                cursor.execute("""
                    INSERT INTO empleados
                    (numero_empleado, nombre_completo, email, password_hash,
                     es_admin, es_demo, activo)
                    VALUES (%s, %s, %s, %s, 0, 1, 1)
                """, (numero_emp, nombre, email, dummy_password))
                print(f"   ✓ Usuario dummy creado: {nombre} ({numero_emp})")
            else:
                print(f"   - Usuario dummy ya existe: {nombre} ({numero_emp})")

        conn.commit()

        # 5. Crear entradas de whitelist demo (opcional)
        print("\n5. Creando entradas demo en whitelist...")

        # Verificar si la tabla whitelist existe
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'empleados_whitelist'
        """)
        result = cursor.fetchone()

        if result['count'] > 0:
            whitelist_demo = [
                ('DEMO101', 'Pedro Gómez Demo', 'pedro.gomez@demo.local'),
                ('DEMO102', 'Elena Ruiz Demo', 'elena.ruiz@demo.local'),
                ('DEMO103', 'Roberto Sanz Demo', 'roberto.sanz@demo.local'),
            ]

            for numero_emp, nombre, email in whitelist_demo:
                cursor.execute("""
                    SELECT numero_empleado FROM empleados_whitelist
                    WHERE numero_empleado = %s
                """, (numero_emp,))
                exists = cursor.fetchone()

                if not exists:
                    cursor.execute("""
                        INSERT INTO empleados_whitelist
                        (numero_empleado, nombre_completo, email)
                        VALUES (%s, %s, %s)
                    """, (numero_emp, nombre, email))
                    print(f"   ✓ Entrada whitelist creada: {nombre} ({numero_emp})")
                else:
                    print(f"   - Entrada whitelist ya existe: {nombre} ({numero_emp})")

            conn.commit()
        else:
            print("   - Tabla empleados_whitelist no encontrada, saltando...")

        print("\n" + "=" * 60)
        print("✓ CONFIGURACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        print("\nResumen:")
        print(f"  • Usuario DEMO creado/actualizado")
        print(f"  • Vinculado al usuario 022428 (ID: {usuario_real_id})")
        print(f"  • {len(usuarios_dummy)} usuarios dummy creados")
        print(f"  • Acceso demo disponible en: /auth/demo-login")
        print("\nNota: El usuario DEMO verá los turnos actualizados del usuario 022428")
        print("      en tiempo real sin duplicación de datos.")
        print("=" * 60)

        return True

    except Exception as e:
        conn.rollback()
        print(f"\n✗ ERROR durante la configuración: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    success = setup_demo_mode()
    sys.exit(0 if success else 1)
