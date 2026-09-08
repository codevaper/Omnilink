from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sys
import requests
from datetime import datetime, timezone, timedelta

import psycopg2
from psycopg2.extras import RealDictCursor, Json

# Add parent directory for middleware import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
CORS(app)

# ── POSTGRES CONFIG ────────────────────────────
POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "ration_card_db"),
    "user": os.getenv("POSTGRES_USER", "omnilinkadmin"),
    "password": os.getenv("POSTGRES_PASSWORD", "omnilinkpass123"),
}

# ── AUDIT SERVICE CONFIG ───────────────────────
AUDIT_SERVICE_URL = os.getenv(
    "AUDIT_SERVICE_URL",
    "http://localhost:5005"
)

# ── JWT CONFIG ─────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", "omnilink-dev-secret-key-change-in-production")

# ── FIELD LABELS ───────────────────────────────
FIELD_LABELS = {
    "first_name": "First Name",
    "middle_name": "Middle Name",
    "last_name": "Last Name",
    "date_of_birth": "Date of Birth",
    "father_name": "Father / Guardian Name",
    "gender": "Gender",
    "marital_status": "Marital Status",
    "category": "Category",
    "mobile_number": "Mobile Number",
    "alternate_mobile_number": "Alternate Mobile Number",
    "email": "Email Address",
    "address": "Current Address",
    "aadhaar_number": "Synthetic Aadhaar Reference",
    "pan_number": "Synthetic PAN Reference",
    "voter_id": "Synthetic Voter Reference",
    "driving_license_number": "Synthetic Driving License Reference",
    "passport_number": "Synthetic Passport Reference",
    "ration_card_number": "Synthetic Ration Card Reference",
    "annual_income": "Annual Income",
    "family_size": "Family Size",
    "bank_name": "Bank Name",
    "bank_account": "Bank Account Reference",
    "bank_ifsc": "Bank IFSC Reference",
    "branch_name": "Bank Branch",
    "education_level": "Education Level",
    "occupation": "Occupation",
    "employer_name": "Employer Name",
    "years_of_experience": "Years of Experience",
    "skills": "Skills",
}

SENSITIVE_FIELDS = {
    "aadhaar_number",
    "pan_number",
    "voter_id",
    "driving_license_number",
    "passport_number",
    "ration_card_number",
    "annual_income",
    "bank_account",
    "bank_ifsc",
}

FORM_LABELS = {
    "ration_card": "Ration Card",
    "scholarship": "Scholarship",
    "municipal_permit": "Municipal Permit",
    "voter_registration": "Voter Registration",
    "driving_license": "Driving License",
    "pension": "Pension",
    "housing_assistance": "Housing Assistance",
    "health_scheme": "Health Scheme",
    "employment_skill": "Employment Skill",
    "social_welfare": "Social Welfare",
}

FORM_VISIBLE_FIELDS = {
    "ration_card": [
        "first_name", "middle_name", "last_name", "father_name",
        "mobile_number", "address", "annual_income", "category",
        "ration_card_number", "family_size", "bank_account", "bank_ifsc",
    ],
    "scholarship": [
        "first_name", "middle_name", "last_name", "date_of_birth",
        "father_name", "gender", "mobile_number", "email", "address",
        "pan_number", "annual_income", "category", "bank_account",
        "bank_ifsc", "education_level",
    ],
    "municipal_permit": [
        "first_name", "middle_name", "last_name", "mobile_number",
        "email", "address", "pan_number",
    ],
    "voter_registration": [
        "first_name", "middle_name", "last_name", "date_of_birth",
        "gender", "mobile_number", "address", "voter_id",
    ],
    "driving_license": [
        "first_name", "middle_name", "last_name", "date_of_birth",
        "gender", "mobile_number", "email", "address",
        "driving_license_number",
    ],
    "pension": [
        "first_name", "middle_name", "last_name", "date_of_birth",
        "mobile_number", "address", "category", "bank_account", "bank_ifsc",
    ],
    "housing_assistance": [
        "first_name", "middle_name", "last_name", "father_name",
        "mobile_number", "address", "annual_income", "category", "family_size",
    ],
    "health_scheme": [
        "first_name", "middle_name", "last_name", "date_of_birth",
        "gender", "mobile_number", "address", "category",
    ],
    "employment_skill": [
        "first_name", "middle_name", "last_name", "date_of_birth",
        "mobile_number", "email", "address", "education_level",
        "occupation", "employer_name", "years_of_experience", "skills",
    ],
    "social_welfare": [
        "first_name", "middle_name", "last_name", "father_name",
        "mobile_number", "address", "annual_income", "category", "family_size",
    ],
}

FORM_REQUIRED_FIELDS = {
    "ration_card": [
        "first_name", "last_name", "mobile_number",
        "address", "category", "family_size",
    ],
    "scholarship": [
        "first_name", "middle_name", "last_name", "date_of_birth",
        "gender", "mobile_number", "email", "address", "pan_number",
        "annual_income", "category", "bank_account", "bank_ifsc",
    ],
    "municipal_permit": [
        "first_name", "last_name", "mobile_number", "email", "address",
    ],
    "voter_registration": [
        "first_name", "last_name", "date_of_birth",
        "gender", "mobile_number", "address",
    ],
    "driving_license": [
        "first_name", "last_name", "date_of_birth",
        "gender", "mobile_number", "address", "driving_license_number",
    ],
    "pension": [
        "first_name", "last_name", "date_of_birth",
        "mobile_number", "address", "bank_account", "bank_ifsc",
    ],
    "housing_assistance": [
        "first_name", "last_name", "mobile_number",
        "address", "annual_income", "category", "family_size",
    ],
    "health_scheme": [
        "first_name", "last_name", "date_of_birth",
        "gender", "mobile_number", "address", "category",
    ],
    "employment_skill": [
        "first_name", "last_name", "mobile_number",
        "email", "education_level", "occupation",
        "years_of_experience", "skills",
    ],
    "social_welfare": [
        "first_name", "last_name", "mobile_number",
        "address", "annual_income", "category",
    ],
}


# ── JWT AUTH HELPERS ───────────────────────────
def verify_jwt(token):
    """Verify JWT token. Returns payload or raises Exception."""
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


# ── AUDIT LOGGING ──────────────────────────────
def log_audit(
    actor_type,
    actor_id,
    action,
    citizen_id=None,
    target_form=None,
    fields_affected=None,
    purpose=None,
    correlation_id=None,
    status="success",
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
        print(f"[consent-service] Audit log failed: {e}", flush=True)
        return False


# ── DATABASE HELPERS ───────────────────────────
def get_connection():
    return psycopg2.connect(**POSTGRES_CONFIG)


def row_to_dict(row):
    if not row:
        return None

    result = dict(row)

    for key in ("created_at", "expires_at", "revoked_at"):
        if result.get(key) is not None:
            result[key] = result[key].isoformat()

    return result


def validate_citizen(citizen_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT citizen_id
                FROM omnilink_core.citizens
                WHERE citizen_id = %s
                """,
                (citizen_id,),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def validate_form(target_form):
    return target_form in FORM_VISIBLE_FIELDS


def get_citizen_quality(citizen_id):
    """Fetch quality score from database."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT quality_score, quality_category,
                       missing_fields, invalid_fields
                FROM citizen_quality_scores
                WHERE citizen_id = %s
                """,
                (citizen_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception:
        return None
    finally:
        conn.close()


# ── HEALTH CHECK ───────────────────────────────
@app.get("/health")
def health():
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        finally:
            conn.close()

        return jsonify({
            "status": "ok",
            "service": "consent_service",
            "port": 5007,
            "database": "connected",
            "audit_service": AUDIT_SERVICE_URL,
            "rbac": "enabled",
        })
    except Exception as exc:
        return jsonify({
            "status": "error",
            "service": "consent_service",
            "port": 5007,
            "database": "unavailable",
            "error": str(exc),
        }), 500


# ── GET FORMS (PUBLIC) ─────────────────────────
@app.get("/consent/forms")
def get_form_requirements():
    forms = []

    for form_key in FORM_VISIBLE_FIELDS:
        visible_fields = FORM_VISIBLE_FIELDS[form_key]
        required_fields = FORM_REQUIRED_FIELDS.get(form_key, [])

        forms.append({
            "form_key": form_key,
            "label": FORM_LABELS.get(form_key, form_key),
            "visible_fields": visible_fields,
            "required_fields": required_fields,
            "read_only_fields": [
                field for field in visible_fields
                if field not in required_fields
            ],
            "field_count": len(visible_fields),
            "required_count": len(required_fields),
        })

    return jsonify({
        "forms": forms,
        "count": len(forms),
        "data_minimization": True,
    })


# ── GET FIELDS (PUBLIC) ────────────────────────
@app.get("/consent/fields/<citizen_id>")
def get_available_fields(citizen_id):
    target_form = request.args.get("target_form")

    if not validate_citizen(citizen_id):
        return jsonify({
            "error": "Citizen not found.",
            "citizen_id": citizen_id,
        }), 404

    quality = get_citizen_quality(citizen_id)

    if not target_form:
        fields = []

        for field_name, label in FIELD_LABELS.items():
            fields.append({
                "name": field_name,
                "label": label,
                "sensitive": field_name in SENSITIVE_FIELDS,
                "required_for_form": False,
                "read_only": True,
            })

        return jsonify({
            "citizen_id": citizen_id,
            "fields": fields,
            "count": len(fields),
            "form_specific": False,
            "quality": quality,
            "synthetic_data": True,
        })

    if not validate_form(target_form):
        return jsonify({
            "error": "Unknown target form.",
            "target_form": target_form,
            "supported_forms": list(FORM_VISIBLE_FIELDS.keys()),
        }), 400

    visible_fields = FORM_VISIBLE_FIELDS[target_form]
    required_fields = set(FORM_REQUIRED_FIELDS[target_form])

    fields = []

    for field_name in visible_fields:
        is_required = field_name in required_fields

        fields.append({
            "name": field_name,
            "label": FIELD_LABELS[field_name],
            "sensitive": field_name in SENSITIVE_FIELDS,
            "required_for_form": is_required,
            "read_only": not is_required,
            "selectable": is_required,
        })

    return jsonify({
        "citizen_id": citizen_id,
        "target_form": target_form,
        "target_form_label": FORM_LABELS.get(target_form, target_form),
        "fields": fields,
        "count": len(fields),
        "required_count": len(required_fields),
        "form_specific": True,
        "data_minimization": True,
        "quality": quality,
        "message": (
            "Required fields are selectable. "
            "Non-required fields are visible but read-only."
        ),
        "synthetic_data": True,
    })


# ── CREATE CONSENT REQUEST (CITIZEN ONLY) ──────
@app.post("/consent/request")
@require_citizen
def create_consent():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must be a JSON object."
        }), 400

    citizen_id = data.get("citizen_id")
    target_form = data.get("target_form")
    requested_fields = data.get("requested_fields")
    purpose = data.get("purpose")
    expires_at = data.get("expires_at")

    # Validation
    if not citizen_id:
        return jsonify({"error": "citizen_id is required."}), 400

    if not target_form:
        return jsonify({"error": "target_form is required."}), 400

    if not validate_form(target_form):
        return jsonify({
            "error": "Unknown target form.",
            "target_form": target_form,
        }), 400

    if not isinstance(requested_fields, list):
        return jsonify({
            "error": "requested_fields must be an array."
        }), 400

    if not requested_fields:
        return jsonify({
            "error": "At least one requested field is required."
        }), 400

    if not purpose:
        return jsonify({"error": "purpose is required."}), 400

    if not validate_citizen(citizen_id):
        return jsonify({
            "error": "Citizen not found.",
            "citizen_id": citizen_id,
        }), 404

    # Ensure JWT user matches citizen_id
    if request.user.get("user_id") != citizen_id:
        return jsonify({
            "error": "You can only create consent for yourself."
        }), 403

    required_fields = set(FORM_REQUIRED_FIELDS[target_form])

    invalid_fields = [
        field for field in requested_fields
        if field not in required_fields
    ]

    if invalid_fields:
        return jsonify({
            "error": "Only fields required by this department form can be approved.",
            "target_form": target_form,
            "invalid_fields": invalid_fields,
            "required_fields": FORM_REQUIRED_FIELDS[target_form],
        }), 403

    # Set default expiry if not provided
    if not expires_at:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    conn = get_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO omnilink_core.consent_records (
                    citizen_id, target_form, requested_fields,
                    approved_fields, status, purpose, expires_at
                )
                VALUES (%s, %s, %s, %s, 'PENDING', %s, %s)
                RETURNING
                    consent_id, citizen_id, target_form,
                    requested_fields, approved_fields, status,
                    purpose, created_at, expires_at, revoked_at
                """,
                (
                    citizen_id,
                    target_form,
                    Json(requested_fields),
                    Json([]),
                    purpose,
                    expires_at,
                ),
            )

            row = cur.fetchone()
            conn.commit()

            consent_id = row["consent_id"]

            # Audit log
            log_audit(
                actor_type="citizen",
                actor_id=citizen_id,
                action="consent_requested",
                citizen_id=citizen_id,
                target_form=target_form,
                fields_affected={"requested_fields": requested_fields},
                purpose=purpose,
                correlation_id=str(consent_id),
            )

            return jsonify({
                **row_to_dict(row),
                "target_form_label": FORM_LABELS.get(target_form, target_form),
                "required_fields": FORM_REQUIRED_FIELDS[target_form],
                "data_minimization": True,
                "synthetic_data": True,
            }), 201

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── APPROVE CONSENT (CITIZEN ONLY) ─────────────
@app.post("/consent/<int:consent_id>/approve")
@require_citizen
def approve_consent(consent_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must be a JSON object."
        }), 400

    approved_fields = data.get("approved_fields")

    if not isinstance(approved_fields, list):
        return jsonify({
            "error": "approved_fields must be an array."
        }), 400

    if not approved_fields:
        return jsonify({
            "error": "At least one approved field is required."
        }), 400

    conn = get_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT consent_id, citizen_id, target_form,
                       requested_fields, approved_fields, status,
                       purpose, created_at, expires_at, revoked_at
                FROM omnilink_core.consent_records
                WHERE consent_id = %s
                """,
                (consent_id,),
            )

            existing = cur.fetchone()

            if not existing:
                return jsonify({
                    "error": "Consent record not found.",
                    "consent_id": consent_id,
                }), 404

            # Ensure JWT user matches consent owner
            if request.user.get("user_id") != existing["citizen_id"]:
                return jsonify({
                    "error": "You can only approve your own consent."
                }), 403

            target_form = existing["target_form"]
            citizen_id = existing["citizen_id"]
            required_fields = set(FORM_REQUIRED_FIELDS[target_form])
            requested_fields = existing["requested_fields"] or []

            unauthorized = [
                field for field in approved_fields
                if field not in requested_fields
            ]

            if unauthorized:
                return jsonify({
                    "error": "Approved fields must be a subset of requested fields.",
                    "unauthorized_fields": unauthorized,
                    "requested_fields": requested_fields,
                }), 400

            invalid_required = [
                field for field in approved_fields
                if field not in required_fields
            ]

            if invalid_required:
                return jsonify({
                    "error": "A field not required by this form was supplied.",
                    "invalid_fields": invalid_required,
                    "required_fields": FORM_REQUIRED_FIELDS[target_form],
                }), 403

            if existing["status"] == "REVOKED":
                return jsonify({
                    "error": "Cannot approve revoked consent.",
                    "consent_id": consent_id,
                }), 409

            cur.execute(
                """
                UPDATE omnilink_core.consent_records
                SET approved_fields = %s, status = 'APPROVED'
                WHERE consent_id = %s
                RETURNING
                    consent_id, citizen_id, target_form,
                    requested_fields, approved_fields, status,
                    purpose, created_at, expires_at, revoked_at
                """,
                (Json(approved_fields), consent_id),
            )

            row = cur.fetchone()
            conn.commit()

            # Audit log
            log_audit(
                actor_type="citizen",
                actor_id=citizen_id,
                action="consent_approved",
                citizen_id=citizen_id,
                target_form=target_form,
                fields_affected={"approved_fields": approved_fields},
                purpose=existing["purpose"],
                correlation_id=str(consent_id),
            )

            return jsonify({
                **row_to_dict(row),
                "target_form_label": FORM_LABELS.get(target_form, target_form),
                "required_fields": FORM_REQUIRED_FIELDS[target_form],
                "data_minimization": True,
                "synthetic_data": True,
            })

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── REVOKE CONSENT (CITIZEN ONLY) ──────────────
@app.post("/consent/<int:consent_id>/revoke")
@require_citizen
def revoke_consent(consent_id):
    conn = get_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get consent before revoking for audit
            cur.execute(
                """
                SELECT citizen_id, target_form, purpose
                FROM omnilink_core.consent_records
                WHERE consent_id = %s
                """,
                (consent_id,),
            )
            existing = cur.fetchone()

            if existing and request.user.get("user_id") != existing["citizen_id"]:
                return jsonify({
                    "error": "You can only revoke your own consent."
                }), 403

            cur.execute(
                """
                UPDATE omnilink_core.consent_records
                SET status = 'REVOKED', revoked_at = NOW()
                WHERE consent_id = %s
                RETURNING
                    consent_id, citizen_id, target_form,
                    requested_fields, approved_fields, status,
                    purpose, created_at, expires_at, revoked_at
                """,
                (consent_id,),
            )

            row = cur.fetchone()

            if not row:
                conn.rollback()
                return jsonify({
                    "error": "Consent record not found.",
                    "consent_id": consent_id,
                }), 404

            conn.commit()

            # Audit log
            if existing:
                log_audit(
                    actor_type="citizen",
                    actor_id=row["citizen_id"],
                    action="consent_revoked",
                    citizen_id=row["citizen_id"],
                    target_form=row["target_form"],
                    fields_affected={"all_fields": "revoked"},
                    purpose=existing["purpose"],
                    correlation_id=str(consent_id),
                )

            return jsonify({
                **row_to_dict(row),
                "message": "Consent revoked",
                "data_minimization": True,
                "synthetic_data": True,
            })

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── GET CONSENT (PUBLIC) ───────────────────────
@app.get("/consent/<int:consent_id>")
def get_consent(consent_id):
    conn = get_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT consent_id, citizen_id, target_form,
                       requested_fields, approved_fields, status,
                       purpose, created_at, expires_at, revoked_at
                FROM omnilink_core.consent_records
                WHERE consent_id = %s
                """,
                (consent_id,),
            )

            row = cur.fetchone()

            if not row:
                return jsonify({
                    "error": "Consent record not found.",
                    "consent_id": consent_id,
                }), 404

            target_form = row["target_form"]

            return jsonify({
                **row_to_dict(row),
                "required_fields": FORM_REQUIRED_FIELDS.get(target_form, []),
                "visible_fields": FORM_VISIBLE_FIELDS.get(target_form, []),
                "data_minimization": True,
                "synthetic_data": True,
            })

    finally:
        conn.close()


# ── GET CITIZEN CONSENTS (PUBLIC) ──────────────
@app.get("/consent/citizen/<citizen_id>")
def get_citizen_consents(citizen_id):
    if not validate_citizen(citizen_id):
        return jsonify({
            "error": "Citizen not found.",
            "citizen_id": citizen_id,
        }), 404

    conn = get_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT consent_id, citizen_id, target_form,
                       requested_fields, approved_fields, status,
                       purpose, created_at, expires_at, revoked_at
                FROM omnilink_core.consent_records
                WHERE citizen_id = %s
                ORDER BY consent_id DESC
                """,
                (citizen_id,),
            )

            rows = cur.fetchall()

            return jsonify({
                "citizen_id": citizen_id,
                "consents": [row_to_dict(row) for row in rows],
                "count": len(rows),
                "data_minimization": True,
                "synthetic_data": True,
            })

    finally:
        conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5007, debug=True)