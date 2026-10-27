from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)

CARPETA_SUBIDAS = os.path.join(app.root_path, 'uploads')
os.makedirs(CARPETA_SUBIDAS, exist_ok=True)
app.config['UPLOAD_FOLDER'] = CARPETA_SUBIDAS

def get_db_connection():
    conn = sqlite3.connect('base_datos.db')
    conn.row_factory = sqlite3.Row
    return conn

def generar_siguiente_expediente(conn):
    ultimo = conn.execute('SELECT MAX(id) FROM expedientes').fetchone()[0]
    siguiente_numero = (ultimo or 0) + 1
    return f"EXP-2026-{siguiente_numero:04d}"

def formatear_fecha_corta():
    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Set', 'Oct', 'Nov', 'Dic']
    ahora = datetime.now()
    return f"{ahora.day} {meses[ahora.month - 1]}"

def procesar_plazos_y_recordatorios(expedientes_raw):
    recordatorios = []
    alertas_vencimiento = []
    alertas_completas = []
    dias_clave = set()
    hoy = datetime.now().date()
    agenda_dias = {d: [] for d in range(1, 32)}

    for exp in expedientes_raw:
        fecha_str = exp['fecha_resolucion']
        try:
            f_res = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except Exception:
            continue

        f_plazo = f_res + timedelta(days=15)
        dias_clave.add(f_res.day)
        dias_clave.add(f_plazo.day)

        if 1 <= f_res.day <= 31:
            agenda_dias[f_res.day].append({
                'tipo': 'Resolución Concedida/Dictada',
                'expediente': exp['numero_expediente'],
                'medida': exp['tipo_medida'],
                'organo': exp['organo_jurisdiccional'],
                'responsable': exp['responsable'],
                'estado': exp['estado'],
                'color': '#0284c7'
            })

        if exp['estado'] in ['Pendiente', 'En seguimiento', 'Concedida', 'En revisión']:
            dias_restantes = (f_plazo - hoy).days
            if 1 <= f_plazo.day <= 31:
                agenda_dias[f_plazo.day].append({
                    'tipo': 'Límite de Ejecución Procesal',
                    'expediente': exp['numero_expediente'],
                    'medida': exp['tipo_medida'],
                    'organo': exp['organo_jurisdiccional'],
                    'responsable': exp['responsable'],
                    'estado': exp['estado'],
                    'color': '#e11d48'
                })

            recordatorios.append({
                'expediente': exp['numero_expediente'],
                'medida': exp['tipo_medida'],
                'fecha_vencimiento': f_plazo.strftime("%d/%m/%Y"),
                'dia': f_plazo.day,
                'dias_restantes': dias_restantes,
                'estado': exp['estado'],
                'responsable': exp['responsable']
            })

            # Módulo 4: Clasificación didáctica de alertas
            if dias_restantes < 0:
                nivel = "Crítica"
                detalle = f"El plazo legal de ejecución procesal venció hace {abs(dias_restantes)} días naturales."
                alertas_vencimiento.append(f"¡Vencido! Plazo de ejecución venció hace {abs(dias_restantes)} días en {exp['numero_expediente']}")
            elif dias_restantes <= 5:
                nivel = "Urgente"
                detalle = f"Faltan solo {dias_restantes} días para el término del plazo de ejecución."
                alertas_vencimiento.append(f"¡Atención! Plazo de ejecución vence en {dias_restantes} días en {exp['numero_expediente']}")
            else:
                nivel = "Preventiva"
                detalle = f"Plazo en curso regular (quedan {dias_restantes} días para vencimiento)."

            alertas_completas.append({
                'id': exp['id'],
                'expediente': exp['numero_expediente'],
                'organo': exp['organo_jurisdiccional'],
                'medida': exp['tipo_medida'],
                'responsable': exp['responsable'],
                'estado': exp['estado'],
                'fecha_limite': f_plazo.strftime("%d/%m/%Y"),
                'nivel': nivel,
                'detalle': detalle
            })

    return recordatorios, alertas_vencimiento, list(dias_clave), agenda_dias, alertas_completas

@app.route('/', methods=['GET', 'POST'])
def dashboard():
    conn = get_db_connection()

    if request.method == 'POST':
        num = request.form.get('numero_expediente')
        organo_select = request.form.get('organo_jurisdiccional')
        organo_manual = request.form.get('organo_manual', '').strip()
        organo = organo_manual if organo_select == 'Otro' and organo_manual else organo_select

        medida = request.form.get('tipo_medida')
        estado = request.form.get('estado')
        fecha_res = request.form.get('fecha_resolucion')
        
        titulo_resp = request.form.get('titulo_responsable', '').strip()
        nombre_resp = request.form.get('responsable', '').strip()
        responsable_completo = f"{titulo_resp} {nombre_resp}" if titulo_resp != 'Ninguno' else nombre_resp

        nombre_archivo = None
        if 'archivo_documento' in request.files:
            archivo = request.files['archivo_documento']
            if archivo and archivo.filename != '':
                nombre_seguro = secure_filename(archivo.filename)
                nombre_archivo = f"{num}_{nombre_seguro}"
                archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo))

        if num and organo and responsable_completo:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO expedientes (numero_expediente, organo_jurisdiccional, tipo_medida, estado, fecha_resolucion, responsable, documento, ultima_actualizacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Reciente')
            ''', (num, organo, medida, estado, fecha_res, responsable_completo, nombre_archivo))
            nuevo_id = cursor.lastrowid

            conn.execute('''
                INSERT INTO actuaciones (id_expediente, fecha, descripcion, responsable)
                VALUES (?, ?, ?, ?)
            ''', (nuevo_id, formatear_fecha_corta(), f"Registro de medida ({medida}) en estado {estado}", f"{responsable_completo} ({num})"))

            conn.commit()
            conn.close()
            return redirect(url_for('dashboard'))

    # Parámetros de navegación: 'dashboard', 'calendario', 'alertas', 'historial'
    vista = request.args.get('vista', 'dashboard')
    estado_filtro = request.args.get('estado', 'Todos')
    dia_calendario = request.args.get('dia', '').strip()

    todos_exp = conn.execute('SELECT * FROM expedientes ORDER BY id DESC').fetchall()
    recordatorios, alertas_vencimiento, dias_con_actividad, agenda_dias, alertas_completas = procesar_plazos_y_recordatorios(todos_exp)

    # Filtrar expedientes para la tabla
    if dia_calendario:
        dia_int = int(dia_calendario)
        expedientes_filtrados = []
        for exp in todos_exp:
            partes = exp['fecha_resolucion'].split('-')
            if len(partes) == 3 and int(partes[2]) == dia_int:
                expedientes_filtrados.append(exp)
                continue
            try:
                f_res = datetime.strptime(exp['fecha_resolucion'], "%Y-%m-%d").date()
                f_plazo = f_res + timedelta(days=15)
                if f_plazo.day == dia_int:
                    expedientes_filtrados.append(exp)
            except Exception:
                pass
        expedientes = expedientes_filtrados
    elif estado_filtro == 'Seguimiento_Procesal':
        expedientes = conn.execute('SELECT * FROM expedientes WHERE estado IN ("Pendiente", "En seguimiento", "En revisión") ORDER BY id DESC').fetchall()
    elif estado_filtro != 'Todos':
        expedientes = conn.execute('SELECT * FROM expedientes WHERE estado = ? ORDER BY id DESC', (estado_filtro,)).fetchall()
    else:
        expedientes = todos_exp

    total_exp = conn.execute('SELECT COUNT(*) FROM expedientes').fetchone()[0]
    pendientes = conn.execute('SELECT COUNT(*) FROM expedientes WHERE estado = "Pendiente"').fetchone()[0]
    en_seguimiento = conn.execute('SELECT COUNT(*) FROM expedientes WHERE estado = "En seguimiento"').fetchone()[0]
    ejecutadas = conn.execute('SELECT COUNT(*) FROM expedientes WHERE estado = "Ejecutada"').fetchone()[0]

    alertas_inactivas = conn.execute('SELECT numero_expediente FROM expedientes WHERE estado = "En seguimiento" LIMIT 2').fetchall()

    # Módulo 5: Historial (completo para la vista dedicada, resumido para el dashboard)
    historial_completo = conn.execute('SELECT * FROM actuaciones ORDER BY id DESC').fetchall()
    historial_resumen = historial_completo[:5]

    siguiente_exp = generar_siguiente_expediente(conn)
    conn.close()

    return render_template(
        'index.html',
        vista=vista,
        expedientes=expedientes,
        estado_filtro=estado_filtro,
        dia_calendario=dia_calendario,
        dias_con_actividad=dias_con_actividad,
        agenda_dias=agenda_dias,
        recordatorios=recordatorios,
        total_exp=total_exp,
        pendientes=pendientes,
        en_seguimiento=en_seguimiento,
        ejecutadas=ejecutadas,
        alertas_vencimiento=alertas_vencimiento,
        alertas_inactivas=alertas_inactivas,
        alertas_completas=alertas_completas,
        historial=historial_resumen,
        historial_completo=historial_completo,
        siguiente_exp=siguiente_exp
    )

@app.route('/editar/<int:id>', methods=['POST'])
def editar(id):
    conn = get_db_connection()
    nuevo_estado = request.form.get('estado')
    
    titulo_resp = request.form.get('titulo_responsable', '').strip()
    nombre_resp = request.form.get('responsable', '').strip()
    responsable_completo = f"{titulo_resp} {nombre_resp}" if titulo_resp != 'Ninguno' else nombre_resp

    exp = conn.execute('SELECT numero_expediente, estado FROM expedientes WHERE id = ?', (id,)).fetchone()
    num = exp['numero_expediente'] if exp else 'EXP'
    estado_anterior = exp['estado'] if exp else ''

    nombre_archivo = None
    if 'archivo_documento' in request.files:
        archivo = request.files['archivo_documento']
        if archivo and archivo.filename != '':
            nombre_seguro = secure_filename(archivo.filename)
            nombre_archivo = f"{num}_{nombre_seguro}"
            archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo))

    if nombre_archivo:
        conn.execute('''
            UPDATE expedientes 
            SET estado = ?, responsable = ?, documento = ?, ultima_actualizacion = 'Actualizado hoy'
            WHERE id = ?
        ''', (nuevo_estado, responsable_completo, nombre_archivo, id))
    else:
        conn.execute('''
            UPDATE expedientes 
            SET estado = ?, responsable = ?, ultima_actualizacion = 'Actualizado hoy'
            WHERE id = ?
        ''', (nuevo_estado, responsable_completo, id))

    descripcion_actuacion = f"Cambio de estado: {estado_anterior} ➔ {nuevo_estado}"
    if nombre_archivo:
        descripcion_actuacion += " (Documento adjunto actualizado)"

    conn.execute('''
        INSERT INTO actuaciones (id_expediente, fecha, descripcion, responsable)
        VALUES (?, ?, ?, ?)
    ''', (id, formatear_fecha_corta(), descripcion_actuacion, f"{responsable_completo} ({num})"))

    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/uploads/<path:filename>')
def ver_documento(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    conn = get_db_connection()
    doc = conn.execute('SELECT documento FROM expedientes WHERE id = ?', (id,)).fetchone()
    if doc and doc['documento']:
        ruta_archivo = os.path.join(app.config['UPLOAD_FOLDER'], doc['documento'])
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)

    conn.execute('DELETE FROM actuaciones WHERE id_expediente = ?', (id,))
    conn.execute('DELETE FROM expedientes WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)