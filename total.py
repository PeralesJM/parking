from flask import Flask, jsonify, request
from flask import render_template
import pymysql
import math
app = Flask(__name__)

# Conexión a la base de datos
def get_db_connection():
    try:
        conn = pymysql.connect(
            host="127.0.0.1",
            user="root",
            password="",
            database="hora_azul",
            port=3306,
            cursorclass=pymysql.cursors.DictCursor)
        return conn
    except Exception as e:
        print("Error al conectar a la base de datos:", e)
        return None

# Obtener datos desde la base de datos
def obtener_aparcamientos():
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE aparcamientos2 SET estado = 0 WHERE tiempo < NOW()")
            cursor.execute("SELECT * FROM aparcamientos2 WHERE estado = 0")
            rows = cursor.fetchall()
        conn.commit()
        conn.close()
        return rows
    except Exception as e:
        print("Error al consultar la base de datos:", e)
        return []

# Ruta de la API
"""@app.route("/datos", methods=["GET"])
def get_aparcamientos_api():
    datos = obtener_aparcamientos()
    return jsonify(datos)"""

# Función para calcular distancia entre dos coordenadas
def distancia_km(lat1, lon1, lat2, lon2):
    d_lat = lat2 - lat1
    d_lon = lon2 - lon1
    lat_media_rad = math.radians((lat1 + lat2) / 2)
    dy = d_lat * 111.32
    dx = d_lon * 111.32 * math.cos(lat_media_rad)
    return math.sqrt(dx ** 2 + dy ** 2)

# Ordenar por cercanía
def cercania(lat_ref, lon_ref, top=15):
    datos = obtener_aparcamientos()
    mas_cerca = []
    for user in datos:
        try:
            lat = float(user["latitud"])
            lon = float(user["longitud"])
            distancia = distancia_km(lat_ref, lon_ref, lat, lon)
            mas_cerca.append({
                "codigo": user.get("codigo", "???"),
                "latitud": lat,
                "longitud": lon,
                "calle": user.get("calle", "???"),
                "distancia": round(distancia * 1000)})
        except (KeyError, ValueError) as e:
            print(f"Error en registro: {e}")
    mas_cerca.sort(key=lambda u: u["distancia"])
    return mas_cerca[:top]

# Ruta HTTP para obtener aparcamientos cercanos
@app.route("/cercanos", methods=["GET"])
def obtener_cercanos():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
        top = int(request.args.get("top", 10))  
        resultado = cercania(lat, lon, top)
        return jsonify(resultado)
    except (TypeError, ValueError):
        return jsonify({"error": "Parámetros inválidos. Usa lat, lon y opcionalmente top."}), 400

# Ruta básica para testear conexión
@app.route("/")
def home():
    return "API de aparcamientos funcionando."

@app.route("/buscar")
def buscar_html():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(port=5050, debug=True)

   # Pedir coordenadas al usuario
"""try:
        mi_lat = float(input("Su latitud: "))
        mi_lon = float(input("Su longitud: "))
        print("\nAparcamientos más cercanos:")
        usuarios = cercania(mi_lat, mi_lon)
        for u in usuarios:
            print(f"{u['codigo']} en calle {u['calle']} a {u['distancia']*1000:.0f} metros")
    except ValueError:
        print("Coordenadas inválidas")"""