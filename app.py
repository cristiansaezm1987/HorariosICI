import os
import csv
import sqlite3
import re
import tempfile
import shutil
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

app = Flask(__name__, static_folder='static', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', 'uautonoma_secreto_2026')
APP_PASSWORD = os.environ.get('APP_PASSWORD', 'UAutonoma2026')

@app.before_request
def check_auth():
    # Only protect API routes, let static files through (like index.html which has the login UI)
    if request.path.startswith('/api/') and request.path not in ['/api/login', '/api/check-auth']:
        if not session.get('logged_in'):
            return jsonify({'success': False, 'message': 'No autorizado'}), 401

@app.after_request
def add_cache_headers(response):
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@app.route('/api/check-auth', methods=['GET'])
def check_auth_endpoint():
    return jsonify({'logged_in': bool(session.get('logged_in'))})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    password = data.get('password')
    
    if password == APP_PASSWORD:
        session['logged_in'] = True
        return jsonify({'success': True, 'message': 'Inicio de sesión exitoso'})
    return jsonify({'success': False, 'message': 'Contraseña incorrecta'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    return jsonify({'success': True})

# For Serverless environments (like Vercel), the root is read-only.
# We copy the database to /tmp so it can be read/written during the instance lifecycle.
DATABASE_FILE = 'planificacion.db'
if os.environ.get('VERCEL') or not os.access('.', os.W_OK):
    tmp_db = os.path.join(tempfile.gettempdir(), 'planificacion.db')
    if not os.path.exists(tmp_db) and os.path.exists(DATABASE_FILE):
        shutil.copy2(DATABASE_FILE, tmp_db)
    DATABASE_FILE = tmp_db

# Define standard columns and their SQL types
# We map CSV column names to safe SQL column names
COLUMN_MAPPING = {
    'CODIGO_PERIODO': 'CODIGO_PERIODO TEXT',
    'CODIGO_PROGRAMA': 'CODIGO_PROGRAMA TEXT',
    'PROGRAMA': 'PROGRAMA TEXT',
    'NIVEL_PROGRAMA': 'NIVEL_PROGRAMA TEXT',
    'FACULTAD': 'FACULTAD TEXT',
    'CARRERA': 'CARRERA TEXT',
    'PERIODO_PLAN': 'PERIODO_PLAN TEXT',
    'NIVEL': 'NIVEL INTEGER',
    'NRC': 'NRC TEXT',
    'NRC_PADRE': 'NRC_PADRE TEXT',
    'HORAS_TOTALES': 'HORAS_TOTALES INTEGER',
    'MATERIA': 'MATERIA TEXT',
    'CURSO': 'CURSO TEXT',
    'TITULO': 'TITULO TEXT',
    'SECCION': 'SECCION TEXT',
    'COD_DEPARTAMENTO': 'COD_DEPARTAMENTO TEXT',
    'DEPARTAMENTO': 'DEPARTAMENTO TEXT',
    'SEDE': 'SEDE TEXT',
    'ESTADO': 'ESTADO TEXT',
    'TIPO_HORARIO': 'TIPO_HORARIO TEXT',
    'JORNADA': 'JORNADA TEXT',
    'PARTE_PERIODO': 'PARTE_PERIODO TEXT',
    'HORAS_CREDITO': 'HORAS_CREDITO INTEGER',
    'HORAS_COBRO': 'HORAS_COBRO INTEGER',
    'LIGA': 'LIGA TEXT',
    'USUARIO': 'USUARIO TEXT',
    'FECHA_MODIFICACION': 'FECHA_MODIFICACION TEXT',
    'CONECTOR_LIGA': 'CONECTOR_LIGA TEXT',
    'CALIFICABLE': 'CALIFICABLE TEXT',
    'CUPO': 'CUPO INTEGER',
    'INSCRITOS': 'INSCRITOS INTEGER',
    'DISPONIBLES': 'DISPONIBLES INTEGER',
    'TIPO_REUNION': 'TIPO_REUNION TEXT',
    'FECHA_INCIO': 'FECHA_INCIO TEXT',
    'FECHA_FIN': 'FECHA_FIN TEXT',
    'LUNES': 'LUNES TEXT',
    'MARTES': 'MARTES TEXT',
    'MIERCOLES': 'MIERCOLES TEXT',
    'JUEVES': 'JUEVES TEXT',
    'VIERNES': 'VIERNES TEXT',
    'SABADO': 'SABADO TEXT',
    'DOMINGO': 'DOMINGO TEXT',
    'HORA_INCIO': 'HORA_INCIO TEXT',
    'HORA_FIN': 'HORA_FIN TEXT',
    'SESION': 'SESION TEXT',
    'COD_EDIFICIO': 'COD_EDIFICIO TEXT',
    'EDIFICIO': 'EDIFICIO TEXT',
    'COD_SALON': 'COD_SALON TEXT',
    'SALON': 'SALON TEXT',
    'CAPACIDAD_SALON': 'CAPACIDAD_SALON INTEGER',
    'TIPO_HORARIO_SESION': 'TIPO_HORARIO_SESION TEXT',
    'ID_DOCENTE': 'ID_DOCENTE TEXT',
    'DOCENTE': 'DOCENTE TEXT',
    'CARGA_TRABAJO': 'CARGA_TRABAJO INTEGER',
    'GRADO': 'GRADO TEXT',
    'AUTOSERVICIO': 'AUTOSERVICIO TEXT',
    'COMPR_HRS_DOCENTE': 'COMPR_HRS_DOCENTE TEXT',
    'ASESOR': 'ASESOR TEXT',
    'JERARQUIA': 'JERARQUIA TEXT',
    'TIPO_CONTRATO': 'TIPO_CONTRATO TEXT',
    'CARGO': 'CARGO TEXT',
    'SEDE_DOCENTE': 'SEDE_DOCENTE TEXT',
    'PORC_RESPONSABILIDAD': 'PORC_RESPONSABILIDAD INTEGER',
    'PRINCIPAL': 'PRINCIPAL TEXT',
    'SOBREPASO': 'SOBREPASO TEXT',
    'PORC_SESION': 'PORC_SESION INTEGER'
}

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_blocks(hora_inicio, hora_fin):
    if not hora_inicio or not hora_fin: return 0
    try:
        hi = int(str(hora_inicio).replace(':', ''))
        hf = int(str(hora_fin).replace(':', ''))
        
        # SCHEDULE_BLOCKS ranges in integer format
        ranges = [
            (800, 840), (841, 920), (930, 1010), (1011, 1050),
            (1100, 1140), (1141, 1220), (1230, 1310), (1311, 1350),
            (1400, 1440), (1441, 1520), (1530, 1610), (1611, 1650),
            (1700, 1740), (1741, 1820)
        ]
        
        blocks = 0
        for r_start, r_end in ranges:
            if hi <= r_start and hf >= r_end:
                blocks += 1
        return blocks
    except:
        return 0

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Create main table
    columns_sql = ", ".join(COLUMN_MAPPING.values())
    cursor.execute(f"CREATE TABLE IF NOT EXISTS planificacion (id INTEGER PRIMARY KEY AUTOINCREMENT, {columns_sql})")
    
    # Create toma_carga_manual table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS toma_carga_manual (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rut TEXT,
            nombre TEXT,
            asignatura TEXT,
            nrc TEXT,
            tipo TEXT,
            comentarios TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize DB on startup (especially for serverless environments)
init_db()

# Load Malla Curricular
MALLA_DATA = {}
try:
    malla_path = os.path.join(os.path.dirname(__file__), 'malla.csv')
    if os.path.exists(malla_path):
        with open(malla_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                MALLA_DATA[row['ID']] = {
                    'nombre': row['ASIGNATURA'],
                    'nivel': float(row['NIVEL']),
                    'requisitos': [r.strip() for r in row['REQUISITO'].split(',')] if row['REQUISITO'] else [],
                    'sct': int(row['SCT']) if row['SCT'] else 0
                }
except Exception as e:
    print(f"Error loading malla.csv: {e}")

def get_malla_id_by_name(asignatura_name):
    if not asignatura_name: return None
    parts = asignatura_name.split('-', 1)
    name = parts[1].strip().upper() if len(parts) > 1 else asignatura_name.strip().upper()
    
    name_norm = normalize_text(name)
    
    # Exact match first
    for id, data in MALLA_DATA.items():
        if normalize_text(data['nombre']) == name_norm:
            return id
            
    # Fallback to substring
    for id, data in MALLA_DATA.items():
        data_norm = normalize_text(data['nombre'])
        if name_norm in data_norm or data_norm in name_norm:
            return id
            
    return None

import re

def parse_malla_api(json_data):
    data = json_data.get('data', [])
    historial = {}
    
    for row in data:
        for k, v in row.items():
            if k.startswith('nivel') and v:
                aprobado = '#AP#' in v
                parts = v.split('-', 1)
                if len(parts) == 2:
                    name = parts[1].split('#')[0].strip()
                    # Remove the period suffix if present (e.g., " 202620")
                    name = re.sub(r'\s+\d{6}$', '', name).strip()
                    id_malla = get_malla_id_by_name(name)
                    if id_malla:
                        historial[id_malla] = {'aprobado': aprobado}
    
    return historial

def clean_value(val, col_type):
    if not val:
        return None
    val = val.strip()
    if val.endswith('.0'):
        val = val[:-2]
    if 'INTEGER' in col_type:
        try:
            return int(val)
        except ValueError:
            return 0
    return val

def import_csv_to_db(file_path):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Drop and recreate the table to clean old data
    cursor.execute("DROP TABLE IF EXISTS planificacion")
    columns_sql = ", ".join(COLUMN_MAPPING.values())
    cursor.execute(f"CREATE TABLE planificacion (id INTEGER PRIMARY KEY AUTOINCREMENT, {columns_sql})")
    
    with open(file_path, mode='r', encoding='utf-8-sig', errors='replace') as f:
        reader = csv.DictReader(f)
        
        # Prepare insert statement
        db_cols = []
        for csv_col in reader.fieldnames:
            safe_col = csv_col.replace(' ', '_').upper()
            if safe_col in COLUMN_MAPPING:
                db_cols.append(safe_col)
                
        placeholders = ", ".join(["?"] * len(db_cols))
        query = f"INSERT INTO planificacion ({', '.join(db_cols)}) VALUES ({placeholders})"
        
        count = 0
        for row in reader:
            values = []
            for csv_col in reader.fieldnames:
                safe_col = csv_col.replace(' ', '_').upper()
                if safe_col in COLUMN_MAPPING:
                    raw_val = row[csv_col]
                    col_type = COLUMN_MAPPING[safe_col]
                    values.append(clean_value(raw_val, col_type))
            
            cursor.execute(query, values)
            count += 1
            
    conn.commit()
    conn.close()
    return count

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No se encontró archivo en la solicitud'}), 400
    
    files = request.files.getlist('file')
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'message': 'Nombre de archivo vacío'}), 400
        
    try:
        import pandas as pd
        dfs = []
        
        for file in files:
            if not file.filename.endswith('.csv'):
                return jsonify({'success': False, 'message': 'Todos los archivos deben ser de formato CSV'}), 400
            
            try:
                df = pd.read_csv(file, sep=None, engine='python', encoding='utf-8')
            except UnicodeDecodeError:
                file.seek(0)
                df = pd.read_csv(file, sep=None, engine='python', encoding='latin1')
            except Exception:
                file.seek(0)
                df = pd.read_csv(file, sep=None, engine='python', encoding='cp1252')
                
            dfs.append(df)
            
        if not dfs:
            return jsonify({'success': False, 'message': 'No se pudo procesar ningún archivo'}), 400
            
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Save temp file
        temp_path = os.path.join(tempfile.gettempdir(), 'temp_upload.csv')
        combined_df.to_csv(temp_path, index=False, encoding='utf-8')
        
        # Import to SQLite
        rows_inserted = import_csv_to_db(temp_path)
        
        # Remove temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return jsonify({
            'success': True,
            'message': f'Planificación cargada con éxito. Se procesaron {rows_inserted} registros.',
            'rows_inserted': rows_inserted
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al procesar el archivo: {str(e)}'}), 500

@app.route('/api/summary', methods=['GET'])
def get_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if table has data
        cursor.execute("SELECT COUNT(*) FROM planificacion")
        total_rows = cursor.fetchone()[0]
        
        if total_rows == 0:
            return jsonify({'success': True, 'empty': True})
            
        # Total unique subjects (by NRC) - parent TEO NRCs only
        cursor.execute("SELECT COUNT(DISTINCT NRC) FROM planificacion WHERE TIPO_HORARIO = 'TEO' AND (NRC_PADRE IS NULL OR TRIM(NRC_PADRE) = '')")
        total_nrcs = cursor.fetchone()[0]
        
        # Total unique Docentes
        cursor.execute("SELECT COUNT(DISTINCT DOCENTE) FROM planificacion WHERE DOCENTE IS NOT NULL AND DOCENTE != ''")
        total_docentes = cursor.fetchone()[0]
        
        # Total unique Rooms
        cursor.execute("SELECT COUNT(DISTINCT COD_SALON) FROM planificacion WHERE COD_SALON IS NOT NULL AND COD_SALON != ''")
        total_salas = cursor.fetchone()[0]
        
        # Total unique Levels
        cursor.execute("SELECT COUNT(DISTINCT NIVEL) FROM planificacion WHERE NIVEL IS NOT NULL")
        total_niveles = cursor.fetchone()[0]
        
        # Total cupos, inscritos, disponibles (using distinct NRCs to avoid double counting)
        cursor.execute("""
            SELECT SUM(CUPO), SUM(INSCRITOS), SUM(DISPONIBLES) 
            FROM (
                SELECT NRC, CUPO, INSCRITOS, DISPONIBLES 
                FROM planificacion 
                GROUP BY NRC
            )
        """)
        sum_row = cursor.fetchone()
        total_cupos = sum_row[0] or 0
        total_inscritos = sum_row[1] or 0
        total_disponibles = sum_row[2] or 0
        
        # Total academic hours (sum of weekly blocks for distinct NRCs) - excluding APM
        cursor.execute("""
            SELECT SUM(weekly_blocks) FROM (
                SELECT NRC,
                       (SUM(CASE WHEN LUNES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN MARTES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN MIERCOLES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN JUEVES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN VIERNES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN SABADO='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN DOMINGO='Y' THEN 1 ELSE 0 END)) as weekly_blocks
                FROM planificacion 
                WHERE TIPO_HORARIO != 'APM' AND HORA_INCIO IS NOT NULL AND HORA_INCIO != ''
                GROUP BY NRC
            )
        """)
        total_horas = cursor.fetchone()[0] or 0
        
        # Hours breakdown by type (parent NRCs only, excluding APM, using weekly blocks)
        cursor.execute("""
            SELECT TIPO_HORARIO, SUM(weekly_blocks) as horas
            FROM (
                SELECT NRC, TIPO_HORARIO,
                       (SUM(CASE WHEN LUNES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN MARTES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN MIERCOLES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN JUEVES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN VIERNES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN SABADO='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN DOMINGO='Y' THEN 1 ELSE 0 END)) as weekly_blocks
                FROM planificacion
                WHERE TIPO_HORARIO != 'APM' AND HORA_INCIO IS NOT NULL AND HORA_INCIO != ''
                GROUP BY NRC, TIPO_HORARIO
            )
            GROUP BY TIPO_HORARIO
            ORDER BY TIPO_HORARIO
        """)
        horas_por_tipo = {row['TIPO_HORARIO']: (row['horas'] or 0) for row in cursor.fetchall()}
        
        # NRC padre count by type (parent NRCs only = those with no NRC_PADRE, excluding APM)
        cursor.execute("""
            SELECT TIPO_HORARIO, COUNT(DISTINCT NRC) as n
            FROM planificacion
            WHERE (NRC_PADRE IS NULL OR TRIM(NRC_PADRE) = '')
              AND TIPO_HORARIO != 'APM'
            GROUP BY TIPO_HORARIO
            ORDER BY TIPO_HORARIO
        """)
        nrcs_padre_por_tipo = {row['TIPO_HORARIO']: row['n'] for row in cursor.fetchall()}
        
        # Components breakdown (by distinct NRCs) - keep for reference
        cursor.execute("""
            SELECT TIPO_HORARIO, COUNT(DISTINCT NRC) as count 
            FROM planificacion 
            GROUP BY TIPO_HORARIO
        """)
        components = {row['TIPO_HORARIO']: row['count'] for row in cursor.fetchall()}
        
        # Occupancy by building (distinct room-time sessions)
        cursor.execute("""
            SELECT EDIFICIO, COUNT(*) as sessions 
            FROM planificacion 
            WHERE EDIFICIO IS NOT NULL AND EDIFICIO != '' AND COD_SALON IS NOT NULL AND COD_SALON != ''
            GROUP BY EDIFICIO
        """)
        edificios = {row['EDIFICIO']: row['sessions'] for row in cursor.fetchall()}
        
        # Contracts distribution (unique teachers)
        cursor.execute("""
            SELECT TIPO_CONTRATO, COUNT(DISTINCT DOCENTE) as count
            FROM planificacion
            WHERE DOCENTE IS NOT NULL AND DOCENTE != '' AND TIPO_CONTRATO IS NOT NULL AND TIPO_CONTRATO != ''
            GROUP BY TIPO_CONTRATO
        """)
        contratos = {row['TIPO_CONTRATO']: row['count'] for row in cursor.fetchall()}
        
        # Jerarquias distribution (unique teachers)
        cursor.execute("""
            SELECT JERARQUIA, COUNT(DISTINCT DOCENTE) as count
            FROM planificacion
            WHERE DOCENTE IS NOT NULL AND DOCENTE != '' AND JERARQUIA IS NOT NULL AND JERARQUIA != ''
            GROUP BY JERARQUIA
        """)
        jerarquias = {row['JERARQUIA']: row['count'] for row in cursor.fetchall()}
        
        # Grados (titles) distribution (unique teachers)
        cursor.execute("""
            SELECT 
                CASE
                    WHEN GRADO IS NULL OR TRIM(GRADO) = '' THEN 'Sin grado informado'
                    ELSE GRADO
                END as grado_label,
                COUNT(DISTINCT DOCENTE) as count
            FROM planificacion
            WHERE DOCENTE IS NOT NULL AND DOCENTE != ''
            GROUP BY grado_label
        """)
        grados = {row['grado_label']: row['count'] for row in cursor.fetchall()}
        
        return jsonify({
            'success': True,
            'empty': False,
            'metrics': {
                'total_nrcs': total_nrcs,
                'total_docentes': total_docentes,
                'total_salas': total_salas,
                'total_niveles': total_niveles,
                'total_cupos': total_cupos,
                'total_inscritos': total_inscritos,
                'total_disponibles': total_disponibles,
                'total_horas': total_horas
            },
            'horas_por_tipo': horas_por_tipo,
            'nrcs_padre_por_tipo': nrcs_padre_por_tipo,
            'components': components,
            'edificios': edificios,
            'contratos': contratos,
            'jerarquias': jerarquias,
            'grados': grados
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/filters', methods=['GET'])
def get_filters():
    carrera = request.args.get('carrera')
    jornada = request.args.get('jornada')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if table has data
        cursor.execute("SELECT COUNT(*) FROM planificacion")
        if cursor.fetchone()[0] == 0:
            return jsonify({'success': True, 'empty': True})
            
        cursor.execute("SELECT DISTINCT CARRERA FROM planificacion WHERE CARRERA IS NOT NULL ORDER BY CARRERA")
        carreras = [r['CARRERA'] for r in cursor.fetchall()]
        
        # Helper for conditions
        base_cond = []
        base_params = []
        if carrera:
            base_cond.append("CARRERA = ?")
            base_params.append(carrera)
        if jornada:
            base_cond.append("JORNADA = ?")
            base_params.append(jornada)
            
        where_clause = ""
        if base_cond:
            where_clause = "AND " + " AND ".join(base_cond)
            
        cursor.execute(f"SELECT DISTINCT NIVEL FROM planificacion WHERE NIVEL IS NOT NULL {where_clause} ORDER BY NIVEL", base_params)
        niveles = [r['NIVEL'] for r in cursor.fetchall()]
        
        # Fetch the maximum number of primary sections any course has in each Nivel
        cursor.execute(f"""
            SELECT NIVEL, MAX(num_sections) as max_secciones
            FROM (
                SELECT NIVEL, MATERIA, CURSO, CARRERA, COUNT(DISTINCT NRC) as num_sections
                FROM planificacion
                WHERE NIVEL IS NOT NULL AND (NRC_PADRE IS NULL OR NRC_PADRE = '') {where_clause}
                GROUP BY NIVEL, MATERIA, CURSO, CARRERA
            )
            GROUP BY NIVEL
        """, base_params)
        niveles_secciones = []
        for r in cursor.fetchall():
            nivel = r['NIVEL']
            max_sec = r['max_secciones']
            if max_sec:
                for i in range(1, max_sec + 1):
                    niveles_secciones.append({'nivel': nivel, 'seccion': str(i)})
        
        cursor.execute(f"SELECT DISTINCT DOCENTE FROM planificacion WHERE DOCENTE IS NOT NULL AND DOCENTE != '' {where_clause} ORDER BY DOCENTE", base_params)
        docentes = [r['DOCENTE'] for r in cursor.fetchall()]
        
        cursor.execute(f"SELECT DISTINCT COD_SALON, SALON FROM planificacion WHERE COD_SALON IS NOT NULL AND COD_SALON != '' {where_clause} ORDER BY COD_SALON", base_params)
        salas = [{'cod': r['COD_SALON'], 'name': f"{r['COD_SALON']} - {r['SALON']}"} for r in cursor.fetchall()]
        
        cursor.execute(f"SELECT DISTINCT EDIFICIO FROM planificacion WHERE EDIFICIO IS NOT NULL AND EDIFICIO != '' {where_clause} ORDER BY EDIFICIO", base_params)
        edificios = [r['EDIFICIO'] for r in cursor.fetchall()]
        
        cursor.execute(f"SELECT DISTINCT CODIGO_PROGRAMA FROM planificacion WHERE CODIGO_PROGRAMA IS NOT NULL {where_clause} ORDER BY CODIGO_PROGRAMA", base_params)
        programas = [r['CODIGO_PROGRAMA'] for r in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT JORNADA FROM planificacion WHERE JORNADA IS NOT NULL ORDER BY JORNADA")
        jornadas = [r['JORNADA'] for r in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'empty': False,
            'carreras': carreras,
            'niveles': niveles,
            'niveles_secciones': niveles_secciones,
            'docentes': docentes,
            'salas': salas,
            'edificios': edificios,
            'programas': programas,
            'jornadas': jornadas
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/asignaturas', methods=['GET'])
def get_asignaturas():
    carrera = request.args.get('carrera')
    nivel = request.args.get('nivel')
    jornada = request.args.get('jornada')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if table has data
        cursor.execute("SELECT COUNT(*) FROM planificacion")
        if cursor.fetchone()[0] == 0:
            return jsonify({'success': True, 'empty': True})
            
        # Build query for all unique sections (NRCs) with calculated weekly blocks as HORAS_TOTALES
        query = """
            SELECT NRC, NRC_PADRE, MATERIA, CURSO, TITULO, SECCION, 
                   LUNES, MARTES, MIERCOLES, JUEVES, VIERNES, SABADO, DOMINGO,
                   HORA_INCIO, HORA_FIN,
                   TIPO_HORARIO, CUPO, INSCRITOS, DISPONIBLES, DOCENTE, NIVEL, CARRERA, JORNADA
            FROM planificacion
        """
        # Apply filters if present
        conditions = []
        params = []
        if carrera:
            conditions.append("CARRERA = ?")
            params.append(carrera)
        if nivel:
            conditions.append("NIVEL = ?")
            params.append(nivel)
        if jornada:
            conditions.append("JORNADA = ?")
            params.append(jornada)
            
        if conditions:
            query += f" WHERE {' AND '.join(conditions)}"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        nrc_dict = {}
        for r in rows:
            nrc = r['NRC']
            if nrc not in nrc_dict:
                nrc_dict[nrc] = {
                    'NRC': nrc,
                    'NRC_PADRE': r['NRC_PADRE'],
                    'MATERIA': r['MATERIA'],
                    'CURSO': r['CURSO'],
                    'TITULO': r['TITULO'],
                    'SECCION': r['SECCION'],
                    'TIPO_HORARIO': r['TIPO_HORARIO'],
                    'CUPO': r['CUPO'],
                    'INSCRITOS': r['INSCRITOS'],
                    'DISPONIBLES': r['DISPONIBLES'],
                    'DOCENTE': r['DOCENTE'],
                    'NIVEL': r['NIVEL'],
                    'CARRERA': r['CARRERA'],
                    'JORNADA': r['JORNADA'],
                    'HORAS_TOTALES': 0
                }
            
            days = 0
            for day in ['LUNES', 'MARTES', 'MIERCOLES', 'JUEVES', 'VIERNES', 'SABADO', 'DOMINGO']:
                if r[day] == 'Y':
                    days += 1
            blocks = calculate_blocks(r['HORA_INCIO'], r['HORA_FIN'])
            nrc_dict[nrc]['HORAS_TOTALES'] += (days * blocks)

        subjects = list(nrc_dict.values())
        
        # Build tree structure
        parents = []
        children_by_parent = {}
        for r in subjects:
            parent_nrc = r['NRC_PADRE']
            # If the course specifies a parent, and that parent actually exists in our data
            if parent_nrc:
                if parent_nrc not in children_by_parent:
                    children_by_parent[parent_nrc] = []
                children_by_parent[parent_nrc].append(r)
            else:
                # If there's no parent, or the parent is not in our dataset, treat it as a parent node
                parents.append(r)
                
        # Attach children to parents
        result = []
        for p in parents:
            p_nrc = p['NRC']
            p_copy = dict(p)
            p_copy['componentes_hijo'] = children_by_parent.get(p_nrc, [])
            result.append(p_copy)
            
        # Sort by Level, then Subject Code (Materia + Curso) and Section
        def safe_int(val):
            try:
                return int(val)
            except:
                return 9999
                
        result.sort(key=lambda x: (safe_int(x.get('NIVEL')), x.get('MATERIA') or '', x.get('CURSO') or '', x.get('SECCION') or ''))
        
        return jsonify({
            'success': True,
            'empty': False,
            'asignaturas': result
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/docentes', methods=['GET'])
def get_docentes():
    carrera = request.args.get('carrera')
    jornada = request.args.get('jornada')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if table has data
        cursor.execute("SELECT COUNT(*) FROM planificacion")
        if cursor.fetchone()[0] == 0:
            return jsonify({'success': True, 'empty': True})
            
        base_cond = ["DOCENTE IS NOT NULL", "DOCENTE != ''"]
        base_params = []
        if carrera:
            base_cond.append("CARRERA = ?")
            base_params.append(carrera)
        if jornada:
            base_cond.append("JORNADA = ?")
            base_params.append(jornada)
            
        where_clause = " AND ".join(base_cond)

        cursor.execute(f"""
            SELECT DOCENTE, ID_DOCENTE, GRADO, TIPO_CONTRATO, JERARQUIA, CARGO, SEDE_DOCENTE
            FROM planificacion
            WHERE {where_clause}
            GROUP BY DOCENTE
            ORDER BY DOCENTE
        """, base_params)
        teachers = [dict(r) for r in cursor.fetchall()]
        
        # For each teacher, find unique subjects they teach and sum HORAS_TOTALES
        for t in teachers:
            docente_name = t['DOCENTE']
            
            sub_cond = ["DOCENTE = ?"]
            sub_params = [docente_name]
            if carrera:
                sub_cond.append("CARRERA = ?")
                sub_params.append(carrera)
            if jornada:
                sub_cond.append("JORNADA = ?")
                sub_params.append(jornada)
            sub_where = " AND ".join(sub_cond)

            cursor.execute(f"""
                SELECT NRC, NRC_PADRE, TITULO, MATERIA, CURSO, SECCION, TIPO_HORARIO,
                       LUNES, MARTES, MIERCOLES, JUEVES, VIERNES, SABADO, DOMINGO,
                       HORA_INCIO, HORA_FIN
                FROM planificacion
                WHERE {sub_where}
            """, sub_params)
            rows = cursor.fetchall()
            
            # Group by NRC in python to calculate total hours correctly
            nrc_dict = {}
            for r in rows:
                nrc = r['NRC']
                if nrc not in nrc_dict:
                    nrc_dict[nrc] = {
                        'NRC': nrc,
                        'NRC_PADRE': r['NRC_PADRE'],
                        'TITULO': r['TITULO'],
                        'MATERIA': r['MATERIA'],
                        'CURSO': r['CURSO'],
                        'SECCION': r['SECCION'],
                        'TIPO_HORARIO': r['TIPO_HORARIO'],
                        'HORAS_TOTALES': 0
                    }
                
                # Count days this specific row is active
                days = 0
                for day in ['LUNES', 'MARTES', 'MIERCOLES', 'JUEVES', 'VIERNES', 'SABADO', 'DOMINGO']:
                    if r[day] == 'Y':
                        days += 1
                
                # Calculate blocks per day
                blocks_per_day = calculate_blocks(r['HORA_INCIO'], r['HORA_FIN'])
                nrc_dict[nrc]['HORAS_TOTALES'] += (days * blocks_per_day)
                
            subjects = list(nrc_dict.values())
            
            t['asignaturas'] = subjects
            t['total_horas'] = sum(s['HORAS_TOTALES'] for s in subjects if s['TIPO_HORARIO'] != 'APM')
            
            # Count unique TEO parent NRCs
            teo_parents = [s for s in subjects if s['TIPO_HORARIO'] == 'TEO' and (s['NRC_PADRE'] is None or s['NRC_PADRE'].strip() == '')]
            if len(teo_parents) > 0:
                t['n_asignaturas'] = len(teo_parents)
            else:
                # Fallback to unique non-APM NRCs if they only teach AYU/LAB/TER
                non_apm_subjects = [s for s in subjects if s['TIPO_HORARIO'] != 'APM']
                t['n_asignaturas'] = len(non_apm_subjects)
            
        return jsonify({
            'success': True,
            'empty': False,
            'docentes': teachers
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/salas', methods=['GET'])
def get_salas():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if table has data
        cursor.execute("SELECT COUNT(*) FROM planificacion")
        if cursor.fetchone()[0] == 0:
            return jsonify({'success': True, 'empty': True})
            
        carrera = request.args.get('carrera')
        jornada = request.args.get('jornada')
        
        # Build conditions for rooms
        room_cond = ["COD_SALON IS NOT NULL", "COD_SALON != ''"]
        room_params = []
        if carrera:
            room_cond.append("CARRERA = ?")
            room_params.append(carrera)
        if jornada:
            room_cond.append("JORNADA = ?")
            room_params.append(jornada)
            
        where_clause = " AND ".join(room_cond)
        
        # Get list of unique classrooms and their properties based on filtered sections
        cursor.execute(f"""
            SELECT COD_SALON, SALON, CAPACIDAD_SALON, EDIFICIO, COD_EDIFICIO
            FROM planificacion
            WHERE {where_clause}
            GROUP BY COD_SALON
            ORDER BY EDIFICIO, COD_SALON
        """, room_params)
        rooms = [dict(r) for r in cursor.fetchall()]
        
        # Calculate occupancy count (number of sessions) for each room
        for r in rooms:
            # Calculate occupancy count (number of sessions) for each room based on filters
            occ_cond = ["COD_SALON = ?", "HORA_INCIO IS NOT NULL", "HORA_INCIO != ''", "(LUNES='Y' OR MARTES='Y' OR MIERCOLES='Y' OR JUEVES='Y' OR VIERNES='Y' OR SABADO='Y' OR DOMINGO='Y')"]
            occ_params = [r['COD_SALON']]
            if carrera:
                occ_cond.append("CARRERA = ?")
                occ_params.append(carrera)
            if jornada:
                occ_cond.append("JORNADA = ?")
                occ_params.append(jornada)
                
            occ_where = " AND ".join(occ_cond)
            
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM planificacion 
                WHERE {occ_where}
            """, occ_params)
            r['ocupacion_sesiones'] = cursor.fetchone()[0]
            
        return jsonify({
            'success': True,
            'empty': False,
            'salas': rooms
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    docente = request.args.get('docente')
    nivel = request.args.get('nivel')
    seccion = request.args.get('seccion')
    sala = request.args.get('sala')
    carrera = request.args.get('carrera')
    jornada = request.args.get('jornada')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if table has data
        cursor.execute("SELECT COUNT(*) FROM planificacion")
        if cursor.fetchone()[0] == 0:
            return jsonify({'success': True, 'empty': True})
            
        def fetch_schedule_rows(docente_val, nivel_val, seccion_val, sala_val, carrera_val, jornada_val):
            query = """
                SELECT NRC, NRC_PADRE, TITULO, MATERIA, CURSO, SECCION, TIPO_HORARIO, DOCENTE, 
                       COD_SALON, SALON, EDIFICIO, NIVEL, CARRERA, JORNADA,
                       LUNES, MARTES, MIERCOLES, JUEVES, VIERNES, SABADO, DOMINGO,
                       HORA_INCIO, HORA_FIN
                FROM planificacion
                WHERE HORA_INCIO IS NOT NULL AND HORA_INCIO != ''
                      AND (LUNES='Y' OR MARTES='Y' OR MIERCOLES='Y' OR JUEVES='Y' OR VIERNES='Y' OR SABADO='Y' OR DOMINGO='Y')
            """
            conditions = []
            params = []
            
            if docente_val:
                conditions.append("DOCENTE = ?")
                params.append(docente_val)
            if nivel_val:
                conditions.append("NIVEL = ?")
                params.append(int(nivel_val))
            if seccion_val:
                try:
                    sec_idx = int(seccion_val) - 1
                    parent_query = """
                        SELECT DISTINCT NRC, MATERIA, CURSO, SECCION
                        FROM planificacion 
                        WHERE (NIVEL = ? OR ? IS NULL) AND (NRC_PADRE IS NULL OR NRC_PADRE = '')
                    """
                    parent_params = [int(nivel_val) if nivel_val else None, nivel_val]
                    
                    if carrera_val:
                        parent_query += " AND CARRERA = ?"
                        parent_params.append(carrera_val)
                    
                    parent_query += " ORDER BY MATERIA, CURSO, SECCION"
                    cursor.execute(parent_query, parent_params)
                    
                    from collections import defaultdict
                    subject_nrcs = defaultdict(list)
                    for r in cursor.fetchall():
                        subj_key = f"{r['MATERIA']}_{r['CURSO']}"
                        subject_nrcs[subj_key].append(r['NRC'])
                    
                    parent_nrcs = []
                    for subj, nrc_list in subject_nrcs.items():
                        if sec_idx < len(nrc_list):
                            parent_nrcs.append(nrc_list[sec_idx])
                    
                    if parent_nrcs:
                        placeholders = ','.join(['?'] * len(parent_nrcs))
                        conditions.append(f"(NRC IN ({placeholders}) OR NRC_PADRE IN ({placeholders}))")
                        params.extend(parent_nrcs)
                        params.extend(parent_nrcs)
                    else:
                        conditions.append("1 = 0")
                except ValueError:
                    conditions.append("SECCION = ?")
                    params.append(seccion_val)
            if sala_val:
                conditions.append("COD_SALON = ?")
                params.append(sala_val)
            if carrera_val:
                conditions.append("CARRERA = ?")
                params.append(carrera_val)
            if jornada_val:
                conditions.append("JORNADA = ?")
                params.append(jornada_val)
                
            if conditions:
                query += " AND " + " AND ".join(conditions)
                
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

        # Primary rows
        rows = fetch_schedule_rows(docente, nivel, seccion, sala, carrera, jornada)
        for r in rows:
            r['is_overlay'] = False
            
        # Overlay rows
        overlay_carrera = request.args.get('overlay_carrera')
        overlay_nivel = request.args.get('overlay_nivel')
        if overlay_carrera and overlay_nivel:
            overlay_seccion = request.args.get('overlay_seccion')
            overlay_exclude_str = request.args.get('overlay_exclude')
            
            overlay_rows = fetch_schedule_rows(docente, overlay_nivel, overlay_seccion, sala, overlay_carrera, jornada)
            
            overlay_exclude_list = []
            if overlay_exclude_str:
                overlay_exclude_list = [t.strip() for t in overlay_exclude_str.split('|') if t.strip()]
                
            filtered_overlay_rows = []
            for r in overlay_rows:
                if r['TITULO'] not in overlay_exclude_list:
                    r['is_overlay'] = True
                    filtered_overlay_rows.append(r)
            
            overlay_rows = filtered_overlay_rows
            
            # Combine without duplicates (same NRC and same time blocks)
            # A combination of NRC + LUNES + HORA_INCIO is usually unique for a block
            seen = set()
            for r in rows:
                key = (r['NRC'], r['LUNES'], r['MARTES'], r['MIERCOLES'], r['JUEVES'], r['VIERNES'], r['SABADO'], r['HORA_INCIO'])
                seen.add(key)
                
            for r in overlay_rows:
                key = (r['NRC'], r['LUNES'], r['MARTES'], r['MIERCOLES'], r['JUEVES'], r['VIERNES'], r['SABADO'], r['HORA_INCIO'])
                if key not in seen:
                    rows.append(r)
                    seen.add(key)
        
        # Identify subgroups within families (e.g. multiple LABs for the same parent)
        from collections import defaultdict
        family_groups = defaultdict(lambda: defaultdict(set))
        for r in rows:
            fam_id = r['NRC_PADRE'] if r['NRC_PADRE'] else r['NRC']
            tipo = r['TIPO_HORARIO']
            family_groups[fam_id][tipo].add((r['NRC'], r['SECCION']))
            
        nrc_to_subgrupo = {}
        for fam_id, tipos in family_groups.items():
            for tipo, nrc_sec_set in tipos.items():
                if len(nrc_sec_set) > 1:
                    # Sort by SECCION string to assign deterministic index
                    sorted_list = sorted(list(nrc_sec_set), key=lambda x: x[1] if x[1] else "")
                    for idx, (nrc, _) in enumerate(sorted_list):
                        nrc_to_subgrupo[nrc] = idx + 1

        # Format times for easier client usage (e.g. HH:MM)
        formatted_rows = []
        for r in rows:
            start_str = r['HORA_INCIO'].zfill(4)
            end_str = r['HORA_FIN'].zfill(4)
            
            # Format as HH:MM
            start_formatted = f"{start_str[:2]}:{start_str[2:]}"
            end_formatted = f"{end_str[:2]}:{end_str[2:]}"
            
            r['hora_inicio_fmt'] = start_formatted
            r['hora_fin_fmt'] = end_formatted
            
            r['subgrupo'] = nrc_to_subgrupo.get(r['NRC'], None)
            
            formatted_rows.append(r)
            
        return jsonify({
            'success': True,
            'empty': False,
            'schedule': formatted_rows
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/send_email', methods=['POST'])
def send_email():
    try:
        email_to = request.form.get('email')
        docente = request.form.get('docente', 'Docente')
        pdf_file = request.files.get('pdf')
        
        if not email_to or not pdf_file:
            return jsonify({'success': False, 'message': 'Faltan datos (correo o archivo)'}), 400
            
        # Get SMTP config from env vars
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_user = os.environ.get('SMTP_USER')
        smtp_pass = os.environ.get('SMTP_PASS')
        
        if not smtp_user or not smtp_pass:
            # Fake success for testing if env vars are not set
            print(f"[MOCK EMAIL] Enviar a {email_to} - SMTP no configurado.")
            return jsonify({'success': True, 'message': 'Simulado (Sin credenciales SMTP)'})
            
        # Build message
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = email_to
        msg['Subject'] = f"Horario Académico - {docente}"
        
        body = f"Estimado/a {docente},\n\nAdjunto encontrará su horario académico semanal.\n\nSaludos cordiales,\nSistema de Planificación."
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach PDF
        part = MIMEApplication(pdf_file.read(), Name=f"Horario_{docente.replace(' ', '_')}.pdf")
        part['Content-Disposition'] = f'attachment; filename="Horario_{docente.replace(" ", "_")}.pdf"'
        msg.attach(part)
        
        # Send
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        
        return jsonify({'success': True, 'message': 'Enviado correctamente'})
    except Exception as e:
        print(f"Error sending email: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

PROGRAMAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'programas')
DOCUMENTOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'documentos')

import unicodedata
def normalize_text(text):
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.lower().replace('\ufffd', '').strip()

@app.route('/api/programas', methods=['GET'])
def get_programas():
    if not os.path.exists(PROGRAMAS_DIR):
        return jsonify([])
    
    programas = []
    for root, dirs, files in os.walk(PROGRAMAS_DIR):
        for file in files:
            if file.lower().endswith('.pdf'):
                # Try to extract subject name: usually "CODE Subject Name.pdf"
                # Strip extension
                name_no_ext = file[:-4]
                # Try to find the first space
                parts = name_no_ext.split(' ', 1)
                if len(parts) == 2:
                    clean_name = normalize_text(parts[1])
                else:
                    clean_name = normalize_text(name_no_ext)
                
                # Get Nivel from folder name if possible
                folder_name = os.path.basename(root)
                
                # Keep absolute path safe for download
                rel_path = os.path.relpath(os.path.join(root, file), PROGRAMAS_DIR)
                
                programas.append({
                    'filename': file,
                    'path': rel_path,
                    'clean_name': clean_name,
                    'folder': folder_name
                })
    
    return jsonify(programas)

@app.route('/api/documentos', methods=['GET'])
def get_documentos():
    if not os.path.exists(DOCUMENTOS_DIR):
        return jsonify([])
    
    documentos = []
    for root, dirs, files in os.walk(DOCUMENTOS_DIR):
        for file in files:
            if file.lower().endswith(('.pdf', '.docx', '.doc')):
                rel_path = os.path.relpath(os.path.join(root, file), DOCUMENTOS_DIR)
                
                documentos.append({
                    'filename': file,
                    'path': rel_path
                })
    
    return jsonify(documentos)

@app.route('/api/programas/download', methods=['GET'])
def download_programa():
    rel_path = request.args.get('path')
    if not rel_path:
        return "Path is required", 400
    
    # Secure the path
    safe_path = os.path.normpath(os.path.join(PROGRAMAS_DIR, rel_path))
    if not safe_path.startswith(PROGRAMAS_DIR):
        return "Invalid path", 403
        
    if not os.path.exists(safe_path):
        return "File not found", 404
        
    dir_name = os.path.dirname(safe_path)
    file_name = os.path.basename(safe_path)
    
    return send_from_directory(dir_name, file_name, as_attachment=True)

# ==========================================
# TOMA DE CARGA (MANUAL REGISTRATION)
# ==========================================
ALUMNOS_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'alumnos', 'Matricula_Total_202620.csv')
_alumnos_cache = None

def get_alumnos_data():
    global _alumnos_cache
    if not _alumnos_cache:
        _alumnos_cache = []
        if os.path.exists(ALUMNOS_CSV_PATH):
            import pandas as pd
            try:
                df = pd.read_csv(ALUMNOS_CSV_PATH, sep=None, engine='python', encoding='utf-8-sig', encoding_errors='replace')
            except Exception:
                df = pd.read_csv(ALUMNOS_CSV_PATH, sep=None, engine='python', encoding='latin1', encoding_errors='replace')
            
            # Fill NaN values with empty string before converting to dict records
            df = df.fillna('')
            _alumnos_cache = df.to_dict('records')
    return _alumnos_cache

@app.route('/api/alumnos/search', methods=['GET'])
def search_alumnos():
    rut_query = request.args.get('rut', '').strip().lower()
    if not rut_query:
        return jsonify([])
    
    alumnos = get_alumnos_data()
    results = []
    # ID_BANNER is the rut
    for a in alumnos:
        if rut_query in str(a.get('ID_BANNER', '')).lower():
            results.append({
                'rut': a.get('ID_BANNER', ''),
                'nombre': f"{a.get('NOMBRES', '')} {a.get('APELLIDOS', '')}".strip()
            })
            if len(results) >= 20: # Limit results
                break
    return jsonify(results)

def get_nrc_info(cursor, nrcs):
    if not nrcs: return []
    placeholders = ','.join(['?']*len(nrcs))
    cursor.execute(f"""
        SELECT NRC, TITULO, LUNES, MARTES, MIERCOLES, JUEVES, VIERNES, SABADO, DOMINGO, HORA_INCIO, HORA_FIN
        FROM planificacion
        WHERE NRC IN ({placeholders})
    """, nrcs)
    
    results_dict = {}
    for row in cursor.fetchall():
        nrc = row['NRC']
        id_malla = get_malla_id_by_name(row['TITULO'])
        malla_info = MALLA_DATA.get(id_malla) if id_malla else None
        
        hi = int(str(row['HORA_INCIO']).replace(':', '')) if row['HORA_INCIO'] else 0
        hf = int(str(row['HORA_FIN']).replace(':', '')) if row['HORA_FIN'] else 0
        
        days = [('LUNES', row['LUNES']), ('MARTES', row['MARTES']), ('MIERCOLES', row['MIERCOLES']), 
                ('JUEVES', row['JUEVES']), ('VIERNES', row['VIERNES']), ('SABADO', row['SABADO']), ('DOMINGO', row['DOMINGO'])]
                
        schedule_entries = []
        for day_name, val in days:
            if val == 'Y':
                schedule_entries.append({'day': day_name, 'start': hi, 'end': hf, 'titulo': row['TITULO']})
                
        if nrc not in results_dict:
            results_dict[nrc] = {
                'nrc': nrc,
                'titulo': row['TITULO'],
                'id_malla': id_malla,
                'sct': malla_info['sct'] if malla_info else 0,
                'nivel': malla_info['nivel'] if malla_info else 99,
                'requisitos': malla_info['requisitos'] if malla_info else [],
                'schedule': []
            }
        
        results_dict[nrc]['schedule'].extend(schedule_entries)
        
    return list(results_dict.values())

def check_schedule_conflict(sched1, sched2):
    for s1 in sched1:
        for s2 in sched2:
            if s1['day'] == s2['day']:
                # overlap if max(start1, start2) < min(end1, end2)
                if max(s1['start'], s2['start']) < min(s1['end'], s2['end']):
                    return True
    return False

@app.route('/api/toma_carga/validar', methods=['POST'])
def validar_toma_carga():
    data = request.json
    rut = data.get('rut')
    nrcs_to_add = data.get('nrcs', [])
    token = data.get('smp_token')
    
    if not rut or not nrcs_to_add or not token:
        return jsonify({'success': False, 'message': 'Faltan datos obligatorios (RUT, NRCs o Token).'}), 400
        
    # Clean token if user pasted 'Bearer ...' or a full cURL
    token_clean = token.strip()
    if token_clean.startswith('Bearer '):
        token_clean = token_clean[7:].strip()
    # If they pasted the whole curl command, try to extract the bearer token
    if 'Bearer ' in token_clean:
        token_clean = token_clean.split('Bearer ')[1].split("'")[0].split('"')[0].strip()
        
    # Remove DV if present
    rut_clean = rut.split('-')[0].replace('.', '')
    
    # 1. Fetch from SMP (malla)
    url = f"https://apismp.uautonoma.cl/estudiantes/malla?pagina=0&registros=1000000&id={rut_clean}&programa=ICIND_111"
    headers = {
        'Accept': '*/*',
        'Authorization': f'Bearer {token_clean}',
        'Origin': 'https://smp.uautonoma.cl',
        'Referer': 'https://smp.uautonoma.cl/',
        'api': 'GESTIÓN ACADÉMICA',
        'aplicativo': 'ESTUDIANTE',
        'codInstitucion': 'UAC',
        'endpoint': url,
        'pidmUsuario': '178360',
        'tipoPeticion': 'GET'
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 401:
            return jsonify({'success': False, 'message': 'Token de SMP inválido o expirado. Por favor, actualiza tu Token.'}), 401
        r.raise_for_status()
        smp_data = r.json()
        
        # 2. Fetch from SMP (horario)
        url_horario = f"https://apismp.uautonoma.cl/estudiantes/horario?pagina=0&registros=1000000&id={rut_clean}&periodo=202620"
        headers['endpoint'] = url_horario
        r_horario = requests.get(url_horario, headers=headers, timeout=10)
        r_horario.raise_for_status()
        smp_horario = r_horario.json()
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error conectando a SMP: {str(e)}'}), 500
        
    historial = parse_malla_api(smp_data)
    
    enrolled_nrcs = list(set([row.get('nrc') for row in smp_horario.get('data', []) if row.get('nrc')]))

    
    # Calculate Nivel Base
    niveles_completos = []
    # Group subjects by level
    niveles = {}
    for mid, info in MALLA_DATA.items():
        if info['nivel'] not in niveles:
            niveles[info['nivel']] = []
        niveles[info['nivel']].append(mid)
        
    nivel_base = 0
    for lvl in sorted(niveles.keys()):
        all_passed = all(historial.get(mid, {}).get('aprobado', False) for mid in niveles[lvl])
        if all_passed:
            nivel_base = lvl
        else:
            break
            
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get info for all enrolled and new NRCs
    enrolled_info = get_nrc_info(cursor, enrolled_nrcs)
    new_info = get_nrc_info(cursor, nrcs_to_add)
    
    conn.close()
    
    errors = []
    
    # Rule 1: Max 32 SCT
    total_sct = sum(x['sct'] for x in enrolled_info) + sum(x['sct'] for x in new_info)
    if total_sct > 32:
        errors.append(f"Regla 1 Falló: Excede límite de 32 créditos SCT (Total proyectado: {total_sct}).")
        
    # Check each new NRC
    all_schedules = [x['schedule'] for x in enrolled_info]
    
    for ni in new_info:
        # Rule 5: Already Approved
        if ni['id_malla'] and historial.get(ni['id_malla'], {}).get('aprobado', False):
            errors.append(f"Regla 5 Falló: {ni['titulo']} ya se encuentra aprobada en el historial del estudiante.")
            
        # Rule 6: Already Enrolled
        if ni['id_malla'] and any((x['id_malla'] == ni['id_malla']) for x in enrolled_info):
            errors.append(f"Regla 6 Falló: {ni['titulo']} ya está inscrita en el periodo actual.")
            
        # Rule 3: Max Levels (+3 from nivel_base)
        if ni['nivel'] > nivel_base + 3:
            errors.append(f"Regla 3 Falló: {ni['titulo']} (Nivel {ni['nivel']}) excede los 3 niveles permitidos (Nivel base actual: {nivel_base}).")
            
        # Rule 4: Prerequisites
        for req_id in ni['requisitos']:
            if not historial.get(req_id, {}).get('aprobado', False):
                req_name = MALLA_DATA.get(req_id, {}).get('nombre', req_id)
                errors.append(f"Regla 4 Falló: {ni['titulo']} requiere aprobar {req_name}.")
                
        # Rule 2: Schedule Conflict
        conflict = False
        for sched in all_schedules:
            if check_schedule_conflict(ni['schedule'], sched):
                conflict = True
                break
        
        if conflict:
            errors.append(f"Regla 2 Falló: {ni['titulo']} presenta tope de horario con otra asignatura inscrita o propuesta.")
        else:
            all_schedules.append(ni['schedule']) # Add to schedule array to check cross-conflicts among new subjects
            
    if errors:
        return jsonify({'success': False, 'errors': errors})
        
    return jsonify({'success': True, 'message': 'Validación exitosa.'})

@app.route('/api/toma_carga/posibles', methods=['POST'])
def posibles_toma_carga():
    data = request.json
    rut = data.get('rut')
    token = data.get('smp_token')
    
    if not rut or not token:
        return jsonify({'success': False, 'message': 'Faltan datos obligatorios (RUT o Token).'}), 400
        
    token_clean = token.strip()
    if token_clean.startswith('Bearer '):
        token_clean = token_clean[7:].strip()
    if 'Bearer ' in token_clean:
        token_clean = token_clean.split('Bearer ')[1].split("'")[0].split('"')[0].strip()
        
    rut_clean = rut.split('-')[0].replace('.', '')
    
    url = f"https://apismp.uautonoma.cl/estudiantes/malla?pagina=0&registros=1000000&id={rut_clean}&programa=ICIND_111"
    headers = {
        'Accept': '*/*',
        'Authorization': f'Bearer {token_clean}',
        'Origin': 'https://smp.uautonoma.cl',
        'Referer': 'https://smp.uautonoma.cl/',
        'api': 'GESTIÓN ACADÉMICA',
        'aplicativo': 'ESTUDIANTE',
        'codInstitucion': 'UAC',
        'endpoint': url,
        'pidmUsuario': '178360',
        'tipoPeticion': 'GET'
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 401:
            return jsonify({'success': False, 'message': 'Token de SMP inválido o expirado. Por favor, actualiza tu Token.'}), 401
        r.raise_for_status()
        smp_data = r.json()
        
        url_horario = f"https://apismp.uautonoma.cl/estudiantes/horario?pagina=0&registros=1000000&id={rut_clean}&periodo=202620"
        headers['endpoint'] = url_horario
        r_horario = requests.get(url_horario, headers=headers, timeout=10)
        r_horario.raise_for_status()
        smp_horario = r_horario.json()
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error conectando a SMP: {str(e)}'}), 500
        
    historial = parse_malla_api(smp_data)
    enrolled_nrcs = list(set([row.get('nrc') for row in smp_horario.get('data', []) if row.get('nrc')]))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    enrolled_info = get_nrc_info(cursor, enrolled_nrcs)
    
    # Calculate Nivel Base
    niveles_aprobados = {}
    for id_malla, data in MALLA_DATA.items():
        nivel = data['nivel']
        if historial.get(id_malla, {}).get('aprobado', False):
            if nivel not in niveles_aprobados:
                niveles_aprobados[nivel] = {'total': 0, 'aprobadas': 0}
            niveles_aprobados[nivel]['aprobadas'] += 1
            
        if nivel not in niveles_aprobados:
            niveles_aprobados[nivel] = {'total': 0, 'aprobadas': 0}
        niveles_aprobados[nivel]['total'] += 1
        
    nivel_base = 0
    for nivel in sorted(niveles_aprobados.keys()):
        if niveles_aprobados[nivel]['aprobadas'] == niveles_aprobados[nivel]['total'] and niveles_aprobados[nivel]['total'] > 0:
            nivel_base = nivel
        else:
            break
            
    sct_actual = sum(x['sct'] for x in enrolled_info)
    all_schedules = [x['schedule'] for x in enrolled_info]
    
    # Get all distinct NRCs from database
    carrera = data.get('carrera')
    if carrera:
        cursor.execute("SELECT DISTINCT NRC FROM planificacion WHERE CARRERA = ?", (carrera,))
    else:
        cursor.execute("SELECT DISTINCT NRC FROM planificacion")
        
    all_nrcs_in_db = [row['NRC'] for row in cursor.fetchall()]
    all_nrcs_info = get_nrc_info(cursor, all_nrcs_in_db)
    
    conn.close()
    
    posibles = []
    topes_horario = {}
    
    for ni in all_nrcs_info:
        # Rule 5: Already Approved
        if ni['id_malla'] and historial.get(ni['id_malla'], {}).get('aprobado', False):
            continue
            
        # Rule 6: Already Enrolled
        if ni['id_malla'] and any((x['id_malla'] == ni['id_malla']) for x in enrolled_info):
            continue
            
        # Rule 3: Max Levels (+3 from nivel_base)
        if ni['nivel'] > (nivel_base + 3):
            continue
            
        # Rule 4: Prerequisites
        missing_prereqs = False
        if ni['requisitos']:
            for req_id in ni['requisitos']:
                if not historial.get(req_id, {}).get('aprobado', False):
                    missing_prereqs = True
                    break
        if missing_prereqs:
            continue
            
        # Rule 1: Max 32 SCT
        if (sct_actual + ni['sct']) > 32:
            continue
            
        # Rule 2: Schedule Conflict
        conflict = False
        conflict_with = None
        for sched in all_schedules:
            if check_schedule_conflict(ni['schedule'], sched):
                conflict = True
                # Get the title of the conflicting subject from the first overlapping entry
                for s1 in ni['schedule']:
                    for s2 in sched:
                        if s1['day'] == s2['day'] and max(s1['start'], s2['start']) < min(s1['end'], s2['end']):
                            conflict_with = s2.get('titulo', 'Desconocido')
                            break
                    if conflict_with:
                        break
                break
                
        if conflict:
            if ni['id_malla']:
                topes_horario[ni['id_malla']] = conflict_with
            continue
            
        # Passed all checks!
        posibles.append({
            'titulo': ni['titulo'],
            'nrc': ni['nrc'],
            'sct': ni['sct'],
            'nivel': ni['nivel'],
            'id_malla': ni['id_malla']
        })
        
    # Group by titulo
    agrupados = {}
    for p in posibles:
        if p['titulo'] not in agrupados:
            agrupados[p['titulo']] = {'titulo': p['titulo'], 'nivel': p['nivel'], 'sct': p['sct'], 'nrcs': []}
        agrupados[p['titulo']]['nrcs'].append(p['nrc'])
        
    resultados_finales = sorted(list(agrupados.values()), key=lambda x: x['nivel'])
    
    # --- Generate Malla Visual Data ---
    malla_visual = {}
    enrolled_malla_ids = set([x['id_malla'] for x in enrolled_info if x['id_malla']])
    sugeridos_malla_ids = set([p['id_malla'] for p in posibles if p['id_malla']])
    
    for id_malla, data in MALLA_DATA.items():
        nivel = data['nivel']
        if nivel not in malla_visual:
            malla_visual[nivel] = []
            
        estado = 'pendiente'
        motivo_bloqueo = None
        
        if historial.get(id_malla, {}).get('aprobado', False):
            estado = 'aprobado'
        elif id_malla in enrolled_malla_ids:
            estado = 'tomado'
        elif id_malla in sugeridos_malla_ids:
            estado = 'sugerido'
        elif id_malla in topes_horario:
            estado = 'tope'
            motivo_bloqueo = f"Tope con {topes_horario[id_malla]}"
            
        malla_visual[nivel].append({
            'id_malla': id_malla,
            'nombre': data['nombre'],
            'sct': data['sct'],
            'estado': estado,
            'motivo_bloqueo': motivo_bloqueo
        })
        
    return jsonify({
        'success': True, 
        'posibles': resultados_finales, 
        'nivel_base': nivel_base, 
        'sct_actual': sct_actual,
        'malla_visual': dict(sorted(malla_visual.items()))
    })
@app.route('/api/toma_carga/asignaturas', methods=['GET'])
def get_toma_carga_asignaturas():
    carrera = request.args.get('carrera', '')
    jornada = request.args.get('jornada', '')
    try:
        conn = get_db_connection()
        query = '''
            SELECT MATERIA, CURSO, TITULO, NRC, NRC_PADRE, TIPO_HORARIO, SECCION
            FROM planificacion
            WHERE 1=1
        '''
        params = []
        if carrera:
            query += ' AND CARRERA = ?'
            params.append(carrera)
        if jornada:
            query += ' AND JORNADA = ?'
            params.append(jornada)
            
        cursor_nrcs = conn.execute(query, params)
        nrcs = [dict(row) for row in cursor_nrcs.fetchall()]
        conn.close()
        
        asignaturas_dict = {}
        for n in nrcs:
            key = f"{n['MATERIA']} {n['CURSO']} - {n['TITULO']}"
            if key not in asignaturas_dict:
                asignaturas_dict[key] = {
                    'materia': n['MATERIA'],
                    'curso': n['CURSO'],
                    'titulo': n['TITULO'],
                    'label': key
                }
        
        asignaturas = list(asignaturas_dict.values())
        asignaturas.sort(key=lambda x: x['label'])
            
        return jsonify({
            'asignaturas': asignaturas,
            'nrcs': nrcs
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/toma_carga', methods=['GET', 'POST'])
def handle_toma_carga():
    if request.method == 'GET':
        try:
            conn = get_db_connection()
            cursor = conn.execute('SELECT * FROM toma_carga_manual ORDER BY id DESC')
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return jsonify(rows)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        data = request.json
        if not data or not data.get('rut'):
            return jsonify({'success': False, 'message': 'RUT requerido'}), 400
            
        try:
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO toma_carga_manual (rut, nombre, asignatura, nrc, tipo, comentarios)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data.get('rut', ''),
                data.get('nombre', ''),
                data.get('asignatura', ''),
                data.get('nrc', ''),
                data.get('tipo', ''),
                data.get('comentarios', '')
            ))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
            
@app.route('/api/toma_carga/<int:record_id>', methods=['DELETE'])
def delete_toma_carga(record_id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM toma_carga_manual WHERE id = ?', (record_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    # Ensure database is initialized
    init_db()
    
    # Check if base file is already in workspace, if so, pre-populate.
    base_csv = "Planificación General 202520 06-07-2026.csv"
    if os.path.exists(base_csv):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM planificacion")
            count = cursor.fetchone()[0]
            if count == 0:
                print(f"Pre-populando base de datos con archivo local: {base_csv}")
                import_csv_to_db(base_csv)
        except Exception as e:
            print(f"Error al precargar base de datos: {e}")
        finally:
            conn.close()
            
    print("Iniciando servidor local en http://0.0.0.0:5000/")
    app.run(debug=True, host='0.0.0.0', port=5000)
