import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS


app = Flask(__name__)
CORS(app)


GATEWAY_URL = os.getenv(
    "GATEWAY_URL",
    "http://localhost:5000"
)

CAMUNDA_REST_URL = os.getenv(
    "CAMUNDA_REST_URL",
    "http://localhost:8080/engine-rest"
).rstrip("/")

PROCESS_DEFINITION_KEY = "citizen_application_review"
EXCEPTIONS_FILE = Path(__file__).resolve().parent / "exceptions.json"


def load_exceptions():
    if not EXCEPTIONS_FILE.exists():
        return []

    try:
        with open(EXCEPTIONS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return []


def save_exceptions(exceptions):
    with open(EXCEPTIONS_FILE, "w", encoding="utf-8") as file:
        json.dump(exceptions, file, indent=2)


def detect_exceptions(applications):
    exceptions = load_exceptions()

    existing_ids = {
        item.get("unified_app_id")
        for item in exceptions
    }

    for application in applications:
        app_id = application.get("unified_app_id")
        source_system = application.get("source_system")
        status = application.get("status")

        if not app_id:
            continue

        if (
            source_system == "scholarship"
            and status == "UNDER_REVIEW"
            and app_id not in existing_ids
        ):
            exceptions.append({
                "exception_id": f"EXC-{app_id}",
                "unified_app_id": app_id,
                "applicant_name": application.get(
                    "applicant_name",
                    "Unknown Applicant"
                ),
                "source_system": source_system,
                "severity": "MEDIUM",
                "reason": "Manual cross-system verification required",
                "details": (
                    "Scholarship application is under review. "
                    "Official verification is required before "
                    "the application can be finalized."
                ),
                "status": "OPEN",
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "resolved_at": None
            })

    save_exceptions(exceptions)

    return exceptions


def get_process_history(app_id=None):
    params = {
        "processDefinitionKey": PROCESS_DEFINITION_KEY
    }

    if app_id:
        params["processInstanceBusinessKey"] = app_id

    response = requests.get(
        f"{CAMUNDA_REST_URL}/history/process-instance",
        params=params,
        timeout=10
    )

    response.raise_for_status()

    return response.json()


def get_tasks(app_id):
    response = requests.get(
        f"{CAMUNDA_REST_URL}/task",
        params={
            "processDefinitionKey": PROCESS_DEFINITION_KEY,
            "processInstanceBusinessKey": app_id
        },
        timeout=10
    )

    response.raise_for_status()

    return response.json()


def get_process_variables(process_instance_id):
    response = requests.get(
        f"{CAMUNDA_REST_URL}/process-instance/{process_instance_id}/variables",
        timeout=10
    )

    if response.status_code != 200:
        return {}

    data = response.json()

    return {
        name: item.get("value")
        for name, item in data.items()
    }


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "tracker_api"
    })


@app.post("/applications")
def create_application():
    data = request.get_json(silent=True) or {}

    source_system = data.get("source_system")
    pan_number = data.get("pan_number")
    request_type = data.get("request_type")
    consent = data.get("consent")

    if consent is not True:
        return jsonify({
            "error": "Citizen consent is required"
        }), 400

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

    try:
        response = requests.post(
            f"{GATEWAY_URL}/applications",
            json={
                "source_system": source_system,
                "pan_number": pan_number,
                "request_type": request_type
            },
            timeout=15
        )

    except requests.RequestException as exc:
        return jsonify({
            "error": "Could not connect to Gateway",
            "details": str(exc)
        }), 502

    try:
        result = response.json()

    except ValueError:
        return jsonify({
            "error": "Gateway returned invalid JSON"
        }), 502

    return jsonify(result), response.status_code


@app.get("/applications/<app_id>")
def get_application_status(app_id):
    try:
        processes = get_process_history(app_id)

    except requests.RequestException as exc:
        return jsonify({
            "error": "Could not connect to Camunda",
            "details": str(exc)
        }), 502

    if not processes:
        return jsonify({
            "error": "Application not found",
            "unified_app_id": app_id
        }), 404

    processes = sorted(
        processes,
        key=lambda item: item.get("startTime") or "",
        reverse=True
    )

    process = processes[0]

    process_instance_id = process.get("id")

    variables = {}

    if process_instance_id:
        try:
            variables = get_process_variables(
                process_instance_id
            )
        except requests.RequestException:
            variables = {}

    state = process.get("state")

    status = (
        "COMPLETED"
        if state == "COMPLETED"
        else "UNDER_REVIEW"
    )

    return jsonify({
        "unified_app_id": app_id,
        "status": status,
        "process_state": state,
        "process_instance_id": process_instance_id,
        "process_definition": process.get(
            "processDefinitionName",
            "Citizen Application Review"
        ),
        "process_version": process.get(
            "processDefinitionVersion"
        ),
        "started_at": process.get("startTime"),
        "completed_at": process.get("endTime"),
        "variables": variables,
        "checked_at": datetime.now(
            timezone.utc
        ).isoformat()
    })


@app.get("/applications/<app_id>/tasks")
def get_application_tasks(app_id):
    try:
        tasks = get_tasks(app_id)

    except requests.RequestException as exc:
        return jsonify({
            "error": "Could not connect to Camunda",
            "details": str(exc)
        }), 502

    return jsonify({
        "unified_app_id": app_id,
        "tasks": [
            {
                "id": task.get("id"),
                "name": task.get("name"),
                "task_state": task.get("taskState"),
                "created": task.get("created"),
                "process_instance_id": task.get(
                    "processInstanceId"
                )
            }
            for task in tasks
        ]
    })


@app.get("/applications")
def list_applications():
    try:
        processes = get_process_history()

    except requests.RequestException as exc:
        return jsonify({
            "error": "Could not connect to Camunda",
            "details": str(exc)
        }), 502

    applications = []

    for process in processes:

        app_id = process.get("businessKey")
        process_instance_id = process.get("id")
        state = process.get("state")

        variables = {}

        if process_instance_id:
            try:
                variables = get_process_variables(
                    process_instance_id
                )
            except requests.RequestException:
                variables = {}

        tasks = []

        if app_id:
            try:
                tasks = get_tasks(app_id)
            except requests.RequestException:
                tasks = []

        status = (
            "COMPLETED"
            if state == "COMPLETED"
            else "UNDER_REVIEW"
        )

        applications.append({
            "unified_app_id": app_id,
            "applicant_name": variables.get(
                "applicantName",
                "Unknown Applicant"
            ),
            "source_system": variables.get(
                "sourceSystem",
                "unknown"
            ),
            "request_type": variables.get(
                "requestType",
                "unknown"
            ),
            "status": status,
            "process_state": state,
            "process_instance_id": process_instance_id,
            "started_at": process.get("startTime"),
            "completed_at": process.get("endTime"),
            "tasks": [
                {
                    "id": task.get("id"),
                    "name": task.get("name"),
                    "created": task.get("created")
                }
                for task in tasks
            ]
        })

    return jsonify({
        "applications": applications
    })


@app.post("/applications/<app_id>/decision")
def make_decision(app_id):
    data = request.get_json(silent=True) or {}

    approved = data.get("approved")

    if not isinstance(approved, bool):
        return jsonify({
            "error": "approved must be true or false"
        }), 400

    try:
        tasks = get_tasks(app_id)

    except requests.RequestException as exc:
        return jsonify({
            "error": "Could not connect to Camunda",
            "details": str(exc)
        }), 502

    if not tasks:
        return jsonify({
            "error": "No open Officer Review task found",
            "unified_app_id": app_id
        }), 404

    task = tasks[0]
    task_id = task.get("id")

    if not task_id:
        return jsonify({
            "error": "Camunda task has no ID"
        }), 502

    try:
        response = requests.post(
            f"{CAMUNDA_REST_URL}/task/{task_id}/complete",
            json={
                "variables": {
                    "approved": {
                        "value": approved,
                        "type": "Boolean"
                    }
                }
            },
            timeout=10
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        details = exc

        if getattr(exc, "response", None) is not None:
            details = exc.response.text

        return jsonify({
            "error": "Could not complete Camunda task",
            "details": str(details)
        }), 502

    return jsonify({
        "message": "Officer decision recorded",
        "unified_app_id": app_id,
        "approved": approved,
        "task_id": task_id
    })
@app.get("/exceptions")
def list_exceptions():
    try:
        applications_response = requests.get(
            "http://localhost:5004/applications",
            timeout=10
        )

        applications_response.raise_for_status()
        applications = applications_response.json().get(
            "applications",
            []
        )

    except requests.RequestException as exc:
        return jsonify({
            "error": "Could not load applications",
            "details": str(exc)
        }), 502

    exceptions = detect_exceptions(applications)

    return jsonify({
        "exceptions": exceptions
    })


@app.post("/exceptions/<exception_id>/resolve")
def resolve_exception(exception_id):
    exceptions = load_exceptions()

    target = None

    for exception in exceptions:
        if exception.get("exception_id") == exception_id:
            target = exception
            break

    if target is None:
        return jsonify({
            "error": "Exception not found",
            "exception_id": exception_id
        }), 404

    if target.get("status") == "RESOLVED":
        return jsonify({
            "message": "Exception already resolved",
            "exception": target
        })

    target["status"] = "RESOLVED"
    target["resolved_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    save_exceptions(exceptions)

    return jsonify({
        "message": "Exception resolved",
        "exception": target
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5004,
        debug=True
    )