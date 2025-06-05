import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
services_collection = db[COLLECTION_NAME]

def insert_service(service_name, secret):
    existing = services_collection.find_one({"service_name": service_name})
    if not existing:
        services_collection.insert_one({
            "service_name": service_name,
            "secret": secret
        })
