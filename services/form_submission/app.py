from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from confluent_kafka import Producer
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
import os
import sys
import uuid
import json
import requests
import re

# Add parent directory for middleware import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
CORS(app)

# ── CONFIG ─────────────────────────────────────
POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "ration_card_db"),
    "user": os.getenv("POSTGRES_USER", "omnilinkadmin"),
    "password": os.getenv("POSTGRES_PASSWORD", "omnilinkpass123"),
}

MONGO_URI = os.getenv(
    "MONGO_URI_FORMS",
    "mongodb://omnilinkadmin:omnilinkpass123@localhost:27017/?authSource=admin"
)

MONGO_DB = os.getenv("MONGO_DB_FORMS", "omnilink_forms")

SUBMISSIONS_COLLECTION = "submitted_applications"
AUDIT_COLLECTION = "application_audit"

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = "application.submitted"
KAFKA_SECURITY_PROTOCOL = os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
KAFKA_SASL_MECHANISMS = os.getenv("KAFKA_SASL_MECHANISMS", "PLAIN")
KAFKA_USERNAME = os.getenv("KAFKA_USERNAME", "")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD", "")
KAFKA_CA_CERT = os.getenv("KAFKA_CA_CERT", "")

if KAFKA_CA_CERT:
    KAFKA_CA_CERT = KAFKA_CA_CERT.replace("\\n", "\n")

AUDIT_SERVICE_URL = os.getenv("AUDIT_SERVICE_URL", "http://localhost:5005")
JWT_SECRET = os.getenv("JWT_SECRET", "omnilink-dev-secret-key-change-in-production")

FORM_COLLECTIONS = {
    "ration_card": "ration_card_forms",
    "scholarship": "scholarship_forms",
    "municipal_permit": "municipal_permit_forms",
    "voter_registration": "voter_registration_forms",
    "driving_license": "driving_license_forms",
    "pension": "pension_forms",
    "housing_assistance": "housing_assistance_forms",
    "health_scheme": "health_scheme_forms",
    "employment_skill": "employment_skill_forms",
    "social_welfare": "social_welfare_forms",
}

# ── DATA QUALITY RULES ─────────────────────────
QUALITY_RULES = {
    "mobile_number": {
        "pattern": r"^[6-9]\d{9}$",
        "message": "Must be 10 digits starting with 6-9",
    },
    "email": {
        "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "message": "Must be a valid email address",
    },
    "pan_number": {
        "pattern": r"^[A-Z]{5}[0-9]{4}[A-Z]$",
        "message": "Must match format ABCDE1234F",
    },
    "bank_ifsc": {
        "pattern": r"^[A-Z]{4}0[A-Z0-9]{6}$",
        "message": "Must match format ABCD0123456",
    },
    "bank_account": {
        "pattern": r"^\d{9,18}$",
        "message": "Must be 9-18 digits",
    },
}


# ── JWT AUTH HELPERS ───────────────────────────
def verify_jwt(token):
    """Verify JWT token."""
    import jwt as pyjwt
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise Exception("Token has expired")
    except pyjwt.InvalidTokenError:
        raise Exception("Invalid token")


def get_token_from_request():
    """Extract token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    return auth_header.replace("Bearer ", "")


def require_citizen(f):
    """Decorator: only citizens can access."""
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = get_token_from_request()
        if not token:
            return jsonify({"error": "Authentication required."}), 401
        try:
            payload = verify_jwt(token)
            if payload["role"] != "citizen":
                return jsonify({"error": "Citizen access required.", "your_role": payload["role"]}), 403
            request.user = payload
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": str(e)}), 401
    return wrapper


def require_officer(f):
    """Decorator: only officers/admins can access."""
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = get_token_from_request()
        if not token:
            return jsonify({"error": "Authentication required."}), 401
        try:
            payload = verify_jwt(token)
            if payload["role"] not in ("officer", "admin"):
                return jsonify({"error": "Officer access required.", "your_role": payload["role"]}), 403
            request.user = payload
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": str(e)}), 401
    return wrapper


# ── HELPERS ────────────────────────────────────
def get_mongo():
    client = MongoClient(MONGO_URI)
    return client, client[MONGO_DB]


def get_pg_connection():
    return psycopg2.connect(**POSTGRES_CONFIG)


def log_audit(
    actor_type, actor_id, action,
    citizen_id=None, target_form=None,
    fields_affected=None, purpose=None,
    correlation_id=None, status="success",
):
    """Send audit event to Audit Service."""
    try:
        payload = {
            "actor_type": actor_type,
            "actor_id": actor_id,
            "action": action,
            "citizen_id": citizen_id,
            "target_form": target_form,
            "fields_affected": fields_affected or {},
            "purpose": purpose,
            "correlation_id": correlation_id,
            "status": status,
        }
        response = requests.post(
            f"{AUDIT_SERVICE_URL}/audit/log",
            json=payload,
            timeout=3,
        )
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"[form-submission] Audit log failed: {e}", flush=True)
        return False


def validate_data_quality(form_data):
    """Check form data against quality rules."""
    issues = []

    for field, rule in QUALITY_RULES.items():
        if field in form_data and form_data[field]:
            value = str(form_data[field])
            if not re.match(rule["pattern"], value):
                issues.append({
                    "field": field,
                    "value": value,
                    "message": rule["message"],
                })

    return len(issues) == 0, issues


def create_kafka_producer():
    config = {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "message.timeout.ms": 10000,
        "request.timeout.ms": 10000,
        "socket.timeout.ms": 10000,
        "delivery.timeout.ms": 10000,
    }

    security_protocol = (KAFKA_SECURITY_PROTOCOL or "PLAINTEXT").strip().upper()

    if security_protocol != "PLAINTEXT":
        config["security.protocol"] = security_protocol
        if KAFKA_SASL_MECHANISMS:
            config["sasl.mechanisms"] = KAFKA_SASL_MECHANISMS.strip()
        if KAFKA_USERNAME:
            config["sasl.username"] = KAFKA_USERNAME
        if KAFKA_PASSWORD:
            config["sasl.password"] = KAFKA_PASSWORD
        if KAFKA_CA_CERT:
            config["ssl.ca.pem"] = KAFKA_CA_CERT

    print(
        f"[form-submission] Kafka: bootstrap={KAFKA_BOOTSTRAP_SERVERS}, "
        f"security={security_protocol}",
        flush=True,
    )

    return Producer(config)


def delivery_report(err, msg):
    if err is not None:
        print(f"[form-submission] Kafka delivery failed: {err}", flush=True)
    else:
        print(
            f"[form-submission] Kafka event delivered to "
            f"{msg.topic()} [{msg.partition()}] offset {msg.offset()}",
            flush=True,
        )


def verify_consent(citizen_id, consent_id, target_form):
    conn = get_pg_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT consent_id, citizen_id, target_form,
                       approved_fields, status, purpose,
                       expires_at, revoked_at
                FROM omnilink_core.consent_records
                WHERE consent_id = %s
                """,
                (consent_id,),
            )
            consent = cur.fetchone()

            if not consent:
                return False, {"error": "Consent record not found.", "consent_id": consent_id}

            consent = dict(consent)

            if consent["citizen_id"] != citizen_id:
                return False, {
                    "error": "Consent does not belong to this citizen.",
                    "citizen_id": citizen_id,
                    "consent_id": consent_id,
                }

            if consent["target_form"] != target_form:
                return False, {
                    "error": "Consent target form does not match submitted form.",
                    "target_form": target_form,
                    "consent_target_form": consent["target_form"],
                }

            if consent["status"] != "APPROVED":
                return False, {
                    "error": "Consent must be APPROVED before submission.",
                    "status": consent["status"],
                    "consent_id": consent_id,
                }

            if consent["revoked_at"] is not None:
                return False, {"error": "Consent has been revoked.", "consent_id": consent_id}

            if consent["expires_at"] is not None:
                now = datetime.now(timezone.utc)
                if consent["expires_at"] <= now:
                    return False, {"error": "Consent has expired.", "consent_id": consent_id}

            return True, consent
    finally:
        conn.close()


# ── HEALTH CHECK ───────────────────────────────
@app.get("/health")
def health():
    mongo_status = "connected"
    postgres_status = "connected"
    kafka_status = "configured"
    audit_status = "configured"

    mongo_client = None
    pg_conn = None
    producer = None

    try:
        mongo_client, db = get_mongo()
        db.command("ping")
    except Exception:
        mongo_status = "unavailable"
    finally:
        if mongo_client:
            mongo_client.close()

    try:
        pg_conn = get_pg_connection()
        with pg_conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception:
        postgres_status = "unavailable"
    finally:
        if pg_conn:
            pg_conn.close()

    try:
        producer = create_kafka_producer()
    except Exception:
        kafka_status = "unavailable"
    finally:
        if producer:
            producer.flush(2)

    try:
        response = requests.get(f"{AUDIT_SERVICE_URL}/health", timeout=3)
        if response.status_code != 200:
            audit_status = "unavailable"
    except Exception:
        audit_status = "unavailable"

    return jsonify({
        "status": "ok",
        "service": "form_submission",
        "port": 5009,
        "mongo": mongo_status,
        "postgres": postgres_status,
        "kafka": kafka_status,
        "audit": audit_status,
        "rbac": "enabled",
        "topic": KAFKA_TOPIC,
    })


# ── GET ALL SUBMISSIONS (OFFICER/ADMIN) ────────
@app.get("/submissions")
@require_officer
def get_submissions():
    client, db = get_mongo()
    try:
        documents = list(
            db[SUBMISSIONS_COLLECTION]
            .find({}, {"_id": 0})
            .sort("created_at", -1)
            .limit(100)
        )

        for document in documents:
            if hasattr(document.get("created_at"), "isoformat"):
                document["created_at"] = document["created_at"].isoformat()
            if hasattr(document.get("updated_at"), "isoformat"):
                document["updated_at"] = document["updated_at"].isoformat()

        return jsonify({
            "submissions": documents,
            "count": len(documents),
            "synthetic_data": True,
        })
    finally:
        client.close()


# ── GET SUBMISSION (OFFICER/ADMIN) ─────────────
@app.get("/submissions/<submission_id>")
@require_officer
def get_submission(submission_id):
    client, db = get_mongo()
    try:
        document = db[SUBMISSIONS_COLLECTION].find_one(
            {"submission_id": submission_id},
            {"_id": 0},
        )

        if not document:
            return jsonify({
                "error": "Submission not found.",
                "submission_id": submission_id,
            }), 404

        if hasattr(document.get("created_at"), "isoformat"):
            document["created_at"] = document["created_at"].isoformat()

        if hasattr(document.get("updated_at"), "isoformat"):
            document["updated_at"] = document["updated_at"].isoformat()

        return jsonify(document)
    finally:
        client.close()


# ── GET SUBMISSION AUDIT (OFFICER/ADMIN) ───────
@app.get("/submissions/<submission_id>/audit")
@require_officer
def get_audit(submission_id):
    client, db = get_mongo()
    try:
        documents = list(
            db[AUDIT_COLLECTION]
            .find({"submission_id": submission_id}, {"_id": 0})
            .sort("created_at", 1)
        )

        for document in documents:
            if hasattr(document.get("created_at"), "isoformat"):
                document["created_at"] = document["created_at"].isoformat()

        return jsonify({
            "submission_id": submission_id,
            "events": documents,
            "count": len(documents),
            "synthetic_data": True,
        })
    finally:
        client.close()


# ── CREATE SUBMISSION (CITIZEN ONLY) ───────────
@app.post("/submissions")
@require_citizen
def create_submission():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    citizen_id = data.get("citizen_id")
    target_form = data.get("target_form")
    consent_id = data.get("consent_id")
    form_data = data.get("form_data")

    # Validation
    if not citizen_id:
        return jsonify({"error": "citizen_id is required."}), 400

    if not target_form:
        return jsonify({"error": "target_form is required."}), 400

    if target_form not in FORM_COLLECTIONS:
        return jsonify({
            "error": "Unknown target_form.",
            "supported_forms": list(FORM_COLLECTIONS.keys()),
        }), 400

    if not consent_id:
        return jsonify({"error": "consent_id is required."}), 400

    if not isinstance(form_data, dict):
        return jsonify({"error": "form_data must be a JSON object."}), 400

    try:
        consent_id = int(consent_id)
    except (TypeError, ValueError):
        return jsonify({"error": "consent_id must be an integer."}), 400

    # Ensure JWT user matches citizen_id
    if request.user.get("user_id") != citizen_id:
        return jsonify({"error": "You can only submit for yourself."}), 403

    # Verify consent
    consent_ok, consent_result = verify_consent(citizen_id, consent_id, target_form)
    if not consent_ok:
        log_audit(
            actor_type="system",
            actor_id="form_submission",
            action="submission_blocked",
            citizen_id=citizen_id,
            target_form=target_form,
            fields_affected={"reason": consent_result.get("error")},
            correlation_id=str(consent_id),
            status="failure",
        )
        return jsonify(consent_result), 403

    # Data quality check
    is_valid, quality_issues = validate_data_quality(form_data)
    if not is_valid:
        log_audit(
            actor_type="system",
            actor_id="data_quality",
            action="quality_warning",
            citizen_id=citizen_id,
            target_form=target_form,
            fields_affected={"issues": quality_issues},
            correlation_id=str(consent_id),
            status="failure",
        )
        return jsonify({
            "error": "Data quality issues found.",
            "issues": quality_issues,
            "suggestion": "Correct the highlighted fields and resubmit.",
        }), 422

    # Create submission
    submission_id = f"SUB-{uuid.uuid4().hex[:12].upper()}"
    created_at = datetime.now(timezone.utc)

    applicant_name = " ".join(
        str(form_data.get(field))
        for field in ("student_first", "student_middle", "student_last")
        if form_data.get(field)
    ) or form_data.get("applicant_name") or form_data.get("beneficiary_name") or ""

    document = {
        "submission_id": submission_id,
        "citizen_id": citizen_id,
        "target_form": target_form,
        "consent_id": consent_id,
        "form_data": form_data,
        "status": "SUBMITTED",
        "created_at": created_at,
        "synthetic_data": True,
    }

    event = {
        "event_type": "application.submitted",
        "event_id": f"EVT-{uuid.uuid4().hex[:12].upper()}",
        "unified_app_id": submission_id,
        "submission_id": submission_id,
        "citizen_id": citizen_id,
        "source_system": target_form,
        "request_type": target_form,
        "consent_id": consent_id,
        "applicant_name": applicant_name,
        "submitted_at": created_at.isoformat(),
        "form_data": form_data,
        "synthetic_data": True,
    }

    client = None
    producer = None

    try:
        client, db = get_mongo()

        db[SUBMISSIONS_COLLECTION].insert_one(document)

        db[AUDIT_COLLECTION].insert_one({
            "audit_id": f"AUD-{uuid.uuid4().hex[:12].upper()}",
            "submission_id": submission_id,
            "citizen_id": citizen_id,
            "action": "APPLICATION_SUBMITTED",
            "previous_status": None,
            "new_status": "SUBMITTED",
            "details": {"target_form": target_form, "consent_id": consent_id},
            "created_at": created_at,
            "synthetic_data": True,
        })

        log_audit(
            actor_type="citizen",
            actor_id=citizen_id,
            action="submission_created",
            citizen_id=citizen_id,
            target_form=target_form,
            fields_affected={"form_data": form_data},
            purpose=f"{target_form} application",
            correlation_id=submission_id,
        )

        producer = create_kafka_producer()
        producer.produce(
            KAFKA_TOPIC,
            key=submission_id,
            value=json.dumps(event),
            callback=delivery_report,
        )

        remaining = producer.flush(10)
        if remaining > 0:
            raise RuntimeError("Kafka event was not delivered within the 10-second timeout.")

        response_document = dict(document)
        response_document.pop("_id", None)
        response_document["created_at"] = created_at.isoformat()

        return jsonify({
            **response_document,
            "event_type": event["event_type"],
            "kafka_topic": KAFKA_TOPIC,
            "kafka_published": True,
        }), 201

    except Exception as exc:
        print(f"[form-submission] submission failed {submission_id}: {exc}", flush=True)
        return jsonify({"error": str(exc), "submission_id": submission_id}), 500

    finally:
        if producer:
            producer.flush(2)
        if client:
            client.close()


# ── UPDATE SUBMISSION STATUS (OFFICER ONLY) ────
@app.post("/submissions/<submission_id>/status")
@require_officer
def update_submission_status(submission_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    new_status = data.get("status")
    details = data.get("details") or {}
    officer_id = data.get("officer_id", request.user.get("user_id", "officer"))

    allowed_statuses = {"SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED"}

    if new_status not in allowed_statuses:
        return jsonify({
            "error": "Invalid status.",
            "allowed_statuses": sorted(allowed_statuses),
        }), 400

    client, db = get_mongo()

    try:
        current = db[SUBMISSIONS_COLLECTION].find_one(
            {"submission_id": submission_id}
        )

        if not current:
            return jsonify({
                "error": "Submission not found.",
                "submission_id": submission_id,
            }), 404

        previous_status = current.get("status", "SUBMITTED")
        now = datetime.now(timezone.utc)

        db[SUBMISSIONS_COLLECTION].update_one(
            {"submission_id": submission_id},
            {"$set": {"status": new_status, "updated_at": now}},
        )

        db[AUDIT_COLLECTION].insert_one({
            "audit_id": f"AUD-{uuid.uuid4().hex[:12].upper()}",
            "submission_id": submission_id,
            "citizen_id": current.get("citizen_id"),
            "action": "STATUS_CHANGED",
            "previous_status": previous_status,
            "new_status": new_status,
            "details": details,
            "created_at": now,
            "synthetic_data": True,
        })

        log_audit(
            actor_type="officer",
            actor_id=str(officer_id),
            action="status_changed",
            citizen_id=current.get("citizen_id"),
            target_form=current.get("target_form"),
            fields_affected={"status": new_status, "previous_status": previous_status},
            correlation_id=submission_id,
        )

        updated = db[SUBMISSIONS_COLLECTION].find_one(
            {"submission_id": submission_id},
            {"_id": 0},
        )

        if hasattr(updated.get("created_at"), "isoformat"):
            updated["created_at"] = updated["created_at"].isoformat()

        if hasattr(updated.get("updated_at"), "isoformat"):
            updated["updated_at"] = updated["updated_at"].isoformat()

        return jsonify(updated)

    finally:
        client.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5009, debug=True)