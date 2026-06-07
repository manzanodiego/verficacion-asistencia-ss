# Sistema de Verificación de Asistencias

¡Bienvenido! Este proyecto es una aplicación web diseñada para automatizar y agilizar el registro y verificación de asistencias a las pláticas de servicio social mediante el uso de códigos QR.

---

## 🚀 Características Implementadas

* **Generación y Lectura de QR:**
    * **Generador:** Crea códigos QR únicos basados en el número de control de cada estudiante.
    * **Lector:** Escaneo rápido en tiempo real utilizando la cámara del dispositivo mediante la librería `Html5Qrcode`.
* **Carga Masiva de Alumnos (CSV):** * Permite importar archivos `.csv` con la información de los estudiantes proporcionada por los departamentos, optimizando el tiempo de captura de datos.
* **Exportación de Datos:**
    * Genera reportes de asistencia descargables en formato `.csv` para facilitar su manejo, filtrado y compartición con otras áreas.

---

## 🛠️ Tecnologías Utilizadas

* **Frontend:** HTML5, CSS3, JavaScript (ES6+)
* **Lectura de QR:** [Html5Qrcode](https://github.com/mebjas/html5-qrcode)
* **Backend:** Python con Flask
* **Base de Datos:** Sqlite

---

## 📋 Estructura del Archivo CSV (Importación)

Para que el sistema procese correctamente la lista de alumnos, el archivo `.csv` debe tener la siguiente estructura (separado por comas):

```csv
numero_control,nombre y apellido,carrera
12345678,Diego Manzano,ISC