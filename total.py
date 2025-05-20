from flask import Flask, jsonify, request, render_template
from supabase import create_client, Client
from datetime import datetime, timezone
import math
from zoneinfo import ZoneInfo
from dateutil import parser
app = Flask(__name__)


# Hora local (España)
local_tz = ZoneInfo("Europe/Madrid")

# Conexión a base de datos Supabase
SUPABASE_URL = "https://qovpbfngsyaenrwaxoix.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFvdnBiZm5nc3lhZW5yd2F4b2l4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzI5NDI3NSwiZXhwIjoyMDYyODcwMjc1fQ.Y0PW-AkWBvgSzm7bygTUD85fLuHdy0Im7k4oad21qOc"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Obtener datos desde la base de datos
def obtener_aparcamientos():
    try:
        # Obtener todos los aparcamientos
        response = supabase.table("aparcamientos").select("*").execute()
        aparcamientos = response.data or []
        ahora_local = datetime.now(tz=local_tz)

        # Revisar tiempos y actualizar estado
        for ap in aparcamientos:
            tiempo = ap.get("tiempo")
            if tiempo and ap.get("estado") != 0:
                try:
                    tiempo_dt = parser.isoparse(tiempo)
                    tiempo_dt = tiempo_dt.astimezone(local_tz)
                    if tiempo_dt < ahora_local:
                        supabase.table("aparcamientos").update({"estado": 0}).eq("id", ap["id"]).execute()
                except Exception as e:
                    print("⛔ Error analizando tiempo:", e)

        response_final = supabase.table("aparcamientos").select("*").eq("estado", 0).execute()
        return response_final.data
    except Exception as e:
        print("❌ Error al consultar Supabase:", e)
        return []
 
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

# Ruta para que aparezcan los aparcamientos en grabar
@app.route("/todos")
def obtener_todos():
    try:
        response = supabase.table("aparcamientos").select("*").execute()
        return jsonify(response.data)
    except Exception as e:
        print("Error al obtener aparcamientos:", e)
        return jsonify({"error": "No se pudieron obtener los aparcamientos"}), 500


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
# Ruta para buscar aparcamientos
@app.route("/buscar")
def buscar_html():
    return render_template("index.html")

# Ruta para grabar aparcamientos
@app.route("/grabar", methods=["POST", "GET"])
def grabar_aparcamiento():
    if request.method == "GET":
        try:
            response = supabase.table("aparcamientos").select("*").execute()
            aparcamientos = response.data if response.data else []
            return render_template("index.html", aparcamientos=aparcamientos)
        except Exception as e:
            print("Error al consultar Supabase:", e)
            return render_template("index.html", codigos=[])
    # POST
    data = request.get_json()
    lat = data.get("latitud")
    lon = data.get("longitud")
    calle = data.get("calle", "")
    codigo = data.get("codigo", "")
    if lat is None or lon is None:
        return jsonify({"error": "Faltan coordenadas"}), 400
    try:
        response = supabase.table("aparcamientos").insert({
            "latitud": lat,
            "longitud": lon,
            "codigo": codigo,
            "calle": calle,
            "estado": 0
        }).execute()
    
        # Verifica si hay errores en la respuesta (depende de la versión)
        if response.data:
            return jsonify({"mensaje": "Aparcamiento guardado correctamente"}), 200
        else:
            return jsonify({"error": "No se insertó ningún dato"}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Error al insertar en Supabase"}), 500

if __name__ == "__main__":
    app.run(port=5050, debug=True)