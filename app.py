import os
import csv
import sqlite3
import re
import tempfile
import shutil
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='static', static_url_path='')

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

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Create main table
    columns_sql = ", ".join(COLUMN_MAPPING.values())
    cursor.execute(f"CREATE TABLE IF NOT EXISTS planificacion (id INTEGER PRIMARY KEY AUTOINCREMENT, {columns_sql})")
    conn.commit()
    conn.close()

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
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if table has data
        cursor.execute("SELECT COUNT(*) FROM planificacion")
        if cursor.fetchone()[0] == 0:
            return jsonify({'success': True, 'empty': True})
            
        cursor.execute("SELECT DISTINCT CARRERA FROM planificacion WHERE CARRERA IS NOT NULL ORDER BY CARRERA")
        carreras = [r['CARRERA'] for r in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT NIVEL FROM planificacion WHERE NIVEL IS NOT NULL ORDER BY NIVEL")
        niveles = [r['NIVEL'] for r in cursor.fetchall()]
        
        # Fetch the maximum number of primary sections any course has in each Nivel
        cursor.execute("""
            SELECT NIVEL, MAX(num_sections) as max_secciones
            FROM (
                SELECT NIVEL, MATERIA, CURSO, CARRERA, COUNT(DISTINCT NRC) as num_sections
                FROM planificacion
                WHERE NIVEL IS NOT NULL AND (NRC_PADRE IS NULL OR NRC_PADRE = '')
                GROUP BY NIVEL, MATERIA, CURSO, CARRERA
            )
            GROUP BY NIVEL
        """)
        niveles_secciones = []
        for r in cursor.fetchall():
            nivel = r['NIVEL']
            max_sec = r['max_secciones']
            if max_sec:
                for i in range(1, max_sec + 1):
                    niveles_secciones.append({'nivel': nivel, 'seccion': str(i)})
        
        cursor.execute("SELECT DISTINCT DOCENTE FROM planificacion WHERE DOCENTE IS NOT NULL AND DOCENTE != '' ORDER BY DOCENTE")
        docentes = [r['DOCENTE'] for r in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT COD_SALON, SALON FROM planificacion WHERE COD_SALON IS NOT NULL AND COD_SALON != '' ORDER BY COD_SALON")
        salas = [{'cod': r['COD_SALON'], 'name': f"{r['COD_SALON']} - {r['SALON']}"} for r in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT EDIFICIO FROM planificacion WHERE EDIFICIO IS NOT NULL AND EDIFICIO != '' ORDER BY EDIFICIO")
        edificios = [r['EDIFICIO'] for r in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT CODIGO_PROGRAMA FROM planificacion WHERE CODIGO_PROGRAMA IS NOT NULL ORDER BY CODIGO_PROGRAMA")
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
                   (SUM(CASE WHEN LUNES='Y' THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN MARTES='Y' THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN MIERCOLES='Y' THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN JUEVES='Y' THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN VIERNES='Y' THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN SABADO='Y' THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN DOMINGO='Y' THEN 1 ELSE 0 END)) as HORAS_TOTALES,
                   TIPO_HORARIO, CUPO, INSCRITOS, DISPONIBLES, DOCENTE, NIVEL, CARRERA, JORNADA
            FROM planificacion
            GROUP BY NRC
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
            # We must apply filters in a subquery or filter unique NRCs carefully.
            # Let's filter the rows first, then group by NRC.
            query = f"""
                SELECT NRC, NRC_PADRE, MATERIA, CURSO, TITULO, SECCION, 
                       (SUM(CASE WHEN LUNES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN MARTES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN MIERCOLES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN JUEVES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN VIERNES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN SABADO='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN DOMINGO='Y' THEN 1 ELSE 0 END)) as HORAS_TOTALES,
                       TIPO_HORARIO, CUPO, INSCRITOS, DISPONIBLES, DOCENTE, NIVEL, CARRERA, JORNADA
                FROM planificacion
                WHERE {' AND '.join(conditions)}
                GROUP BY NRC
            """
            
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        
        # Build parent-child relationships
        nrc_map = {r['NRC']: r for r in rows}
        parents = []
        children_by_parent = {}
        
        for r in rows:
            parent_nrc = r['NRC_PADRE']
            # If the course specifies a parent, and that parent actually exists in our data
            if parent_nrc and parent_nrc in nrc_map:
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
            
        # Sort by subject code (Materia + Curso) and Section
        result.sort(key=lambda x: (x.get('MATERIA') or '', x.get('CURSO') or '', x.get('SECCION') or ''))
        
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
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if table has data
        cursor.execute("SELECT COUNT(*) FROM planificacion")
        if cursor.fetchone()[0] == 0:
            return jsonify({'success': True, 'empty': True})
            
        # Query distinct teachers and their profile fields (taking the most frequent or first one)
        # We also want to compute their total hours
        cursor.execute("""
            SELECT DOCENTE, ID_DOCENTE, GRADO, TIPO_CONTRATO, JERARQUIA, CARGO, SEDE_DOCENTE
            FROM planificacion
            WHERE DOCENTE IS NOT NULL AND DOCENTE != ''
            GROUP BY DOCENTE
            ORDER BY DOCENTE
        """)
        teachers = [dict(r) for r in cursor.fetchall()]
        
        # For each teacher, find unique subjects they teach and sum HORAS_TOTALES
        for t in teachers:
            docente_name = t['DOCENTE']
            
            # Subquery to get distinct NRCs for this teacher and their properties, calculating weekly blocks as HORAS_TOTALES
            cursor.execute("""
                SELECT NRC, NRC_PADRE, TITULO, MATERIA, CURSO, SECCION, 
                       (SUM(CASE WHEN LUNES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN MARTES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN MIERCOLES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN JUEVES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN VIERNES='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN SABADO='Y' THEN 1 ELSE 0 END) +
                        SUM(CASE WHEN DOMINGO='Y' THEN 1 ELSE 0 END)) as HORAS_TOTALES,
                       TIPO_HORARIO
                FROM planificacion
                WHERE DOCENTE = ?
                GROUP BY NRC
            """, (docente_name,))
            subjects = [dict(r) for r in cursor.fetchall()]
            
            t['asignaturas'] = subjects
            t['total_horas'] = sum(s['HORAS_TOTALES'] or 0 for s in subjects if s['TIPO_HORARIO'] != 'APM')
            
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
            
        # Get list of unique classrooms and their properties
        cursor.execute("""
            SELECT COD_SALON, SALON, CAPACIDAD_SALON, EDIFICIO, COD_EDIFICIO
            FROM planificacion
            WHERE COD_SALON IS NOT NULL AND COD_SALON != ''
            GROUP BY COD_SALON
            ORDER BY EDIFICIO, COD_SALON
        """)
        rooms = [dict(r) for r in cursor.fetchall()]
        
        # Calculate occupancy count (number of sessions) for each room
        for r in rooms:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM planificacion 
                WHERE COD_SALON = ? AND HORA_INCIO IS NOT NULL AND HORA_INCIO != ''
                      AND (LUNES='Y' OR MARTES='Y' OR MIERCOLES='Y' OR JUEVES='Y' OR VIERNES='Y' OR SABADO='Y' OR DOMINGO='Y')
            """, (r['COD_SALON'],))
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
            
        # We need rows with day and hour information
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
        
        if docente:
            conditions.append("DOCENTE = ?")
            params.append(docente)
        if nivel:
            conditions.append("NIVEL = ?")
            params.append(int(nivel))
        if seccion:
            try:
                sec_idx = int(seccion) - 1
                
                # We need to respect the carrera filter when determining the Nth section!
                parent_query = """
                    SELECT DISTINCT NRC, MATERIA, CURSO, SECCION
                    FROM planificacion 
                    WHERE (NIVEL = ? OR ? IS NULL) AND (NRC_PADRE IS NULL OR NRC_PADRE = '')
                """
                parent_params = [int(nivel) if nivel else None, nivel]
                
                if carrera:
                    parent_query += " AND CARRERA = ?"
                    parent_params.append(carrera)
                
                parent_query += " ORDER BY MATERIA, CURSO, SECCION"
                
                cursor.execute(parent_query, parent_params)
                
                # Group by subject and pick the Nth NRC
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
                    conditions.append("1 = 0") # Impossible condition since no parents match this group
            except ValueError:
                conditions.append("SECCION = ?")
                params.append(seccion)
        if sala:
            conditions.append("COD_SALON = ?")
            params.append(sala)
        if carrera:
            conditions.append("CARRERA = ?")
            params.append(carrera)
        if jornada:
            conditions.append("JORNADA = ?")
            params.append(jornada)
            
        if conditions:
            query += " AND " + " AND ".join(conditions)
            
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        
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
