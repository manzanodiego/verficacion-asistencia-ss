from flask import Flask, request, render_template, jsonify, url_for, redirect, flash, Response, session
import pandas as pd
from db import get_db
import qrcode
import io
import base64
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)


app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}
app.secret_key = 'tu_clave_secreta_aqui'

#Creamos carpeta de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Inicializar tabla de usuarios
def init_users_table():
    """Crea la tabla de usuarios si no existe y añade el usuario administrador por defecto"""
    db = get_db()
    cursor = db.cursor()
    
    # Crear tabla de usuarios si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            contraseña TEXT NOT NULL
        )
    ''')
    
    # Verificar si el usuario administrador ya existe
    cursor.execute('SELECT usuario FROM usuarios WHERE usuario = ?', ('admi-asistencia25',))
    if not cursor.fetchone():
        # Crear hash de la contraseña
        password_hash = generate_password_hash('servicio25')
        # Insertar usuario administrador
        cursor.execute(
            'INSERT INTO usuarios (usuario, contraseña) VALUES (?, ?)',
            ('admi-asistencia25', password_hash)
        )
    
    db.commit()

# Decorador para verificar si el usuario está logueado
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Inicializar la tabla de usuarios al iniciar la aplicación
with app.app_context():
    init_users_table()

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        contraseña = request.form.get('contraseña')
        
        if not usuario or not contraseña:
            flash('Por favor, completa todos los campos', 'error')
            return render_template('login.html')
        
        db = get_db()
        cursor = db.cursor()
        
        # Buscar usuario en la base de datos
        cursor.execute('SELECT * FROM usuarios WHERE usuario = ?', (usuario,))
        user = cursor.fetchone()
        db.close()
        
        if user and check_password_hash(user['contraseña'], contraseña):
            # Iniciar sesión
            session['user_id'] = user['id']
            session['usuario'] = user['usuario']
            flash('Sesión iniciada correctamente', 'success')
            return redirect(url_for('home'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route("/logout")
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('login'))


@app.route("/")
@login_required
def home():
    db = get_db()
    alumnos = db.execute('SELECT * FROM ALUMNOS').fetchall()
    return render_template('index.html', alumnos=alumnos)


@app.route("/generar_qr", methods=['GET', 'POST'])
def generar_qr():
    qr_code =None
    if request.method == "POST":
        numero_control = request.form["numero_control"]
        qr_img = qrcode.make(numero_control.strip())
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)

        qr_code = base64.b64encode(buffer.getvalue()).decode()

    return render_template('generar_qr.html', qr_code=qr_code)

@app.route("/asistencia_qr")
@login_required
def asistencia_qr():
    return render_template('leer_asistencia_qr.html')


@app.route("/leer_qr", methods=['POST'])
@login_required
def leer_qr():
    try:
        # Obtener datos del JSON
        data = request.get_json()
        
        if not data:
            return jsonify({
                "status": "error", 
                "message": "No se recibieron datos"
            }), 400
        
        numero_control = data.get('qr_data')
        
        if not numero_control:
            return jsonify({
                "status": "error", 
                "message": "Número de control no proporcionado"
            }), 400
        
        print(f'Código QR recibido: {numero_control}')
        
        db = get_db()
        cursor = db.cursor()
        
        # Primero verificar si el alumno existe
        cursor.execute(
            'SELECT * FROM ALUMNOS WHERE NUMERO_CONTROL = ?', 
            (numero_control,)
        )
        alumno = cursor.fetchone()
        
        if not alumno:
            db.close()
            return jsonify({
                "status": "error",
                "message": f"Alumno con número de control {numero_control} no encontrado"
            }), 404
        
        # Actualizar asistencia (sintaxis SQL corregida)
        cursor.execute(
            'UPDATE ALUMNOS SET ASISTENCIA = 1 WHERE NUMERO_CONTROL = ?', 
            (numero_control,)
        )
        db.commit()
        
        # Obtener información actualizada del alumno
        cursor.execute(
            'SELECT * FROM ALUMNOS WHERE NUMERO_CONTROL = ?',
            (numero_control,)
        )
        alumno_actualizado = cursor.fetchone()
        
        db.close()
        
        # Convertir row a diccionario
        alumno_dict = dict(alumno_actualizado)
        
        return jsonify({
            "status": "success",
            "message": "Asistencia registrada correctamente",
            "alumno": alumno_dict
        }), 200
    
    except Exception as e:
        print(f"Error en leer_qr: {e}")
        return jsonify({
            "status": "error",
            "message": "Error interno del servidor"
        }), 500


@app.route("/añadir_alumno",methods=['POST', 'GET'])
@login_required
def añadir_alumno():
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            nombre = request.form.get('nombre')
            #semestre = request.form.get('semestre')
            carrera = request.form.get('carrera')
            numero_control = request.form.get('numero_control')
            #reticula = request.form.get('reticula')
            
            # Validar que todos los campos estén presentes
            if not all([nombre, carrera, numero_control]):
                #flash('Todos los campos son obligatorios', 'error')
                return redirect(url_for('home'))
            
            db = get_db()
            cursor = db.cursor()
            
            # Verificar si el número de control ya existe
            cursor.execute(
                'SELECT NUMERO_CONTROL FROM ALUMNOS WHERE NUMERO_CONTROL = ?',
                (numero_control,)
            )
            if cursor.fetchone():
                #flash(f'El número de control {numero_control} ya existe', 'error')
                db.close()
                return redirect(url_for('home'))
            
            # Insertar nuevo alumno (con coma después del VALUES)
            cursor.execute(
                '''INSERT INTO ALUMNOS(NUMERO_CONTROL, NOMBRE, CARRERA) 
                   VALUES(?, ?, ?)''',
                (numero_control, nombre, carrera)
            )
            db.commit()
            db.close()
            
            return redirect(url_for('home'))

        except sqlite3.Error as e:
            db.close()
            return redirect(url_for('home'))
        except Exception as e:
            if 'db' in locals():
                db.close()
            return redirect(url_for('home'))   
    
    # Si es GET, mostrar el template
    return render_template('index.html')

# Función para verificar extensión de archivo
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

#Insertar datos a la base de datos
def insertar_csv_db(csv_path):
    try:
        df = pd.read_csv(csv_path)

        # Mapear columnas del CSV a columnas de la base de datos
        # Las columnas esperadas en la BD son: NUMERO_CONTROL, NOMBRE, CARRERA, SEMESTRE, AVANCE_RETICULAR
        columnas_bd = ['NUMERO_CONTROL', 'NOMBRE', 'CARRERA']
        
        # Normalizar nombres de columnas del CSV (convertir a mayúsculas y sin espacios)
        df.columns = df.columns.str.strip().str.upper()
        
        # Verificar que existan las columnas necesarias
        columnas_faltantes = [col for col in columnas_bd if col not in df.columns]
        if columnas_faltantes:
            return False, f"Faltan las siguientes columnas en el CSV: {', '.join(columnas_faltantes)}"
        
        db = get_db()
        cursor = db.cursor()
        
        registros_insertados = 0
        registros_duplicados = 0
        errores = []

        for _, row in df.iterrows():
            try:
                numero_control = str(row['NUMERO_CONTROL']).strip()
                nombre = str(row['NOMBRE']).strip()
                carrera = str(row['CARRERA']).strip()
                #semestre = str(row['SEMESTRE']).strip()
                #reticula = str(row['AVANCE_RETICULAR']).strip()
                
                # Verificar si el número de control ya existe
                cursor.execute(
                    'SELECT NUMERO_CONTROL FROM ALUMNOS WHERE NUMERO_CONTROL = ?',
                    (numero_control,)
                )
                if cursor.fetchone():
                    registros_duplicados += 1
                    continue
                
                # Insertar nuevo alumno
                cursor.execute(
                    '''INSERT INTO ALUMNOS(NUMERO_CONTROL, NOMBRE, CARRERA) 
                       VALUES(?, ?, ?)''',
                    (numero_control, nombre, carrera)
                )
                registros_insertados += 1
                
            except Exception as e:
                errores.append(f"Error en fila {_ + 2}: {str(e)}")
                continue
        
        db.commit()
        db.close()
        
        mensaje = f"Se insertaron {registros_insertados} registros correctamente"
        if registros_duplicados > 0:
            mensaje += f". {registros_duplicados} registros duplicados fueron omitidos"
        if errores:
            mensaje += f". {len(errores)} errores encontrados"
        
        return True, mensaje

    except Exception as e:
        return False, f"Error al insertar datos: {str(e)}"


@app.route('/exportar_csv', methods=['GET'])
@login_required
def exportar_csv():
    try:
        db = get_db()
        alumnos = db.execute('SELECT * FROM ALUMNOS').fetchall()
        db.close()
        
        # Convertir a DataFrame
        df = pd.DataFrame([dict(row) for row in alumnos])
        
        # Crear respuesta CSV
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        
        # Crear respuesta con headers apropiados
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=alumnos_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
    except Exception as e:
        flash(f'Error al exportar CSV: {str(e)}', 'error')
        return redirect(url_for('home'))



#Subir csv
@app.route('/upload_csv', methods=['GET', 'POST'])
@login_required
def upload_csv():
    if request.method == 'POST':
        # Verificar que se haya subido un archivo
        if 'archivo-csv' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(url_for('home'))
        
        file_csv = request.files['archivo-csv']
        
        # Verificar que el archivo tenga un nombre
        if file_csv.filename == '':
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(url_for('home'))
        
        # Verificar extensión del archivo
        if not allowed_file(file_csv.filename):
            flash('El archivo debe ser un CSV (.csv)', 'error')
            return redirect(url_for('home'))
        
        try:
            filename = secure_filename(file_csv.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Guardar el archivo
            file_csv.save(filepath)
            
            # Insertar datos en la base de datos
            exito, mensaje = insertar_csv_db(filepath)
            
            if exito:
                flash(mensaje, 'success')
            else:
                flash(mensaje, 'error')
            
            #eliminar el archivo después de procesarlo
            os.remove(filepath)
            
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'error')
        
        return redirect(url_for('home'))
    
    return render_template("index.html")

@app.route('/filtro_asistencia', methods=['GET'])
@login_required
def filtro_asistencia():
    db = get_db()
    alumnos = db.execute('SELECT * FROM ALUMNOS WHERE ASISTENCIA = 1').fetchall()
    return render_template('index.html', alumnos=alumnos)


@app.route('/filtro_carrera/<string:carrera>/', methods=['GET'])
@login_required
def filtro_carrera(carrera):
    db = get_db()
    carrera = carrera.upper()
    alumnos = db.execute('SELECT * FROM ALUMNOS WHERE CARRERA = ?', (carrera, )).fetchall()
    return render_template('index.html', alumnos=alumnos)


@app.route('/eliminar_todos_alumnos', methods=['POST'])
@login_required
def eliminar_todos_alumnos():
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Contar cuántos alumnos se van a eliminar
        cursor.execute('SELECT COUNT(*) as total FROM ALUMNOS')
        total = cursor.fetchone()['total']
        
        # Eliminar todos los alumnos
        cursor.execute('DELETE FROM ALUMNOS')
        db.commit()
        db.close()
        
        flash(f'Se eliminaron {total} alumnos correctamente', 'success')
    except Exception as e:
        flash(f'Error al eliminar alumnos: {str(e)}', 'error')
    
    return redirect(url_for('home'))


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug_mode)