from flask import Blueprint, request, jsonify
from pymongo import MongoClient
import jwt
import os
import datetime
import time
from routes.validation import decrypt_secret
# from services.mongo_service import services_collection

# Conexión a MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["kong_api_db"]
services_collection = db["services"]

auth_blueprint = Blueprint("auth", __name__)

SECRET_KEY = 'clave-super-secreta'

@auth_blueprint.route('/generate-jwt-hardcoded', methods=['GET'])
def generate_jwt():
    username = request.args.get('user', 'testuser')

    payload = {
        'sub': username,
        'iat': int(time.time()),
        # 'exp': int(time.time()) + 10
        'exp': int(time.time()) + 60 * 5
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

    return jsonify({ 'token': token })


@auth_blueprint.route('/generate-jwt', methods=['GET'])
def generate_jwt_from_db():
    domain = request.args.get('domain')
    username = request.args.get('user', 'testuser')

    if not domain:
        return jsonify({ "error": "Missing 'domain' parameter" }), 400

    # Buscar en Mongo
    service = services_collection.find_one({ "domain": domain })
    if not service:
        return jsonify({ "error": f"No service found for domain '{domain}'" }), 404

    encrypted_secret = service.get("encrypted_secret")
    if not encrypted_secret:
        return jsonify({ "error": "Missing encrypted secret in service record" }), 500

    try:
        raw_secret = decrypt_secret(encrypted_secret)
    except Exception as e:
        return jsonify({ "error": f"Failed to decrypt secret: {str(e)}" }), 500

    # Crear el JWT
    payload = {
        "sub": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + 60 * 5  # 5 minutos
    }

    token = jwt.encode(payload, raw_secret, algorithm='HS256')

    return jsonify({ "token": token }), 200

# SECRET_KEY = "mi_clave_secreta"

@auth_blueprint.route('/generate-jwt-policy', methods=['GET'])
def generate_jwt_policy():
    username = request.args.get('user', 'testuser')

    payload = {
        'sub': username,
        'iat': int(time.time()),
        'exp': int(time.time()) + 60 * 5,
        'policies': {
            'permission': [
                {
                    'action': 'READ',
                    'leftOperand': 'location',
                    'operator': 'eq',
                    'rightOperand': 'EU'
                },
                {
                    'action': 'READ',
                    'leftOperand': 'location',
                    'operator': 'eq',
                    'rightOperand': 'ESP'
                }
            ],
            'prohibition': [
                {
                    'target': 'https://prueba-obx.proxy.upcxels.upc.edu/alerting',
                    'action': 'not_show'
                }
            ]
        }
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    
    return jsonify({ 'token': token })

# @auth_blueprint.route('/generate-jwt', methods=['POST'])
# def generate_jwt():
#     """
#     Genera un token JWT para un servicio registrado en MongoDB
#     ---
#     tags:
#       - Autenticación
#     parameters:
#       - in: body
#         name: body
#         required: true
#         schema:
#           type: object
#           required:
#             - service_name
#             - minutes
#           properties:
#             service_name:
#               type: string
#               description: Nombre del servicio registrado
#               example: opendata-gg
#             minutes:
#               type: integer
#               description: Duración del token en minutos
#               example: 10
#             user:
#               type: string
#               description: Nombre de usuario a incluir en el token (opcional)
#               example: pepito
#     responses:
#       200:
#         description: Token JWT generado correctamente
#         schema:
#           type: object
#           properties:
#             token:
#               type: string
#               description: JWT firmado con el secreto del servicio
#       400:
#         description: Faltan parámetros obligatorios
#       404:
#         description: Servicio no encontrado en la base de datos
#       500:
#         description: No se encontró la clave secreta para el servicio
#     """
#     data = request.get_json()
#     service_name = data.get("service_name")
#     minutes = data.get("minutes")
#     username = data.get("user", "testuser")

#     if not service_name or minutes is None:
#         return jsonify({"error": "Missing service_name or minutes"}), 400

#     service = services_collection.find_one({"service_name": service_name})
#     if not service:
#         return jsonify({"error": "Service not found"}), 404

#     secret = service.get("secret")
#     if not secret:
#         return jsonify({"error": "Secret not found for service"}), 500

#     payload = {
#         'sub': username,
#         'iat': int(time.time()),
#         'exp': int(time.time()) + 60 * int(minutes)
#     }

#     token = jwt.encode(payload, secret, algorithm='HS256')

#     return jsonify({ 'token': token })