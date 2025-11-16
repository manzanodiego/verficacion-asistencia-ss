from flask import Flask, request, render_template, jsonify, url_for, redirect, flash
import pandas as pd
from db import get_db
import qrcode
import io
import base64
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)


app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}
app.secret_key = 'tu_clave_secreta_aqui'

#Creamos carpeta de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route("/")
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
def asistencia_qr():
    return render_template('leer_asistencia_qr.html')


@app.route("/leer_qr", methods=['POST'])
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
            'SELECT NUMERO_CONTROL, NOMBRE, ASISTENCIA FROM ALUMNOS WHERE NUMERO_CONTROL = ?',
            (numero_control,)
        )
        alumno_actualizado = cursor.fetchone()
        
        db.close()
        
        return jsonify({
            "status": "success",
            "message": "Asistencia registrada correctamente",
            "alumno": {
                "numero_control": alumno_actualizado[0],
                "nombre": alumno_actualizado[1] if len(alumno_actualizado) > 1 else "N/A",
                "asistencia": alumno_actualizado[2] if len(alumno_actualizado) > 2 else 1
            }
        }), 200
    
    except Exception as e:
        print(f"Error en leer_qr: {e}")
        return jsonify({
            "status": "error",
            "message": "Error interno del servidor"
        }), 500


@app.route("/añadir_alumno",methods=['POST', 'GET'])
def añadir_alumno():
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            nombre = request.form.get('nombre')
            semestre = request.form.get('semestre')
            carrera = request.form.get('carrera')
            numero_control = request.form.get('numero_control')
            reticula = request.form.get('reticula')
            
            # Validar que todos los campos estén presentes
            if not all([nombre, semestre, carrera, numero_control, reticula]):
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
                '''INSERT INTO ALUMNOS(NUMERO_CONTROL, NOMBRE, CARRERA, SEMESTRE, AVANCE_RETICULAR) 
                   VALUES(?, ?, ?, ?, ?)''',
                (numero_control, nombre, carrera, semestre, reticula)
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
        columnas_bd = ['NUMERO_CONTROL', 'NOMBRE', 'CARRERA', 'SEMESTRE', 'AVANCE_RETICULAR']
        
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
                semestre = str(row['SEMESTRE']).strip()
                reticula = str(row['AVANCE_RETICULAR']).strip()
                
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
                    '''INSERT INTO ALUMNOS(NUMERO_CONTROL, NOMBRE, CARRERA, SEMESTRE, AVANCE_RETICULAR) 
                       VALUES(?, ?, ?, ?, ?)''',
                    (numero_control, nombre, carrera, semestre, reticula)
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


#Subir csv
@app.route('/upload_csv', methods=['GET', 'POST'])
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
            
            # Opcional: eliminar el archivo después de procesarlo
            # os.remove(filepath)
            
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'error')
        
        return redirect(url_for('home'))
    
    return render_template("index.html")

@app.route('/filtro_asistencia', methods=['GET'])
def filtro_asistencia():
    db = get_db()
    alumnos = db.execute('SELECT * FROM ALUMNOS WHERE ASISTENCIA = 1').fetchall()
    return render_template('index.html', alumnos=alumnos)


if __name__ == '__main__':
    app.run(debug=True, port=5000)