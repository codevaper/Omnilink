"""
Municipal connector
-------------------
Wraps the MongoDB `municipal_permits.permit_applications` collection
and exposes it via the same normalized REST/JSON shape as the other
two connectors. This is the ONLY service that should know about
`applicant_fname`, `pan_number`, etc.
"""

import os
from flask import Flask, jsonify, request
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

MONGO_USER = os.getenv("MONGO_USER", "setuadmin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "setupass123")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")

client = MongoClient(
    f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
)

db = client["municipal_permits"]
collection = db["permit_applications"]


def normalize(doc):
    """Map messy permit_applications fields -> canonical field names."""
    app_date = doc.get("application_date")

    return {
        "source_system": "municipal",
        "source_record_id": doc.get("permit_id"),
        "first_name": doc.get("applicant_fname"),
        "last_name": doc.get("applicant_lname"),
        "father_or_guardian_name": doc.get("father_name"),
        "address_line": doc.get("address_line_1"),
        "phone_number": doc.get("contact_number"),
        "pan_number": doc.get("pan_number"),
        "extra": {
            "permit_type": doc.get("permit_type"),
            "application_date": app_date.isoformat() if app_date else None,
            "annual_income": doc.get("annual_income"),
            "status": doc.get("status"),
        },
    }


@app.route("/health")
def health():
    try:
        client.admin.command("ping")
        return jsonify({
            "status": "ok",
            "service": "municipal_connector"
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "service": "municipal_connector",
            "detail": str(e)
        }), 500


@app.route("/records")
def list_records():
    docs = list(collection.find({}))
    return jsonify([normalize(d) for d in docs])


@app.route("/records/search")
def search_by_pan():
    pan = request.args.get("pan")

    if not pan:
        return jsonify({
            "error": "pass ?pan=<PAN_NUMBER>"
        }), 400

    doc = collection.find_one({"pan_number": pan})

    if not doc:
        return jsonify({"error": "not found"}), 404

    return jsonify(normalize(doc))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)