from flask import Blueprint, request, jsonify
from pymongo import MongoClient
import requests

redirect_blueprint = Blueprint("redirects", __name__)

# Mongo config
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["kong_gateway"]
redirects = db["redirects"]

# Kong Admin API base
KONG_ADMIN = "http://localhost:8001"

@redirect_blueprint.route("/redirects", methods=["POST"])
def create_redirect():
    data = request.get_json()
    url = data.get("url")
    ip = data.get("ip")

    if not url or not ip:
        return jsonify({"error": "url and ip are required"}), 400

    # Normaliza host (sin http, slashes...)
    host = url.replace("http://", "").replace("https://", "").strip("/")

    # 1. Crear servicio en Kong
    service_resp = requests.post(f"{KONG_ADMIN}/services", data={
        "name": host.replace(".", "-"),
        "url": f"http://{ip}"
    })

    if service_resp.status_code >= 300:
        return jsonify({"error": "Error creando servicio en Kong", "details": service_resp.text}), 500

    # 2. Crear ruta en Kong
    route_resp = requests.post(f"{KONG_ADMIN}/routes", data={
        "name": f"{host}-route",
        "service.name": host.replace(".", "-"),
        "hosts[]": host
    })

    if route_resp.status_code >= 300:
        return jsonify({"error": "Error creando ruta en Kong", "details": route_resp.text}), 500

    # 3. Guardar en MongoDB
    redirects.insert_one({"url": url, "ip": ip, "service": host.replace(".", "-")})

    return jsonify({"message": "Redirección creada"}), 201

@redirect_blueprint.route("/redirects", methods=["GET"])
def list_redirects():
    data = list(redirects.find({}, {"_id": 0}))
    return jsonify(data)

@redirect_blueprint.route("/redirects", methods=["DELETE"])
def delete_redirect():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "url is required"}), 400

    host = url.replace("http://", "").replace("https://", "").strip("/")

    # Borrar de Kong
    requests.delete(f"{KONG_ADMIN}/routes/{host}-route")
    requests.delete(f"{KONG_ADMIN}/services/{host.replace('.', '-')}")

    # Borrar de Mongo
    redirects.delete_one({"url": url})

    return jsonify({"message": "Redirección eliminada"}), 200
