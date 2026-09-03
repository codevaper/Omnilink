import os
import uuid
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from kafka_producer import publish_event


load_dotenv()

app = Flask(__name__)
CORS(app)

TOPIC = "application_events"

CONNECTORS = {
    "ration_card": "http://localhost:5001",
    "municipal": "http://localhost:5002",
    "scholarship": "http://localhost:5003",
}


def generate_unified_app_id():
    return f"OMNI-{uuid.uuid4().hex[:10].upper()}"


def get_applicant_name(record):
    first_name = (
        record.get("first_name")
        or record.get("student_first")
        or record.get("applicant_fname")
        or ""
    )

    last_name = (
        record.get("last_name")
        or record.get("student_last")
        or record.get("applicant_lname")
        or ""
    )

    name = f"{first_name} {last_name}".strip()

    return name or "Unknown Applicant"


@app.get("/health")
def health():
    return jsonify({
        "status": "ok"
    })


@app.post("/applications")
def submit_application():
    data = request.get_json(silent=True) or {}

    source_system = data.get("source_system")
    pan_number = data.get("pan_number")
    request_type = data.get("request_type")

    if not source_system:
        return jsonify({
            "error": "source_system is required"
        }), 400

    if not pan_number:
        return jsonify({
            "error": "pan_number is required"
        }), 400

    if not request_type:
        return jsonify({
            "error": "request_type is required"
        }), 400

    if source_system not in CONNECTORS:
        return jsonify({
            "error": f"Unknown source_system: {source_system}"
        }), 400

    connector_url = CONNECTORS[source_system]

    try:
        response = requests.get(
            f"{connector_url}/records/search",
            params={"pan": pan_number},
            timeout=10
        )
    except requests.RequestException as exc:
        return jsonify({
            "error": "Could not reach connector",
            "details": str(exc)
        }), 502

    if response.status_code != 200:
        return jsonify({
            "error": "Connector returned an error",
            "details": response.text
        }), 502

    try:
        connector_data = response.json()
    except ValueError:
        return jsonify({
            "error": "Connector returned invalid JSON"
        }), 502

    # The current connector APIs return the applicant record directly.
    record = connector_data

    if not record:
        return jsonify({
            "error": "No applicant record found",
            "source_system": source_system,
            "pan_number": pan_number
        }), 404

    applicant_name = get_applicant_name(record)

    unified_app_id = generate_unified_app_id()

    event = {
        "event_type": "application.submitted",
        "unified_app_id": unified_app_id,
        "applicant_name": applicant_name,
        "source_system": source_system,
        "pan_number": pan_number,
        "request_type": request_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "record": record,
    }

    try:
        publish_event(TOPIC, event)
    except Exception as exc:
        return jsonify({
            "error": "Failed to publish application event",
            "details": str(exc)
        }), 500

    return jsonify({
        "message": (
            f"Application submitted for {applicant_name} "
            f"via {source_system}. "
            f"Event published to Kafka topic {TOPIC}."
        ),
        "unified_app_id": unified_app_id,
        "applicant_name": applicant_name,
        "source_system": source_system,
        "request_type": request_type
    }), 201


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )