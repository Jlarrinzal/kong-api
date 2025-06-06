from flask import Blueprint, request, jsonify
from pymongo import MongoClient
import jwt
import os
import datetime
import time
from services.mongo_service import services_collection

auth_blueprint = Blueprint("auth", __name__)

# SECRET_KEY = 'clave-super-secreta'

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
    """
    Genera un token JWT para un servicio registrado en MongoDB
    ---
    tags:
      - Autenticación
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - service_name
            - minutes
          properties:
            service_name:
              type: string
              description: Nombre del servicio registrado
              example: opendata-gg
            minutes:
              type: integer
              description: Duración del token en minutos
              example: 10
            user:
              type: string
              description: Nombre de usuario a incluir en el token (opcional)
              example: pepito
    responses:
      200:
        description: Token JWT generado correctamente
        schema:
          type: object
          properties:
            token:
              type: string
              description: JWT firmado con el secreto del servicio
      400:
        description: Faltan parámetros obligatorios
      404:
        description: Servicio no encontrado en la base de datos
      500:
        description: No se encontró la clave secreta para el servicio
    """
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