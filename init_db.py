import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "base_datos.db")

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expedientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            materia TEXT NOT NULL,
            juzgado TEXT NOT NULL,
            demandante TEXT NOT NULL,
            demandado TEXT NOT NULL,
            fecha_concesion TEXT NOT NULL,
            fecha_limite TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Pendiente',
            archivo_pdf TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expediente_id INTEGER,
            codigo TEXT,
            accion TEXT NOT NULL,
            detalle TEXT NOT NULL,
            usuario TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("Base de datos inicializada correctamente.")

if __name__ == "__main__":
    init_database()