from flask import Flask, jsonify, request
from flask_cors import CORS
import os

import psycopg2
from psycopg2.extras import RealDictCursor, Json


app = Flask(__name__)
CORS(app)


POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "ration_card_db"),
    "user": os.getenv("POSTGRES_USER", "omnilinkadmin"),
    "password": os.getenv("POSTGRES_PASSWORD", "omnilinkpass123"),
}


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


# Fields that are relevant to each form and may be shown
# on the citizen consent screen.
FORM_VISIBLE_FIELDS = {

    "ration_card": [
        "first_name",
        "middle_name",
        "last_name",
        "father_name",
        "mobile_number",
        "address",
        "annual_income",
        "category",
        "ration_card_number",
        "family_size",
        "bank_account",
        "bank_ifsc",
    ],

    "scholarship": [
        "first_name",
        "middle_name",
        "last_name",
        "date_of_birth",
        "father_name",
        "gender",
        "mobile_number",
        "email",
        "address",
        "pan_number",
        "annual_income",
        "category",
        "bank_account",
        "bank_ifsc",
        "education_level",
    ],

    "municipal_permit": [
        "first_name",
        "middle_name",
        "last_name",
        "mobile_number",
        "email",
        "address",
        "pan_number",
    ],

    "voter_registration": [
        "first_name",
        "middle_name",
        "last_name",
        "date_of_birth",
        "gender",
        "mobile_number",
        "address",
        "voter_id",
    ],

    "driving_license": [
        "first_name",
        "middle_name",
        "last_name",
        "date_of_birth",
        "gender",
        "mobile_number",
        "email",
        "address",
        "driving_license_number",
    ],

    "pension": [
        "first_name",
        "middle_name",
        "last_name",
        "date_of_birth",
        "mobile_number",
        "address",
        "category",
        "bank_account",
        "bank_ifsc",
    ],

    "housing_assistance": [
        "first_name",
        "middle_name",
        "last_name",
        "father_name",
        "mobile_number",
        "address",
        "annual_income",
        "category",
        "family_size",
    ],

    "health_scheme": [
        "first_name",
        "middle_name",
        "last_name",
        "date_of_birth",
        "gender",
        "mobile_number",
        "address",
        "category",
    ],

    "employment_skill": [
        "first_name",
        "middle_name",
        "last_name",
        "date_of_birth",
        "mobile_number",
        "email",
        "address",
        "education_level",
        "occupation",
        "employer_name",
        "years_of_experience",
        "skills",
    ],

    "social_welfare": [
        "first_name",
        "middle_name",
        "last_name",
        "father_name",
        "mobile_number",
        "address",
        "annual_income",
        "category",
        "family_size",
    ],
}


# Fields the department form actually requires.
#
# Required fields are selectable by the citizen.
# Everything visible but not in this list is read-only.
FORM_REQUIRED_FIELDS = {

    "ration_card": [
        "first_name",
        "last_name",
        "mobile_number",
        "address",
        "category",
        "family_size",
    ],

    "scholarship": [
        "first_name",
        "middle_name",
        "last_name",
        "date_of_birth",
        "gender",
        "mobile_number",
        "email",
        "address",
        "pan_number",
        "annual_income",
        "category",
        "bank_account",
        "bank_ifsc",
    ],

    "municipal_permit": [
        "first_name",
        "last_name",
        "mobile_number",
        "email",
        "address",
    ],

    "voter_registration": [
        "first_name",
        "last_name",
        "date_of_birth",
        "gender",
        "mobile_number",
        "address",
    ],

    "driving_license": [
        "first_name",
        "last_name",
        "date_of_birth",
        "gender",
        "mobile_number",
        "address",
        "driving_license_number",
    ],

    "pension": [
        "first_name",
        "last_name",
        "date_of_birth",
        "mobile_number",
        "address",
        "bank_account",
        "bank_ifsc",
    ],

    "housing_assistance": [
        "first_name",
        "last_name",
        "mobile_number",
        "address",
        "annual_income",
        "category",
        "family_size",
    ],

    "health_scheme": [
        "first_name",
        "last_name",
        "date_of_birth",
        "gender",
        "mobile_number",
        "address",
        "category",
    ],

    "employment_skill": [
        "first_name",
        "last_name",
        "mobile_number",
        "email",
        "education_level",
        "occupation",
        "years_of_experience",
        "skills",
    ],

    "social_welfare": [
        "first_name",
        "last_name",
        "mobile_number",
        "address",
        "annual_income",
        "category",
    ],
}


def get_connection():
    return psycopg2.connect(**POSTGRES_CONFIG)


def row_to_dict(row):
    if not row:
        return None

    result = dict(row)

    for key in (
        "created_at",
        "expires_at",
        "revoked_at",
    ):
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
                (citizen_id,)
            )

            return cur.fetchone() is not None

    finally:

        conn.close()


def validate_form(target_form):
    return target_form in FORM_VISIBLE_FIELDS


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
        })

    except Exception as exc:

        return jsonify({
            "status": "error",
            "service": "consent_service",
            "port": 5007,
            "database": "unavailable",
            "error": str(exc),
        }), 500


@app.get("/consent/forms")
def get_form_requirements():

    forms = []

    for form_key in FORM_VISIBLE_FIELDS:

        visible_fields = FORM_VISIBLE_FIELDS[form_key]

        required_fields = FORM_REQUIRED_FIELDS.get(
            form_key,
            []
        )

        forms.append({
            "form_key": form_key,
            "label": FORM_LABELS.get(
                form_key,
                form_key
            ),
            "visible_fields": visible_fields,
            "required_fields": required_fields,
            "read_only_fields": [
                field
                for field in visible_fields
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


@app.get("/consent/fields/<citizen_id>")
def get_available_fields(citizen_id):

    target_form = request.args.get(
        "target_form"
    )

    if not validate_citizen(citizen_id):

        return jsonify({
            "error": "Citizen not found.",
            "citizen_id": citizen_id,
        }), 404

    if not target_form:

        fields = []

        for field_name, label in FIELD_LABELS.items():

            fields.append({
                "name": field_name,
                "label": label,
                "sensitive": (
                    field_name in SENSITIVE_FIELDS
                ),
                "required_for_form": False,
                "read_only": True,
            })

        return jsonify({
            "citizen_id": citizen_id,
            "fields": fields,
            "count": len(fields),
            "form_specific": False,
            "synthetic_data": True,
        })

    if not validate_form(target_form):

        return jsonify({
            "error": "Unknown target form.",
            "target_form": target_form,
            "supported_forms": list(
                FORM_VISIBLE_FIELDS.keys()
            ),
        }), 400

    visible_fields = FORM_VISIBLE_FIELDS[
        target_form
    ]

    required_fields = set(
        FORM_REQUIRED_FIELDS[
            target_form
        ]
    )

    fields = []

    for field_name in visible_fields:

        is_required = (
            field_name in required_fields
        )

        fields.append({
            "name": field_name,
            "label": FIELD_LABELS[field_name],
            "sensitive": (
                field_name in SENSITIVE_FIELDS
            ),
            "required_for_form": is_required,
            "read_only": not is_required,
            "selectable": is_required,
        })

    return jsonify({
        "citizen_id": citizen_id,
        "target_form": target_form,
        "target_form_label": FORM_LABELS.get(
            target_form,
            target_form
        ),
        "fields": fields,
        "count": len(fields),
        "required_count": len(required_fields),
        "form_specific": True,
        "data_minimization": True,
        "message": (
            "Required fields are selectable. "
            "Non-required fields are visible "
            "but read-only."
        ),
        "synthetic_data": True,
    })


@app.post("/consent/request")
def create_consent():

    data = request.get_json(
        silent=True
    )

    if not isinstance(data, dict):

        return jsonify({
            "error":
                "Request body must be a JSON object."
        }), 400

    citizen_id = data.get(
        "citizen_id"
    )

    target_form = data.get(
        "target_form"
    )

    requested_fields = data.get(
        "requested_fields"
    )

    purpose = data.get(
        "purpose"
    )

    expires_at = data.get(
        "expires_at"
    )

    if not citizen_id:

        return jsonify({
            "error":
                "citizen_id is required."
        }), 400

    if not target_form:

        return jsonify({
            "error":
                "target_form is required."
        }), 400

    if not validate_form(target_form):

        return jsonify({
            "error":
                "Unknown target form.",
            "target_form":
                target_form,
        }), 400

    if not isinstance(
        requested_fields,
        list
    ):

        return jsonify({
            "error":
                "requested_fields must be an array."
        }), 400

    if not requested_fields:

        return jsonify({
            "error":
                "At least one requested field is required."
        }), 400

    if not purpose:

        return jsonify({
            "error":
                "purpose is required."
        }), 400

    required_fields = set(
        FORM_REQUIRED_FIELDS[target_form]
    )

    invalid_fields = [
        field
        for field in requested_fields
        if field not in required_fields
    ]

    if invalid_fields:

        return jsonify({
            "error": (
                "Only fields required by this "
                "department form can be approved."
            ),
            "target_form":
                target_form,
            "invalid_fields":
                invalid_fields,
            "required_fields":
                FORM_REQUIRED_FIELDS[target_form],
        }), 403

    if not validate_citizen(citizen_id):

        return jsonify({
            "error":
                "Citizen not found.",
            "citizen_id":
                citizen_id,
        }), 404

    conn = get_connection()

    try:

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                INSERT INTO omnilink_core.consent_records (
                    citizen_id,
                    target_form,
                    requested_fields,
                    approved_fields,
                    status,
                    purpose,
                    expires_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    'PENDING',
                    %s,
                    %s
                )
                RETURNING
                    consent_id,
                    citizen_id,
                    target_form,
                    requested_fields,
                    approved_fields,
                    status,
                    purpose,
                    created_at,
                    expires_at,
                    revoked_at
                """,
                (
                    citizen_id,
                    target_form,
                    Json(requested_fields),
                    Json([]),
                    purpose,
                    expires_at,
                )
            )

            row = cur.fetchone()

            conn.commit()

            return jsonify({
                **row_to_dict(row),
                "target_form_label":
                    FORM_LABELS.get(
                        target_form,
                        target_form
                    ),
                "required_fields":
                    FORM_REQUIRED_FIELDS[target_form],
                "data_minimization": True,
                "synthetic_data": True,
            }), 201

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()


@app.post("/consent/<int:consent_id>/approve")
def approve_consent(consent_id):

    data = request.get_json(
        silent=True
    )

    if not isinstance(data, dict):

        return jsonify({
            "error":
                "Request body must be a JSON object."
        }), 400

    approved_fields = data.get(
        "approved_fields"
    )

    if not isinstance(
        approved_fields,
        list
    ):

        return jsonify({
            "error":
                "approved_fields must be an array."
        }), 400

    if not approved_fields:

        return jsonify({
            "error":
                "At least one approved field is required."
        }), 400

    conn = get_connection()

    try:

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT
                    consent_id,
                    citizen_id,
                    target_form,
                    requested_fields,
                    approved_fields,
                    status,
                    purpose,
                    created_at,
                    expires_at,
                    revoked_at
                FROM omnilink_core.consent_records
                WHERE consent_id = %s
                """,
                (consent_id,)
            )

            existing = cur.fetchone()

            if not existing:

                return jsonify({
                    "error":
                        "Consent record not found.",
                    "consent_id":
                        consent_id,
                }), 404

            target_form = existing[
                "target_form"
            ]

            required_fields = set(
                FORM_REQUIRED_FIELDS[target_form]
            )

            requested_fields = (
                existing["requested_fields"]
                or []
            )

            unauthorized = [
                field
                for field in approved_fields
                if field not in requested_fields
            ]

            if unauthorized:

                return jsonify({
                    "error": (
                        "Approved fields must be "
                        "a subset of requested fields."
                    ),
                    "unauthorized_fields":
                        unauthorized,
                    "requested_fields":
                        requested_fields,
                }), 400

            invalid_required = [
                field
                for field in approved_fields
                if field not in required_fields
            ]

            if invalid_required:

                return jsonify({
                    "error": (
                        "A field not required by "
                        "this form was supplied."
                    ),
                    "invalid_fields":
                        invalid_required,
                    "required_fields":
                        FORM_REQUIRED_FIELDS[target_form],
                }), 403

            if existing["status"] == "REVOKED":

                return jsonify({
                    "error":
                        "Cannot approve revoked consent.",
                    "consent_id":
                        consent_id,
                }), 409

            cur.execute(
                """
                UPDATE omnilink_core.consent_records
                SET
                    approved_fields = %s,
                    status = 'APPROVED'
                WHERE consent_id = %s
                RETURNING
                    consent_id,
                    citizen_id,
                    target_form,
                    requested_fields,
                    approved_fields,
                    status,
                    purpose,
                    created_at,
                    expires_at,
                    revoked_at
                """,
                (
                    Json(approved_fields),
                    consent_id,
                )
            )

            row = cur.fetchone()

            conn.commit()

            return jsonify({
                **row_to_dict(row),
                "target_form_label":
                    FORM_LABELS.get(
                        target_form,
                        target_form
                    ),
                "required_fields":
                    FORM_REQUIRED_FIELDS[target_form],
                "data_minimization":
                    True,
                "synthetic_data":
                    True,
            })

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()


@app.post("/consent/<int:consent_id>/revoke")
def revoke_consent(consent_id):

    conn = get_connection()

    try:

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                UPDATE omnilink_core.consent_records
                SET
                    status = 'REVOKED',
                    revoked_at = NOW()
                WHERE consent_id = %s
                RETURNING
                    consent_id,
                    citizen_id,
                    target_form,
                    requested_fields,
                    approved_fields,
                    status,
                    purpose,
                    created_at,
                    expires_at,
                    revoked_at
                """,
                (consent_id,)
            )

            row = cur.fetchone()

            if not row:

                conn.rollback()

                return jsonify({
                    "error":
                        "Consent record not found.",
                    "consent_id":
                        consent_id,
                }), 404

            conn.commit()

            return jsonify({
                **row_to_dict(row),
                "message":
                    "Consent revoked",
                "data_minimization":
                    True,
                "synthetic_data":
                    True,
            })

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()


@app.get("/consent/<int:consent_id>")
def get_consent(consent_id):

    conn = get_connection()

    try:

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT
                    consent_id,
                    citizen_id,
                    target_form,
                    requested_fields,
                    approved_fields,
                    status,
                    purpose,
                    created_at,
                    expires_at,
                    revoked_at
                FROM omnilink_core.consent_records
                WHERE consent_id = %s
                """,
                (consent_id,)
            )

            row = cur.fetchone()

            if not row:

                return jsonify({
                    "error":
                        "Consent record not found.",
                    "consent_id":
                        consent_id,
                }), 404

            target_form = row[
                "target_form"
            ]

            return jsonify({
                **row_to_dict(row),
                "required_fields":
                    FORM_REQUIRED_FIELDS.get(
                        target_form,
                        []
                    ),
                "visible_fields":
                    FORM_VISIBLE_FIELDS.get(
                        target_form,
                        []
                    ),
                "data_minimization":
                    True,
                "synthetic_data":
                    True,
            })

    finally:

        conn.close()


@app.get("/consent/citizen/<citizen_id>")
def get_citizen_consents(citizen_id):

    if not validate_citizen(citizen_id):

        return jsonify({
            "error":
                "Citizen not found.",
            "citizen_id":
                citizen_id,
        }), 404

    conn = get_connection()

    try:

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT
                    consent_id,
                    citizen_id,
                    target_form,
                    requested_fields,
                    approved_fields,
                    status,
                    purpose,
                    created_at,
                    expires_at,
                    revoked_at
                FROM omnilink_core.consent_records
                WHERE citizen_id = %s
                ORDER BY consent_id DESC
                """,
                (citizen_id,)
            )

            rows = cur.fetchall()

            return jsonify({
                "citizen_id":
                    citizen_id,
                "consents": [
                    row_to_dict(row)
                    for row in rows
                ],
                "count":
                    len(rows),
                "data_minimization":
                    True,
                "synthetic_data":
                    True,
            })

    finally:

        conn.close()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5007,
        debug=True
    )