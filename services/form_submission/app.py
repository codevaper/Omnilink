from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from confluent_kafka import Producer
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
import os
import uuid
import json

app = Flask(__name__)
CORS(app)

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

MONGO_DB = os.getenv(
    "MONGO_DB_FORMS",
    "omnilink_forms"
)

SUBMISSIONS_COLLECTION = "submitted_applications"
AUDIT_COLLECTION = "application_audit"

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092"
)

KAFKA_TOPIC = "application.submitted"


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


def get_mongo():
    client = MongoClient(MONGO_URI)
    return client, client[MONGO_DB]


def get_pg_connection():
    return psycopg2.connect(**POSTGRES_CONFIG)


def create_kafka_producer():
    return Producer({
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS
    })


def delivery_report(err, msg):
    if err is not None:
        print(
            f"[form-submission] Kafka delivery failed: {err}",
            flush=True,
        )
    else:
        print(
            f"[form-submission] Kafka event delivered to "
            f"{msg.topic()} [{msg.partition()}] "
            f"offset {msg.offset()}",
            flush=True,
        )


def verify_consent(citizen_id, consent_id, target_form):
    conn = get_pg_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    consent_id,
                    citizen_id,
                    target_form,
                    approved_fields,
                    status,
                    purpose,
                    expires_at,
                    revoked_at
                FROM omnilink_core.consent_records
                WHERE consent_id = %s
                """,
                (consent_id,),
            )

            consent = cur.fetchone()

            if not consent:
                return False, {
                    "error": "Consent record not found.",
                    "consent_id": consent_id,
                }

            consent = dict(consent)

            if consent["citizen_id"] != citizen_id:
                return False, {
                    "error": (
                        "Consent does not belong to "
                        "this citizen."
                    ),
                    "citizen_id": citizen_id,
                    "consent_id": consent_id,
                }

            if consent["target_form"] != target_form:
                return False, {
                    "error": (
                        "Consent target form does not "
                        "match submitted form."
                    ),
                    "target_form": target_form,
                    "consent_target_form": (
                        consent["target_form"]
                    ),
                }

            if consent["status"] != "APPROVED":
                return False, {
                    "error": (
                        "Consent must be APPROVED "
                        "before submission."
                    ),
                    "status": consent["status"],
                    "consent_id": consent_id,
                }

            if consent["revoked_at"] is not None:
                return False, {
                    "error": "Consent has been revoked.",
                    "consent_id": consent_id,
                }

            if consent["expires_at"] is not None:
                now = datetime.now(timezone.utc)

                if consent["expires_at"] <= now:
                    return False, {
                        "error": "Consent has expired.",
                        "consent_id": consent_id,
                    }

            return True, consent

    finally:
        conn.close()


def write_audit(
    submission_id,
    citizen_id,
    action,
    previous_status,
    new_status,
    details=None,
):
    client, db = get_mongo()

    try:
        db[AUDIT_COLLECTION].insert_one({
            "audit_id": (
                f"AUD-{uuid.uuid4().hex[:12].upper()}"
            ),
            "submission_id": submission_id,
            "citizen_id": citizen_id,
            "action": action,
            "previous_status": previous_status,
            "new_status": new_status,
            "details": details or {},
            "created_at": datetime.now(timezone.utc),
            "synthetic_data": True,
        })

    finally:
        client.close()


@app.get("/health")
def health():
    mongo_status = "connected"
    postgres_status = "connected"
    kafka_status = "configured"

    mongo_client = None
    pg_conn = None

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
        create_kafka_producer()
    except Exception:
        kafka_status = "unavailable"

    return jsonify({
        "status": "ok",
        "service": "form_submission",
        "port": 5009,
        "mongo": mongo_status,
        "postgres": postgres_status,
        "kafka": kafka_status,
        "topic": KAFKA_TOPIC,
    })


@app.get("/submissions")
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
            if hasattr(
                document.get("created_at"),
                "isoformat",
            ):
                document["created_at"] = (
                    document["created_at"].isoformat()
                )

        return jsonify({
            "submissions": documents,
            "count": len(documents),
            "synthetic_data": True,
        })

    finally:
        client.close()


@app.get("/submissions/<submission_id>")
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

        if hasattr(
            document.get("created_at"),
            "isoformat",
        ):
            document["created_at"] = (
                document["created_at"].isoformat()
            )

        return jsonify(document)

    finally:
        client.close()


@app.get("/submissions/<submission_id>/audit")
def get_audit(submission_id):
    client, db = get_mongo()

    try:
        documents = list(
            db[AUDIT_COLLECTION]
            .find(
                {"submission_id": submission_id},
                {"_id": 0},
            )
            .sort("created_at", 1)
        )

        for document in documents:
            if hasattr(
                document.get("created_at"),
                "isoformat",
            ):
                document["created_at"] = (
                    document["created_at"].isoformat()
                )

        return jsonify({
            "submission_id": submission_id,
            "events": documents,
            "count": len(documents),
            "synthetic_data": True,
        })

    finally:
        client.close()


@app.post("/submissions")
def create_submission():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must be a JSON object."
        }), 400

    citizen_id = data.get("citizen_id")
    target_form = data.get("target_form")
    consent_id = data.get("consent_id")
    form_data = data.get("form_data")

    if not citizen_id:
        return jsonify({
            "error": "citizen_id is required."
        }), 400

    if not target_form:
        return jsonify({
            "error": "target_form is required."
        }), 400

    if target_form not in FORM_COLLECTIONS:
        return jsonify({
            "error": "Unknown target_form.",
            "supported_forms": list(
                FORM_COLLECTIONS.keys()
            ),
        }), 400

    if not consent_id:
        return jsonify({
            "error": "consent_id is required."
        }), 400

    if not isinstance(form_data, dict):
        return jsonify({
            "error": "form_data must be a JSON object."
        }), 400

    try:
        consent_id = int(consent_id)
    except (TypeError, ValueError):
        return jsonify({
            "error": "consent_id must be an integer."
        }), 400

    consent_ok, consent_result = verify_consent(
        citizen_id,
        consent_id,
        target_form,
    )

    if not consent_ok:
        return jsonify(consent_result), 403

    submission_id = (
        f"SUB-{uuid.uuid4().hex[:12].upper()}"
    )

    created_at = datetime.now(timezone.utc)

    applicant_name = (
        " ".join(
            str(form_data.get(field))
            for field in (
                "student_first",
                "student_middle",
                "student_last",
            )
            if form_data.get(field)
        )
        or form_data.get("applicant_name")
        or form_data.get("beneficiary_name")
        or ""
    )

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
        "event_id": (
            f"EVT-{uuid.uuid4().hex[:12].upper()}"
        ),
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

        db[SUBMISSIONS_COLLECTION].insert_one(
            document
        )

        db[AUDIT_COLLECTION].insert_one({
            "audit_id": (
                f"AUD-{uuid.uuid4().hex[:12].upper()}"
            ),
            "submission_id": submission_id,
            "citizen_id": citizen_id,
            "action": "APPLICATION_SUBMITTED",
            "previous_status": None,
            "new_status": "SUBMITTED",
            "details": {
                "target_form": target_form,
                "consent_id": consent_id,
            },
            "created_at": created_at,
            "synthetic_data": True,
        })

        producer = create_kafka_producer()

        producer.produce(
            KAFKA_TOPIC,
            key=submission_id,
            value=json.dumps(event),
            callback=delivery_report,
        )

        producer.flush()

        response_document = dict(document)
        response_document.pop("_id", None)

        response_document["created_at"] = (
            created_at.isoformat()
        )

        return jsonify({
            **response_document,
            "event_type": event["event_type"],
            "kafka_topic": KAFKA_TOPIC,
            "kafka_published": True,
        }), 201

    except Exception as exc:
        return jsonify({
            "error": str(exc),
            "submission_id": submission_id,
        }), 500

    finally:
        if producer:
            producer.flush()

        if client:
            client.close()


@app.post("/submissions/<submission_id>/status")
def update_submission_status(submission_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must be a JSON object."
        }), 400

    new_status = data.get("status")
    details = data.get("details") or {}

    allowed_statuses = {
        "SUBMITTED",
        "UNDER_REVIEW",
        "APPROVED",
        "REJECTED",
    }

    if new_status not in allowed_statuses:
        return jsonify({
            "error": "Invalid status.",
            "allowed_statuses": sorted(
                allowed_statuses
            ),
        }), 400

    client, db = get_mongo()

    try:
        current = db[
            SUBMISSIONS_COLLECTION
        ].find_one(
            {"submission_id": submission_id}
        )

        if not current:
            return jsonify({
                "error": "Submission not found.",
                "submission_id": submission_id,
            }), 404

        previous_status = current.get(
            "status",
            "SUBMITTED",
        )

        now = datetime.now(timezone.utc)

        db[SUBMISSIONS_COLLECTION].update_one(
            {"submission_id": submission_id},
            {
                "$set": {
                    "status": new_status,
                    "updated_at": now,
                }
            },
        )

        db[AUDIT_COLLECTION].insert_one({
            "audit_id": (
                f"AUD-{uuid.uuid4().hex[:12].upper()}"
            ),
            "submission_id": submission_id,
            "citizen_id": current.get(
                "citizen_id"
            ),
            "action": "STATUS_CHANGED",
            "previous_status": previous_status,
            "new_status": new_status,
            "details": details,
            "created_at": now,
            "synthetic_data": True,
        })

        updated = db[
            SUBMISSIONS_COLLECTION
        ].find_one(
            {"submission_id": submission_id},
            {"_id": 0},
        )

        if hasattr(
            updated.get("created_at"),
            "isoformat",
        ):
            updated["created_at"] = (
                updated["created_at"].isoformat()
            )

        if hasattr(
            updated.get("updated_at"),
            "isoformat",
        ):
            updated["updated_at"] = (
                updated["updated_at"].isoformat()
            )

        return jsonify(updated)

    finally:
        client.close()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5009,
        debug=True,
    )