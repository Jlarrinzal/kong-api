from flask import Blueprint, request, jsonify
from pymongo import MongoClient
import jwt
import os
import datetime
import time
from services.mongo_service import services_collection

auth_blueprint = Blueprint("auth", __name__)

# JWT_SECRET = "tu_clave_super_secreta"
# JWT_ALGORITHM = "HS256"
# KONG_KEY_ACTIVIDADES = os.getenv("KONG_KEY")
# KONG_SECRET_ACTIVIDADES = os.getenv("KONG_SECRET")

# KONG_KEY_GRAFANA = os.getenv("KONG_KEY")
# KONG_SECRET_GRAFANA = os.getenv("KONG_SECRET")

# mongo_client = MongoClient("mongodb://localhost:27017/")
# db = mongo_client["kong_gateway"]
# purchases = db["purchases"]

# @auth_blueprint.route("/validate-access", methods=["GET"])
# def validate_access():
#     auth_header = request.headers.get("Authorization", "")
#     service = request.headers.get("Service", "")

#     if not auth_header or not service:
#         return jsonify({"error": "Faltan headers"}), 400

#     token = auth_header.replace("Bearer ", "")

#     try:
#         payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
#     except jwt.ExpiredSignatureError:
#         return jsonify({"error": "Token expirado"}), 401
#     except jwt.InvalidTokenError:
#         return jsonify({"error": "Token inválido"}), 401

#     user = payload.get("sub")
#     if not user:
#         return jsonify({"error": "Token sin usuario"}), 401

#     # Verificamos en Mongo si el usuario compró ese servicio
#     result = purchases.find_one({"user": user, "service": service})
#     if not result:
#         return jsonify({"error": "No autorizado"}), 403

#     return jsonify({"message": "Acceso permitido"}), 200

# @auth_blueprint.route("/access-url", methods=["GET"])
# def access_url():
#     auth_header = request.headers.get("Authorization", "")
#     service = request.headers.get("Service", "")

#     if not auth_header or not service:
#         return jsonify({"error": "Faltan headers"}), 400

#     token = auth_header.replace("Bearer ", "")

#     try:
#         payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
#     except jwt.ExpiredSignatureError:
#         return jsonify({"error": "Token expirado"}), 401
#     except jwt.InvalidTokenError:
#         return jsonify({"error": "Token inválido"}), 401

#     user = payload.get("sub")
#     if not user:
#         return jsonify({"error": "Token sin usuario"}), 401

#     # Verificar si el usuario ha comprado ese servicio
#     result = purchases.find_one({"user": user, "service": service})
#     if not result:
#         return jsonify({"error": "No autorizado"}), 403

#     # Buscar la URL del servicio en la colección services
#     services = db["services"]
#     service_data = services.find_one({"name": service})
#     if not service_data:
#         return jsonify({"error": "Servicio no encontrado"}), 404
    
#     kong_token = jwt.encode(
#         {
#             "iss": KONG_KEY_ACTIVIDADES,    # esta es la key que te dio Kong
#             "sub": user,
#             "exp": 9999999999
#         },
#         KONG_SECRET_ACTIVIDADES,          # esta es la secret que te dio Kong
#         JWT_ALGORITHM
#     )

#     return jsonify({
#         "token": kong_token,
#         "url": service_data["url"]
#     }), 200

# @auth_blueprint.route("/access-url-cookie", methods=["GET"])
# def access_url_cookie():
#     cookie_token = request.cookies.get("auth_token")
#     service = request.headers.get("Service")

#     if not cookie_token or not service:
#         return jsonify({"error": "Faltan cookie o header 'Service'"}), 400

#     try:
#         payload = jwt.decode(cookie_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
#     except jwt.ExpiredSignatureError:
#         return jsonify({"error": "Token expirado"}), 401
#     except jwt.InvalidTokenError:
#         return jsonify({"error": "Token inválido"}), 401

#     user = payload.get("sub")
#     if not user:
#         return jsonify({"error": "Token sin usuario"}), 401

#     # Verificar si el usuario ha comprado ese servicio
#     result = purchases.find_one({"user": user, "service": service})
#     if not result:
#         return jsonify({"error": "No autorizado"}), 403

#     # Obtener la URL desde la colección de servicios
#     services = db["services"]
#     service_data = services.find_one({"name": service})
#     if not service_data:
#         return jsonify({"error": "Servicio no encontrado"}), 404

#     # return jsonify({"url": service_data["url"]}), 200
    
#     # Crear token JWT que Kong valida
#     kong_token = jwt.encode({
#         "iss": KONG_KEY_GRAFANA,  # la key que te dio Kong
#         "sub": user,
#         "exp": 9999999999
#     }, KONG_SECRET_GRAFANA, algorithm="HS256")

#     return jsonify({
#         "token": kong_token,
#         "url": service_data["url"],
#     }), 200

# @auth_blueprint.route("/grafana-token", methods=["GET"])
# def grafana_token():
#     cookie_token = request.cookies.get("auth_token")
#     if not cookie_token:
#         return jsonify({"error": "Falta token"}), 400

#     try:
#         payload = jwt.decode(cookie_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
#     except Exception:
#         return jsonify({"error": "Token inválido"}), 401

#     user = payload.get("sub")
#     if not user:
#         return jsonify({"error": "Token sin usuario"}), 401

#     result = purchases.find_one({"user": user, "service": "grafana"})
#     if not result:
#         return jsonify({"error": "No autorizado"}), 403

#     # Crear token JWT que Kong valida
#     kong_token = jwt.encode({
#         "iss": "grafana-key",  # la key que te dio Kong
#         "sub": user,
#         "exp": 9999999999
#     }, "grafana-secret", algorithm="HS256")

#     return jsonify({
#         "token": kong_token,
#         "url": "http://grafana.marketplace.test:8000"
#     }), 200



# # Nueva ruta para "comprar" un servicio
# @auth_blueprint.route("/purchases", methods=["POST"])
# def create_purchase():
#     data = request.get_json()
#     user = data.get("user")
#     service = data.get("service")

#     if not user or not service:
#         return jsonify({"error": "user and service are required"}), 400

#     purchases.insert_one({
#         "user": user,
#         "service": service
#     })

#     return jsonify({"message": f"Servicio '{service}' comprado por '{user}'"}), 201

# @auth_blueprint.route("/services", methods=["POST"])
# def create_service():
#     data = request.get_json()
#     name = data.get("name")
#     url = data.get("url")

#     if not name or not url:
#         return jsonify({"error": "name and url are required"}), 400

#     # Insertar en la colección services
#     services = db["services"]
#     existing = services.find_one({"name": name})
#     if existing:
#         return jsonify({"error": "Service already exists"}), 409

#     services.insert_one({"name": name, "url": url})
#     return jsonify({"message": f"Servicio '{name}' registrado correctamente"}), 201

# Clave secreta (debe coincidir con la de validar-jwt.lua)

SECRET_KEY = 'clave-super-secreta'

# @auth_blueprint.route('/generate-jwt-hardcoded', methods=['GET'])
# def generate_jwt():
#     username = request.args.get('user', 'testuser')

#     payload = {
#         'sub': username,
#         'iat': int(time.time()),
#         'exp': int(time.time()) + 60 * 3
#     }

#     token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

#     return jsonify({ 'token': token })


@auth_blueprint.route('/generate-jwt', methods=['POST'])
def generate_jwt():
    data = request.get_json()
    service_name = data.get("service_name")
    minutes = data.get("minutes")
    username = data.get("user", "testuser")

    if not service_name or minutes is None:
        return jsonify({"error": "Missing service_name or minutes"}), 400

    service = services_collection.find_one({"service_name": service_name})
    if not service:
        return jsonify({"error": "Service not found"}), 404

    secret = service.get("secret")
    if not secret:
        return jsonify({"error": "Secret not found for service"}), 500

    payload = {
        'sub': username,
        'iat': int(time.time()),
        'exp': int(time.time()) + 60 * int(minutes)
    }

    token = jwt.encode(payload, secret, algorithm='HS256')

    return jsonify({ 'token': token })