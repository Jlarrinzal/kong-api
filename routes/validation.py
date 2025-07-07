from flask import Blueprint, request, jsonify
from pymongo import MongoClient
import os
import time
import requests
import secrets
import hashlib
import geoip2.database
from cryptography.fernet import Fernet
from dotenv import load_dotenv
load_dotenv()

validation_blueprint = Blueprint("validation", __name__)

# Conexión a MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["kong_api_db"]
policies_collection = db["policies"]
requests_collection = db["requests"]
services_collection = db["services"]

FERNET_KEY = os.getenv("FERNET_KEY").encode()
fernet = Fernet(FERNET_KEY)

db_path = os.path.join("geodb", "GeoLite2-Country.mmdb")
reader = geoip2.database.Reader(db_path)

def get_country_from_ip(ip):
    try:
        response = reader.country(ip)
        return response.country.iso_code
    except geoip2.errors.AddressNotFoundError:
        return None
    except Exception as e:
        print(f"Error getting country for IP {ip}: {e}")
        return None

# API para saber la geolocalización de una IP, tiene límite de uso
# def get_country_from_ip(ip):
#     try:
#         headers = {
#             "User-Agent": "Mozilla/5.0"
#         }
#         response = requests.get(f"https://ipapi.co/{ip}/json/", headers=headers)
#         if response.status_code == 200:
#             data = response.json()
#             return data.get("country")
#         else:
#             print(f"Error: status code {response.status_code}")
#     except Exception as e:
#         print(f"Error retrieving country for IP {ip}: {e}")
#     return None

@validation_blueprint.route("/validate-ip", methods=["POST"])
def validate_ip():
    data = request.get_json()

    ip = data.get("ip")
    domain = data.get("domain")

    if not ip or not domain:
        return jsonify({"allowed": False, "reason": "Missing IP or domain"}), 400

    policy = policies_collection.find_one({ "domain": domain })

    if not policy:
        return jsonify({"allowed": False, "reason": "Domain not found"}), 404

    allowed_ips = policy.get("allowed_ips", [])
    allowed_countries = policy.get("allowed_countries", [])

    if ip in allowed_ips:
        if allowed_countries:
            country = get_country_from_ip(ip)
            if country:
                if country not in allowed_countries:
                    return jsonify({
                        "allowed": False,
                        "reason": f"Access from country '{country}' is not allowed"
                    }), 403
                return jsonify({ "allowed": True, "country": country }), 200
            else:
                return jsonify({
                    "allowed": False,
                    "reason": "Could not determine country"
                }), 403
        else:
            return jsonify({ "allowed": True }), 200
    else:
        return jsonify({ "allowed": False, "reason": "IP not allowed" }), 403

@validation_blueprint.route("/add-policy", methods=["POST"])
def add_policy():
    data = request.get_json()

    domain = data.get("domain")
    allowed_ips = data.get("allowed_ips")
    allowed_countries = data.get("allowed_countries", [])
    request_limit = data.get("request_limit")

    if not domain or not allowed_ips or not isinstance(allowed_ips, list):
        return jsonify({
            "error": "Invalid input. 'domain' and 'allowed_ips' (list) required."
        }), 400
    
    if not isinstance(allowed_countries, list):
        return jsonify({
            "error": "'allowed_countries' must be a list if provided."
        }), 400

    update_fields = {
        "allowed_ips": allowed_ips,
        "allowed_countries": allowed_countries
    }

    if request_limit is not None:
        update_fields["request_limit"] = request_limit

    policies_collection.update_one(
        { "domain": domain },
        { "$set": update_fields },
        upsert=True
    )

    return jsonify({
        "message": "Policy added/updated successfully",
        "domain": domain,
        "allowed_ips": allowed_ips,
        "allowed_countries": allowed_countries,
        "request_limit": request_limit
    }), 200
    
@validation_blueprint.route("/validate-request", methods=["POST"])
def validate_and_log_request():
    data = request.get_json()
    domain = data.get("domain")
    ip = data.get("ip")

    if not domain or not ip:
        return jsonify({ "error": "Missing 'domain' or 'ip'" }), 400

    # Obtener la política del dominio
    policy = policies_collection.find_one({ "domain": domain })
    if not policy:
        return jsonify({ "error": f"No policy found for domain {domain}" }), 404

    request_limit = policy.get("request_limit")
    if request_limit is None:
        request_limit = float("inf")

    # Buscar si ya existe un registro para esta IP + dominio
    existing = requests_collection.find_one({ "domain": domain, "ip": ip })

    if existing:
        num_requests = len(existing.get("timestamps", []))
    else:
        num_requests = 0

    if num_requests >= request_limit:
        return jsonify({
            "allowed": False,
            "reason": "Request limit exceeded",
            "total_requests": num_requests
        }), 429

    # Agregar el timestamp actual
    timestamp = int(time.time())
    if existing:
        requests_collection.update_one(
            { "domain": domain, "ip": ip },
            { "$push": { "timestamps": timestamp } }
        )
    else:
        requests_collection.insert_one({
            "domain": domain,
            "ip": ip,
            "timestamps": [timestamp]
        })

    return jsonify({
        "allowed": True,
        "total_requests": num_requests + 1,
        "request_limit": request_limit,
    }), 200

@validation_blueprint.route("/odrl-export/<domain>", methods=["GET"])
def export_odrl_policy(domain):
    policy = policies_collection.find_one({ "domain": domain })

    if not policy:
        return jsonify({ "error": f"No policy found for domain {domain}" }), 404

    allowed_ips = policy.get("allowed_ips", [])
    allowed_countries = policy.get("allowed_countries", [])
    request_limit = policy.get("request_limit")

    odrl_policy = {
        "@context": "http://www.w3.org/ns/odrl.jsonld",
        "uid": f"http://kong-api.local/policy:{domain}",
        "type": "Set",
        "profile": "http://kong-api.local/policies",
        "permission": [
            {
                "target": domain,
                "action": "use",
                "assignee": [{"uid": f"ip:{ip}"} for ip in allowed_ips],
                "constraint": []
            }
        ]
    }

    if request_limit:
        odrl_policy["permission"][0]["constraint"].append({
            "name": "count",
            "operator": "lteq",
            "rightOperand": request_limit
        })
        
    if allowed_countries:
        odrl_policy["permission"][0]["constraint"].append({
            "name": "country",
            "operator": "isAnyOf",
            "rightOperand": allowed_countries
        })

    return jsonify(odrl_policy), 200

@validation_blueprint.route("/import-odrl-policy", methods=["POST"])
def import_odrl_policy():
    odrl_data = request.get_json()

    # Validación mínima de ODRL
    if not odrl_data or "permission" not in odrl_data or not isinstance(odrl_data["permission"], list):
        return jsonify({ "error": "Invalid ODRL format" }), 400

    permission = odrl_data["permission"][0]
    domain = permission.get("target")

    if not domain:
        return jsonify({ "error": "'target' (domain) is required in permission" }), 400

    # Extraer IPs permitidas
    assignees = permission.get("assignee", [])
    allowed_ips = [a["uid"].split("ip:")[1] for a in assignees if a.get("uid", "").startswith("ip:")]

    # Extraer constraints
    constraints = permission.get("constraint", [])
    request_limit = None
    allowed_countries = []

    for constraint in constraints:
        name = constraint.get("name")
        if name == "count":
            request_limit = constraint.get("rightOperand")
        elif name == "country":
            allowed_countries = constraint.get("rightOperand", [])

    # Guardar política en MongoDB
    policy_data = {
        "allowed_ips": allowed_ips,
        "allowed_countries": allowed_countries,
        "request_limit": request_limit,
        "imported_policy": odrl_data
    }

    policies_collection.update_one(
        { "domain": domain },
        { "$set": policy_data },
        upsert=True
    )

    return jsonify({
        "message": "ODRL policy imported and stored successfully",
        "domain": domain,
        "allowed_ips": allowed_ips,
        "allowed_countries": allowed_countries,
        "request_limit": request_limit
    }), 200

@validation_blueprint.route("/register-kong-service", methods=["POST"])
def register_kong_service():
    data = request.get_json()
    service_name = data.get("service_name")
    failure_url = data.get("failure_url")
    proxied_url = data.get("proxied_url")

    if not service_name or not failure_url or not proxied_url:
        return jsonify({ "error": "Missing required fields" }), 400

    KONG_ADMIN_URL = "http://localhost:9001"
    DOMAIN = f"{service_name}.proxy.upcxels.upc.edu"

    # Generar secreto
    raw_secret, encrypted_secret = generate_secret()

    # Eliminar configuración previa
    for route in [f"launch-jwt-{service_name}", f"proxy-{service_name}"]:
        requests.delete(f"{KONG_ADMIN_URL}/routes/{route}")

    for service in [f"launch-jwt-service-{service_name}", f"proxy-service-{service_name}"]:
        requests.delete(f"{KONG_ADMIN_URL}/services/{service}")

    # Crear servicio real
    requests.post(f"{KONG_ADMIN_URL}/services", data={
        "name": f"proxy-service-{service_name}",
        "url": proxied_url
    })

    # Crear ruta principal
    requests.post(f"{KONG_ADMIN_URL}/services/proxy-service-{service_name}/routes", data={
        "name": f"proxy-{service_name}",
        "hosts[]": DOMAIN,
        "paths[]": "/",
        "strip_path": "false"
    })

    # Añadir plugin de validación por cookie
    requests.post(f"{KONG_ADMIN_URL}/routes/proxy-{service_name}/plugins", data={
        "name": "jwt_policy_cookie_validator",
        "config.secret": raw_secret,
        "config.failure_url": failure_url
    })

    # Añadir plugin de rate limiting
    requests.post(f"{KONG_ADMIN_URL}/routes/proxy-{service_name}/plugins", data={
        "name": "rate-limiting",
        "config.minute": "20",
        "config.policy": "local"
    })

    # Servicio dummy JWT
    requests.post(f"{KONG_ADMIN_URL}/services", data={
        "name": f"launch-jwt-service-{service_name}",
        "url": "https://example.com"
    })

    # Ruta para JWT
    requests.post(f"{KONG_ADMIN_URL}/services/launch-jwt-service-{service_name}/routes", data={
        "name": f"launch-jwt-{service_name}",
        "hosts[]": DOMAIN,
        "paths[]": "/__LAUNCH__",
        "strip_path": "false"
    })

    # Plugin para lanzar JWT y poner cookie
    requests.post(f"{KONG_ADMIN_URL}/routes/launch-jwt-{service_name}/plugins", data={
        "name": "jwt_validator",
        "config.secret": raw_secret,
        "config.success_url": f"https://{DOMAIN}",
        "config.failure_url": failure_url,
        "config.domain": DOMAIN
    })

    # Guardar en MongoDB
    services_collection.insert_one({
        "domain": DOMAIN,
        "encrypted_secret": encrypted_secret
    })

    return jsonify({
        "message": "✅ Servicio registrado con éxito",
        "domain": DOMAIN,
        "launch_url": f"https://{DOMAIN}/__LAUNCH__?token=<JWT>"
    }), 200

def generate_secret():
    """Genera un secreto plano, lo cifra y devuelve (secreto plano, secreto cifrado)."""
    raw_secret = secrets.token_hex(32)
    encrypted_secret = fernet.encrypt(raw_secret.encode()).decode()
    return raw_secret, encrypted_secret

def decrypt_secret(encrypted_secret: str) -> str:
    return fernet.decrypt(encrypted_secret.encode()).decode()