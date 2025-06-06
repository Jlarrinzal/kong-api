import requests
from pymongo import MongoClient
import os
from services.mongo_service import delete_service_from_db, insert_service
from dotenv import load_dotenv
load_dotenv()

KONG_ADMIN_URL = os.getenv("KONG_ADMIN_URL")

def plugin_exists(route_name, plugin_name):
    resp = requests.get(f"{KONG_ADMIN_URL}/routes/{route_name}/plugins")
    if resp.status_code != 200:
        return False
    plugins = resp.json().get("data", [])
    return any(plugin["name"] == plugin_name for plugin in plugins)

def exists_service(name):
    return requests.get(f"{KONG_ADMIN_URL}/services/{name}").status_code == 200

def exists_route(name):
    return requests.get(f"{KONG_ADMIN_URL}/routes/{name}").status_code == 200

def configure_simple_service(service_name, service_url):
    domain = f"{service_name}.proxy.upcxels.upc.edu"
    service_kong_name = f"proxy-service-{service_name}"
    route_kong_name = f"proxy-{service_name}"

    created = {"services": [], "routes": []}
    skipped = {"services": [], "routes": []}

    # ───── Servicio ─────
    if not exists_service(service_kong_name):
        r = requests.post(f"{KONG_ADMIN_URL}/services", data={
            "name": service_kong_name,
            "url": service_url
        })
        if r.status_code in [200, 201]:
            created["services"].append(service_kong_name)
        elif r.status_code == 409:
            skipped["services"].append(service_kong_name)
        else:
            print(f"❌ Error creando servicio {service_kong_name}: {r.text}")
    else:
        skipped["services"].append(service_kong_name)

    # ───── Ruta ─────
    if not exists_route(route_kong_name):
        r = requests.post(f"{KONG_ADMIN_URL}/services/{service_kong_name}/routes", data={
            "name": route_kong_name,
            "hosts[]": domain,
            "paths[]": "/",
            "strip_path": "false",
            "https_redirect_status_code": 426
        })
        if r.status_code in [200, 201]:
            created["routes"].append(route_kong_name)
        elif r.status_code == 409:
            skipped["routes"].append(route_kong_name)
        else:
            print(f"❌ Error creando ruta {route_kong_name}: {r.text}")
    else:
        skipped["routes"].append(route_kong_name)

    return {
        "proxy_url": f"https://{domain}",
        "created": created,
        "skipped": skipped
    }

def configure_jwt_service(service_name, service_url):
    domain = f"{service_name}.proxy.upcxels.upc.edu"
    secret = f"{service_name}1234"

    created = {"services": [], "routes": [], "plugins": []}
    skipped = {"services": [], "routes": [], "plugins": []}

    # ───── Servicio real (proxy) ─────
    proxy_service_name = f"proxy-service-{service_name}"
    if not exists_service(proxy_service_name):
        r = requests.post(f"{KONG_ADMIN_URL}/services", data={
            "name": proxy_service_name,
            "url": service_url
        })
        if r.status_code in [200, 201]:
            created["services"].append(proxy_service_name)
        elif r.status_code == 409:
            skipped["services"].append(proxy_service_name)
        else:
            print(f"❌ Error creando servicio {proxy_service_name}: {r.text}")
    else:
        skipped["services"].append(proxy_service_name)

    # ───── Ruta real protegida ─────
    proxy_route_name = f"proxy-{service_name}"
    if not exists_route(proxy_route_name):
        r = requests.post(f"{KONG_ADMIN_URL}/services/{proxy_service_name}/routes", data={
            "name": proxy_route_name,
            "hosts[]": domain,
            "paths[]": "/",
            "strip_path": "false"
        })
        if r.status_code in [200, 201]:
            created["routes"].append(proxy_route_name)
        elif r.status_code == 409:
            skipped["routes"].append(proxy_route_name)
        else:
            print(f"❌ Error creando ruta {proxy_route_name}: {r.text}")
    else:
        skipped["routes"].append(proxy_route_name)

    # ───── Plugin: jwt_cookie_validator ─────
    if not plugin_exists(proxy_route_name, "jwt_cookie_validator"):
        r = requests.post(f"{KONG_ADMIN_URL}/routes/{proxy_route_name}/plugins", data={
            "name": "jwt_cookie_validator",
            "config.secret": secret,
            "config.failure_url": f"https://{domain}/__LAUNCH__"
        })
        if r.status_code in [200, 201]:
            created["plugins"].append("jwt_cookie_validator")
        else:
            skipped["plugins"].append("jwt_cookie_validator")
    else:
        skipped["plugins"].append("jwt_cookie_validator")

    # ───── Servicio dummy para JWT ─────
    launch_service_name = f"launch-jwt-service-{service_name}"
    if not exists_service(launch_service_name):
        r = requests.post(f"{KONG_ADMIN_URL}/services", data={
            "name": launch_service_name,
            "url": "https://example.com"
        })
        if r.status_code in [200, 201]:
            created["services"].append(launch_service_name)
        elif r.status_code == 409:
            skipped["services"].append(launch_service_name)
        else:
            print(f"❌ Error creando servicio {launch_service_name}: {r.text}")
    else:
        skipped["services"].append(launch_service_name)

    # ───── Ruta JWT ─────
    launch_route_name = f"launch-jwt-{service_name}"
    if not exists_route(launch_route_name):
        r = requests.post(f"{KONG_ADMIN_URL}/services/{launch_service_name}/routes", data={
            "name": launch_route_name,
            "hosts[]": domain,
            "paths[]": "/__LAUNCH__",
            "strip_path": "false"
        })
        if r.status_code in [200, 201]:
            created["routes"].append(launch_route_name)
        elif r.status_code == 409:
            skipped["routes"].append(launch_route_name)
        else:
            print(f"❌ Error creando ruta {launch_route_name}: {r.text}")
    else:
        skipped["routes"].append(launch_route_name)

    # ───── Plugin: jwt_validator ─────
    if not plugin_exists(launch_route_name, "jwt_validator"):
        r = requests.post(f"{KONG_ADMIN_URL}/routes/{launch_route_name}/plugins", data={
            "name": "jwt_validator",
            "config.secret": secret,
            "config.success_url": f"https://{domain}",
            "config.failure_url": "https://example.com",
            "config.domain": domain
        })
        if r.status_code in [200, 201]:
            created["plugins"].append("jwt_validator")
        else:
            skipped["plugins"].append("jwt_validator")
    else:
        skipped["plugins"].append("jwt_validator")
        
    # ───── Guardar en Mongo solo si todo fue creado ─────
    required_services = [proxy_service_name, launch_service_name]
    required_routes = [proxy_route_name, launch_route_name]
    required_plugins = ["jwt_cookie_validator", "jwt_validator"]

    all_services_created = all(s in created["services"] for s in required_services)
    all_routes_created = all(r in created["routes"] for r in required_routes)
    all_plugins_created = all(p in created["plugins"] for p in required_plugins)

    if all_services_created and all_routes_created and all_plugins_created:
        insert_service(service_name, secret)

    return {
        "secret": secret,
        "launch_url": f"https://{domain}/__LAUNCH__?token=<JWT>",
        "created": created,
        "skipped": skipped
    }

def get_all_routes():
    resp = requests.get(f"{KONG_ADMIN_URL}/routes")
    if resp.status_code == 200:
        return resp.json().get("data", [])
    else:
        return []

def get_all_services():
    resp = requests.get(f"{KONG_ADMIN_URL}/services")
    if resp.status_code == 200:
        return resp.json().get("data", [])
    else:
        return []

def get_routes_by_service(service_name):
    possible_service_names = [
        f"proxy-{service_name}",
        f"launch-jwt-{service_name}",
        f"proxy-service-{service_name}",
        f"launch-jwt-service-{service_name}"
    ]

    all_routes = []

    for full_name in possible_service_names:
        resp = requests.get(f"{KONG_ADMIN_URL}/services/{full_name}/routes")
        if resp.status_code == 200:
            all_routes.extend(resp.json().get("data", []))

    if not all_routes:
        return {"error": "Service not found or has no routes"}
    return all_routes

def get_service_by_name(service_name):
    possible_names = [
        f"proxy-service-{service_name}",
        f"launch-jwt-service-{service_name}"
    ]

    all_services = []

    for name in possible_names:
        resp = requests.get(f"{KONG_ADMIN_URL}/services/{name}")
        if resp.status_code == 200:
            all_services.append(resp.json())

    if all_services:
        return all_services
    else:
        return {"error": "Service not found"}

def get_all_kong_resources():
    services = get_all_services()
    routes = get_all_routes()
    return {
        "services": services,
        "routes": routes
    }

def delete_service(service_name):
    route_names = [f"launch-jwt-{service_name}", f"proxy-{service_name}"]
    service_names = [f"launch-jwt-service-{service_name}", f"proxy-service-{service_name}"]

    deleted = {"routes": [], "services": []}
    not_found = {"routes": [], "services": []}

    # Eliminar rutas si existen
    for route in route_names:
        check = requests.get(f"{KONG_ADMIN_URL}/routes/{route}")
        if check.status_code == 200:
            r = requests.delete(f"{KONG_ADMIN_URL}/routes/{route}")
            if r.status_code == 204:
                deleted["routes"].append(route)
        else:
            not_found["routes"].append(route)

    # Eliminar servicios si existen
    for service in service_names:
        check = requests.get(f"{KONG_ADMIN_URL}/services/{service}")
        if check.status_code == 200:
            r = requests.delete(f"{KONG_ADMIN_URL}/services/{service}")
            if r.status_code == 204:
                deleted["services"].append(service)
        else:
            not_found["services"].append(service)
            
    deleted["db"] = delete_service_from_db(service_name)

    return deleted, not_found

