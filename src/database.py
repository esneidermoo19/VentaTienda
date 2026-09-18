import sqlite3
import sys
from datetime import datetime

import os

if getattr(sys, 'frozen', False):
    # Ejecutándose como .exe compilado: la BD va junto al ejecutable
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    # Desarrollo normal: subir un nivel desde src/ hasta la raíz del proyecto
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_PATH = os.path.join(_BASE_DIR, "data", "ventatienda_datos.db")

# Asegurar que el directorio data/ exista
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def _conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def iniciar_db():
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL, precio REAL NOT NULL,
        stock INTEGER NOT NULL,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        categoria TEXT DEFAULT 'General',
        codigo_barras TEXT)""")
    # Migraciones para DBs antiguas
    cursor.execute("PRAGMA table_info(inventario)")
    columnas = [row[1] for row in cursor.fetchall()]
    if "fecha_registro" not in columnas:
        cursor.execute("ALTER TABLE inventario ADD COLUMN fecha_registro TEXT")
        cursor.execute("UPDATE inventario SET fecha_registro = datetime('now') WHERE fecha_registro IS NULL")
    if "categoria" not in columnas:
        cursor.execute("ALTER TABLE inventario ADD COLUMN categoria TEXT DEFAULT 'General'")
    if "codigo_barras" not in columnas:
        cursor.execute("ALTER TABLE inventario ADD COLUMN codigo_barras TEXT")
    # Índice UNIQUE parcial (ignorar NULLs para permitir múltiples sin código)
    try:
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_codigo_barras "
            "ON inventario(codigo_barras) WHERE codigo_barras IS NOT NULL"
        )
    except Exception:
        pass
    cursor.execute("""CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER NOT NULL, cantidad INTEGER NOT NULL,
        total REAL NOT NULL, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metodo_pago TEXT DEFAULT 'Efectivo',
        FOREIGN KEY (producto_id) REFERENCES inventario(id))""")
    # Migración para agregar metodo_pago a DBs antiguas
    cursor.execute("PRAGMA table_info(ventas)")
    columnas_ventas = [row[1] for row in cursor.fetchall()]
    if "metodo_pago" not in columnas_ventas:
        cursor.execute("ALTER TABLE ventas ADD COLUMN metodo_pago TEXT DEFAULT 'Efectivo'")
    
    # Índices para optimizar consultas
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_producto ON ventas(producto_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventario_categoria ON inventario(categoria)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventario_nombre ON inventario(nombre)")
    
    conn.commit()
    conn.close()
    
    iniciar_tabla_config()


def iniciar_tabla_config():
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS configuracion (
        id INTEGER PRIMARY KEY,
        nombre_negocio TEXT,
        nit_rut TEXT,
        telefono TEXT,
        direccion TEXT,
        margen_ganancia REAL DEFAULT 35.0,
        stock_minimo INTEGER DEFAULT 5)""")
    
    cursor.execute("SELECT COUNT(*) FROM configuracion")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO configuracion (id, nombre_negocio, nit_rut, telefono, direccion, margen_ganancia, stock_minimo) VALUES (1, 'Mi Negocio', '', '', '', 35.0, 5)")
        
    conn.commit()
    conn.close()


def obtener_config():
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM configuracion WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return row


def guardar_config(datos):
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute("""UPDATE configuracion 
                      SET nombre_negocio = ?, nit_rut = ?, telefono = ?, direccion = ?, margen_ganancia = ?, stock_minimo = ? 
                      WHERE id = 1""", 
                   (datos.get('nombre_negocio') or 'Mi Negocio',
                    datos.get('nit_rut') or '',
                    datos.get('telefono') or '',
                    datos.get('direccion') or '',
                    datos.get('margen_ganancia') or 35.0,
                    datos.get('stock_minimo') or 5))
    conn.commit()
    conn.close()


def obtener_productos(filtro=""):
    conn = _conectar()
    cursor = conn.cursor()
    if filtro.strip():
        cursor.execute(
            "SELECT id, nombre, precio, stock, COALESCE(date(fecha_registro, 'localtime'), 'Sin fecha'), categoria, COALESCE(codigo_barras, '') "
            "FROM inventario WHERE nombre LIKE ? OR categoria LIKE ? OR codigo_barras LIKE ? ORDER BY nombre ASC",
            (f"%{filtro}%", f"%{filtro}%", f"%{filtro}%")
        )
    else:
        cursor.execute(
            "SELECT id, nombre, precio, stock, COALESCE(date(fecha_registro, 'localtime'), 'Sin fecha'), categoria, COALESCE(codigo_barras, '') "
            "FROM inventario ORDER BY nombre ASC"
        )
    rows = cursor.fetchall()
    conn.close()
    return rows


def obtener_producto_por_id(producto_id):
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, precio, stock FROM inventario WHERE id = ?", (producto_id,))
    prod = cursor.fetchone()
    conn.close()
    return prod


def obtener_producto_por_codigo_barras(codigo):
    """Busca un producto con coincidencia EXACTA del código de barras."""
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, nombre, precio, stock FROM inventario WHERE codigo_barras = ?",
        (codigo.strip(),)
    )
    prod = cursor.fetchone()
    conn.close()
    return prod


def insertar_producto(nombre, precio, stock, categoria="General", codigo_barras=None):
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO inventario (nombre, precio, stock, categoria, fecha_registro, codigo_barras) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)",
        (nombre, precio, stock, categoria, codigo_barras if codigo_barras and codigo_barras.strip() else None)
    )
    conn.commit()
    conn.close()


def actualizar_producto(id_producto, nombre, precio, stock, categoria="General", codigo_barras=None):
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE inventario SET nombre = ?, precio = ?, stock = ?, categoria = ?, fecha_registro = CURRENT_TIMESTAMP, codigo_barras = ? WHERE id = ?",
        (nombre, precio, stock, categoria, codigo_barras if codigo_barras and codigo_barras.strip() else None, id_producto)
    )
    conn.commit()
    conn.close()


def eliminar_producto(id_producto):
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventario WHERE id = ?", (id_producto,))
    conn.commit()
    conn.close()


def actualizar_stock(id_producto, nuevo_stock):
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute("UPDATE inventario SET stock = ?, fecha_registro = CURRENT_TIMESTAMP WHERE id = ?", (nuevo_stock, id_producto))
    conn.commit()
    conn.close()


def registrar_venta(producto_id, cantidad, total, metodo_pago="Efectivo"):
    conn = _conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE inventario SET stock = stock - ? WHERE id = ?", (cantidad, producto_id))
        cursor.execute("INSERT INTO ventas (producto_id, cantidad, total, fecha, metodo_pago) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)", (producto_id, cantidad, total, metodo_pago))
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


def obtener_ventas():
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute("""SELECT v.id, COALESCE(i.nombre, 'Producto Eliminado'), v.cantidad, v.total, datetime(v.fecha, 'localtime') as fecha_local FROM ventas v LEFT JOIN inventario i ON v.producto_id = i.id ORDER BY v.fecha DESC""")
    rows = cursor.fetchall()
    conn.close()
    return rows


def obtener_estadisticas():
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(total) FROM ventas")
    total_ingresos = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT SUM(cantidad) FROM ventas")
    total_unidades = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM ventas")
    total_transacciones = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT margen_ganancia FROM configuracion WHERE id = 1")
    margen_row = cursor.fetchone()
    margen = (margen_row[0] / 100.0) if margen_row else 0.35
    
    conn.close()
    return {"total_ingresos": total_ingresos, "total_unidades": total_unidades, "total_transacciones": total_transacciones, "ganancia_estimada": total_ingresos * margen}


def obtener_ventas_por_producto(limite=5):
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(i.nombre, 'Producto Eliminado'), SUM(v.total) as total_ventas FROM ventas v LEFT JOIN inventario i ON v.producto_id = i.id GROUP BY COALESCE(i.nombre, 'Producto Eliminado') ORDER BY total_ventas DESC LIMIT ?", (limite,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def obtener_ventas_por_categoria(limite=5):
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(i.categoria, 'Sin Categoría'), SUM(v.total) as total_ventas FROM ventas v LEFT JOIN inventario i ON v.producto_id = i.id GROUP BY COALESCE(i.categoria, 'Sin Categoría') ORDER BY total_ventas DESC LIMIT ?", (limite,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def obtener_ventas_diarias(limite=24):
    conn = _conectar()
    cursor = conn.cursor()
    # Ventas de las últimas 24 horas agrupadas por hora
    cursor.execute("SELECT strftime('%H:00', datetime(fecha, 'localtime')) as dia, SUM(total) as total_dia FROM ventas WHERE datetime(fecha, 'localtime') >= datetime('now', '-1 day', 'localtime') GROUP BY dia ORDER BY dia ASC LIMIT ?", (limite,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def obtener_ventas_para_exportar():
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT v.id, COALESCE(i.nombre, 'Producto Eliminado'), COALESCE(i.categoria, 'Sin Categoría'), v.cantidad, v.total, v.fecha, COALESCE(v.metodo_pago, 'Efectivo') FROM ventas v LEFT JOIN inventario i ON v.producto_id = i.id ORDER BY v.fecha DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows
