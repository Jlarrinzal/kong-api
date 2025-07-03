from flask import Blueprint, request, jsonify
from pymongo import MongoClient
import os
import time
import requests

validation_blueprint = Blueprint("validation", __name__)

# Conexión a MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["kong_api_db"]
policies_collection = db["policies"]
requests_collection = db["requests"]

def get_country_from_ip(ip):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(f"https://ipapi.co/{ip}/json/", headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get("country")
        else:
            print(f"Error: status code {response.status_code}")
    except Exception as e:
        print(f"Error retrieving country for IP {ip}: {e}")
    return None

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

    # print("🔍 Comparando IP:", repr(ip), "con", [repr(i) for i in allowed_ips])

    if ip in allowed_ips:
        if allowed_countries:
            country = get_country_from_ip(ip)
            if country not in allowed_countries:
                return jsonify({
                    "allowed": False,
                    "reason": f"Access from country '{country}' is not allowed"
                }), 403
            return jsonify({ "allowed": True, "country": country }), 200
            return jsonify({ "allowed": True, "country": "ByPass" }), 200
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