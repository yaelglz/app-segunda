from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas

# Configuración inicial de Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'Cacahuete53'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///datos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo de base de datos


class Transaccion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(10))  # "ingreso" o "gasto"
    categoria = db.Column(db.String(50))  # Ejemplo: "mensual", "diario"
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.Date, default=datetime.today)

# Ruta principal


@app.route("/")
def index():
    transacciones = Transaccion.query.order_by(Transaccion.fecha.desc()).all()
    return render_template("index.html", transacciones=transacciones)


# Agregar transacciones


@app.route("/agregar", methods=["POST"])
def agregar():
    tipo = request.form.get("tipo")
    categoria = request.form.get("categoria")
    monto = float(request.form.get("monto"))
    fecha = datetime.strptime(request.form.get("fecha"), "%Y-%m-%d")
    nueva_transaccion = Transaccion(
        tipo=tipo, categoria=categoria, monto=monto, fecha=fecha)
    db.session.add(nueva_transaccion)
    db.session.commit()
    return redirect(url_for("index"))

# Eliminar transacciones


@app.route("/eliminar", methods=["POST"])
def eliminar():
    # Obtener el ID del registro desde el formulario
    transaccion_id = request.form.get("id")

    # Buscar la transacción por ID y eliminarla
    transaccion = Transaccion.query.get(transaccion_id)
    if transaccion:
        db.session.delete(transaccion)
        db.session.commit()
        flash("Registro eliminado con éxito.", "success")
    else:
        flash("Registro no encontrado.", "danger")

    # Redirigir de vuelta a la página principal
    return redirect("/")


# Generar reporte en PDF


@app.route("/reporte", methods=["GET"])
def reporte():
    # Obtener el año y mes de la solicitud
    anio = int(request.args.get("anio"))
    mes = int(request.args.get("mes"))

    # Crear un buffer para generar el PDF en memoria
    buffer = BytesIO()
    c = canvas.Canvas(buffer)

    # Consultar las transacciones del mes y año solicitados
    transacciones = db.session.query(Transaccion).filter(
        db.extract("year", Transaccion.fecha) == anio,
        db.extract("month", Transaccion.fecha) == mes
    ).all()

    # Agregar información al PDF
    c.drawString(100, 800, f"Reporte de Finanzas - {mes}/{anio}")
    y = 750
    total_ingresos = 0
    total_gastos = 0

    for transaccion in transacciones:
        c.drawString(100, y, f"{transaccion.tipo.title()}: {
                     transaccion.categoria} - ${transaccion.monto} (Fecha: {transaccion.fecha})")
        if transaccion.tipo == "ingreso":
            total_ingresos += transaccion.monto
        elif transaccion.tipo == "gasto":
            total_gastos += transaccion.monto
        y -= 20  # Espaciado entre líneas

    # Agregar totales al final del reporte
    y -= 40
    c.drawString(100, y, f"Total de Ingresos: ${total_ingresos}")
    y -= 20
    c.drawString(100, y, f"Total de Gastos: ${total_gastos}")
    y -= 20
    c.drawString(
        100, y, f"Diferencia (Ingresos - Gastos): ${total_ingresos - total_gastos}")

    # Finalizar y guardar el PDF
    c.save()
    buffer.seek(0)

    # Devolver el PDF como respuesta descargable
    return send_file(buffer, as_attachment=True, download_name=f"reporte_{mes}_{anio}.pdf", mimetype="application/pdf")


# Datos para la gráfica


@app.route("/datos_grafica")
def datos_grafica():
    mes_actual = datetime.today().month
    ingresos = sum([t.monto for t in db.session.query(Transaccion).filter_by(
        tipo="ingreso").filter(db.extract("month", Transaccion.fecha) == mes_actual).all()])
    gastos = sum([t.monto for t in db.session.query(Transaccion).filter_by(
        tipo="gasto").filter(db.extract("month", Transaccion.fecha) == mes_actual).all()])
    return jsonify({"ingresos": ingresos, "gastos": gastos})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Crear todas las tablas en la base de datos
    app.run(debug=True)
