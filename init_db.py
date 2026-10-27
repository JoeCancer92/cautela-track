import sqlite3

conexion = sqlite3.connect('base_datos.db')
cursor = conexion.cursor()

cursor.execute('DROP TABLE IF EXISTS actuaciones')
cursor.execute('DROP TABLE IF EXISTS expedientes')

# Tabla de Expedientes
cursor.execute('''
    CREATE TABLE expedientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_expediente TEXT NOT NULL,
        organo_jurisdiccional TEXT NOT NULL,
        tipo_medida TEXT NOT NULL,
        estado TEXT NOT NULL,
        fecha_resolucion TEXT NOT NULL,
        responsable TEXT NOT NULL,
        documento TEXT DEFAULT NULL,
        ultima_actualizacion TEXT DEFAULT 'Hoy'
    )
''')

# Tabla del Módulo 5: Historial y Trazabilidad de Actuaciones
cursor.execute('''
    CREATE TABLE actuaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_expediente INTEGER,
        fecha TEXT NOT NULL,
        descripcion TEXT NOT NULL,
        responsable TEXT NOT NULL,
        FOREIGN KEY (id_expediente) REFERENCES expedientes(id)
    )
''')

# Expedientes de demostración iniciales
casos_iniciales = [
    ('EXP-2023-0891', '1º Juzgado Civil', 'Embargo', 'Pendiente', '2023-11-10', 'Dra. María Ramos', None, 'Fechas recientes'),
    ('EXP-2023-0902', '2º Juzgado Comercial', 'Secuestro', 'En seguimiento', '2023-12-05', 'Dr. Carlos Mendoza', None, 'Fechas recientes'),
    ('EXP-2023-1039', '2º Juzgado Comercial', 'Inscripción', 'Ejecutada', '2023-10-15', 'Dr. Alejandro Soto', None, 'Fechas 15 días')
]

cursor.executemany('''
    INSERT INTO expedientes (numero_expediente, organo_jurisdiccional, tipo_medida, estado, fecha_resolucion, responsable, documento, ultima_actualizacion)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', casos_iniciales)

# Actuaciones de demostración iniciales
actuaciones_iniciales = [
    (1, '26 Oct', 'Medida concedida e inicio de trámite', 'Dra. María Ramos (EXP-2023-0891)'),
    (2, '26 Oct', 'Emisión de Oficio de embargo judicial', 'Dr. Carlos Mendoza (EXP-2023-0902)'),
    (3, '25 Oct', 'Verificación de auto resolutivo', 'Dr. Alejandro Soto (EXP-2023-1039)')
]

cursor.executemany('''
    INSERT INTO actuaciones (id_expediente, fecha, descripcion, responsable)
    VALUES (?, ?, ?, ?)
''', actuaciones_iniciales)

conexion.commit()
conexion.close()
print("¡Base de datos actualizada con Módulo 4 (Alertas) y Módulo 5 (Historial)!")