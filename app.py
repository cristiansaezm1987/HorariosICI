import os
import csv
import sqlite3
import re
import tempfile
import shutil
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
import smtplib
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
ALUMNOS_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'alumnos', 'Matrícula Total 202620.csv')
_alumnos_cache = None

def get_alumnos_data():
    global _alumnos_cache
    if _alumnos_cache is None:
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
