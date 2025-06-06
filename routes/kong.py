from flask import Blueprint, request, jsonify
from pymongo import MongoClient
import jwt
import os
import datetime
import time
from services.kong_service_configurator import configure_jwt_service, delete_service, configure_simple_service, get_all_kong_resources, get_all_routes, get_all_services, get_routes_by_service, get_service_by_name

kong_blueprint = Blueprint("kong", __name__)

@kong_blueprint.route("/create-jwt-service", methods=["POST"])
def setup_kong():
    """
    Crear configuración JWT para un servicio en Kong
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - service_name
            - service_url
          properties:
            service_name:
              type: string
            service_url:
              type: string
    responses:
      200:
        description: Configuración JWT creada correctamente
      400:
        description: Faltan parámetros
    """
    data = request.get_json()
    service_name = data.get("service_name")
    service_url = data.get("service_url")

    if not service_name or not service_url:
        return jsonify({"error": "Missing service_name or service_url"}), 400

    result = configure_jwt_service(service_name, service_url)
    return jsonify(result), 200

@kong_blueprint.route("/create-simple-service", methods=["POST"])
def setup_simple_proxy():
    """
    Crear un servicio proxy simple en Kong
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - service_name
            - service_url
          properties:
            service_name:
              type: string
            service_url:
              type: string
    responses:
      200:
        description: Servicio simple creado correctamente
      400:
        description: Faltan parámetros
    """
    data = request.get_json()
    service_name = data.get("service_name")
    service_url = data.get("service_url")

    if not service_name or not service_url:
        return jsonify({"error": "Missing service_name or service_url"}), 400

    result = configure_simple_service(service_name, service_url)
    return jsonify(result), 200

@kong_blueprint.route("/kong/routes", methods=["GET"])
def api_get_routes():
    """
    Obtener todas las rutas de Kong
    ---
    responses:
      200:
        description: Lista de rutas
        schema:
          type: array
          items:
            type: object
    """
    return jsonify(get_all_routes()), 200

@kong_blueprint.route("/kong/services", methods=["GET"])
def api_get_services():
    """
    Obtener todos los servicios registrados en Kong
    ---
    responses:
      200:
        description: Lista de servicios
        schema:
          type: array
          items:
            type: object
    """
    return jsonify(get_all_services()), 200

@kong_blueprint.route("/kong/routes/<service_name>", methods=["GET"])
def api_get_routes_by_service(service_name):
    """
    Obtener rutas asociadas a un servicio específico
    ---
    parameters:
      - name: service_name
        in: path
        required: true
        type: string
    responses:
      200:
        description: Rutas asociadas al servicio
    """
    return jsonify(get_routes_by_service(service_name)), 200

@kong_blueprint.route("/kong/services/<service_name>", methods=["GET"])
def api_get_service_by_name(service_name):
    """
    Obtener detalles de un servicio específico
    ---
    parameters:
      - name: service_name
        in: path
        required: true
        type: string
    responses:
      200:
        description: Información del servicio
    """
    return jsonify(get_service_by_name(service_name)), 200

@kong_blueprint.route("/kong/resources", methods=["GET"])
def api_get_all_kong_resources():
    """
    Obtener todos los servicios y rutas registrados en Kong
    ---
    responses:
      200:
        description: Servicios y rutas de Kong
        schema:
          type: object
          properties:
            services:
              type: array
              items:
                type: object
            routes:
              type: array
              items:
                type: object
    """
    return jsonify(get_all_kong_resources()), 200

@kong_blueprint.route("/delete-service", methods=["DELETE"])
def delete_kong():
    """
    Eliminar las rutas y servicios asociados a un nombre
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - service_name
          properties:
            service_name:
              type: string
    responses:
      200:
        description: Resultado del borrado de recursos
      400:
        description: Faltan parámetros
    """
    data = request.get_json()
    service_name = data.get("service_name")

    if not service_name:
        return jsonify({"error": "Missing service_name"}), 400

    deleted, not_found = delete_service(service_name)

    response = {
        "service_name": service_name,
        "deleted": deleted
    }

    if deleted["routes"] or deleted["services"]:
        response["message"] = "Some resources were deleted."
    else:
        response["message"] = "No resources existed for this service."

    return jsonify(response), 200