from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pymongo import MongoClient
from datetime import datetime, timezone

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

MONGO_DB = os.getenv("MONGO_DB_FORMS", "omnilink_forms")


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


def get_pg_connection():
    return psycopg2.connect(**POSTGRES_CONFIG)


def get_mongo():
    client = MongoClient(MONGO_URI)
    return client, client[MONGO_DB]


def load_approved_consent(citizen_id, target_form):
    conn = get_pg_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
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
                  AND target_form = %s
                ORDER BY consent_id DESC
                LIMIT 1
                """,
                (citizen_id, target_form),
            )

            row = cur.fetchone()

            if not row:
                return None

            return dict(row)

    finally:
        conn.close()


def load_citizen_profile(citizen_id):
    conn = get_pg_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute(
                """
                SELECT
                    c.citizen_id,
                    c.first_name,
                    c.middle_name,
                    c.last_name,
                    c.gender,
                    c.date_of_birth,
                    c.marital_status,
                    c.category
                FROM omnilink_core.citizens c
                WHERE c.citizen_id = %s
                """,
                (citizen_id,),
            )

            citizen = cur.fetchone()

            if not citizen:
                return None

            cur.execute(
                """
                SELECT
                    a.address_type,
                    a.full_address
                FROM omnilink_core.address_details a
                WHERE a.citizen_id = %s
                ORDER BY
                    CASE
                        WHEN a.address_type = 'CURRENT' THEN 0
                        ELSE 1
                    END,
                    a.address_id
                LIMIT 1
                """,
                (citizen_id,),
            )

            address = cur.fetchone()

            cur.execute(
                """
                SELECT
                    mobile_number,
                    alternate_mobile,
                    email,
                    emergency_contact_name,
                    emergency_contact_phone
                FROM omnilink_core.contact_details
                WHERE citizen_id = %s
                LIMIT 1
                """,
                (citizen_id,),
            )

            contact = cur.fetchone()

            cur.execute(
                """
                SELECT
                    synthetic_aadhaar_number,
                    pan_number,
                    voter_id,
                    driving_license_number,
                    passport_number,
                    ration_card_number
                FROM omnilink_core.identity_details
                WHERE citizen_id = %s
                LIMIT 1
                """,
                (citizen_id,),
            )

            identity = cur.fetchone()

            cur.execute(
                """
                SELECT
                    annual_income,
                    family_size,
                    bank_name,
                    account_number,
                    ifsc_code,
                    branch_name,
                    account_holder_name
                FROM omnilink_core.financial_details
                WHERE citizen_id = %s
                LIMIT 1
                """,
                (citizen_id,),
            )

            financial = cur.fetchone()

            cur.execute(
                """
                SELECT
                    education_level,
                    occupation,
                    employer_name,
                    years_of_experience,
                    skills
                FROM omnilink_core.education_employment
                WHERE citizen_id = %s
                LIMIT 1
                """,
                (citizen_id,),
            )

            education_employment = cur.fetchone()

            return {
                "citizen": dict(citizen),
                "address": dict(address) if address else {},
                "contact": dict(contact) if contact else {},
                "identity": dict(identity) if identity else {},
                "financial": dict(financial) if financial else {},
                "education_employment": (
                    dict(education_employment)
                    if education_employment
                    else {}
                ),
            }

    finally:
        conn.close()


def normalize_date(value):
    if value is None:
        return None

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)


def build_reusable_field_map(profile):
    citizen = profile["citizen"]
    address = profile["address"]
    contact = profile["contact"]
    identity = profile["identity"]
    financial = profile["financial"]
    education = profile["education_employment"]

    return {
        "first_name": citizen.get("first_name"),
        "middle_name": citizen.get("middle_name"),
        "last_name": citizen.get("last_name"),

        "full_name": " ".join(
            part
            for part in [
                citizen.get("first_name"),
                citizen.get("middle_name"),
                citizen.get("last_name"),
            ]
            if part
        ),

        "gender": citizen.get("gender"),
        "date_of_birth": normalize_date(
            citizen.get("date_of_birth")
        ),
        "marital_status": citizen.get("marital_status"),
        "category": citizen.get("category"),

        "mobile_number": contact.get("mobile_number"),
        "alternate_mobile_number": contact.get(
            "alternate_mobile"
        ),
        "email": contact.get("email"),

        "emergency_contact_name": contact.get(
            "emergency_contact_name"
        ),
        "emergency_contact_phone": contact.get(
            "emergency_contact_phone"
        ),

        "address": address.get("full_address"),

        "aadhaar_number": identity.get(
            "synthetic_aadhaar_number"
        ),
        "pan_number": identity.get(
            "pan_number"
        ),
        "voter_id": identity.get(
            "voter_id"
        ),
        "driving_license_number": identity.get(
            "driving_license_number"
        ),
        "passport_number": identity.get(
            "passport_number"
        ),
        "ration_card_number": identity.get(
            "ration_card_number"
        ),

        "annual_income": financial.get(
            "annual_income"
        ),
        "family_size": financial.get(
            "family_size"
        ),
        "bank_name": financial.get(
            "bank_name"
        ),
        "bank_account": financial.get(
            "account_number"
        ),
        "bank_ifsc": financial.get(
            "ifsc_code"
        ),
        "branch_name": financial.get(
            "branch_name"
        ),
        "account_holder_name": financial.get(
            "account_holder_name"
        ),

        "highest_qualification": education.get(
            "education_level"
        ),
        "education_level": education.get(
            "education_level"
        ),
        "occupation": education.get(
            "occupation"
        ),
        "employer_name": education.get(
            "employer_name"
        ),
        "years_of_experience": education.get(
            "years_of_experience"
        ),
        "skills": education.get(
            "skills"
        ),
    }


TARGET_FIELD_ALIASES = {
    "ration_card": {
        "first_name": "head_first_name",
        "last_name": "head_last_name",
        "mobile_number": "contact_mobile",
        "address": "residential_address",
        "annual_income": "yearly_income",
        "category": "household_category",
        "ration_card_number": "ration_number",
    },

    "scholarship": {
        "first_name": "student_first",
        "middle_name": "student_middle",
        "last_name": "student_last",
        "father_name": "guardian_name",
        "date_of_birth": "birth_date",
        "gender": "student_gender",
        "address": "home_address",
        "mobile_number": "contact_mobile",
        "email": "contact_email",
        "pan_number": "pan_id",
        "annual_income": "annual_income",
        "category": "student_category",
        "bank_account": "bank_acc",
        "bank_ifsc": "bank_ifsc",
    },

    "municipal_permit": {
        "first_name": "applicant_fname",
        "last_name": "applicant_lname",
        "mobile_number": "contact_number",
        "address": "address_line_1",
        "email": "email_address",
        "pan_number": "pan_number",
    },

    "voter_registration": {
        "first_name": "given_name",
        "last_name": "surname",
        "date_of_birth": "dob",
        "gender": "sex",
        "address": "residential_address",
        "mobile_number": "mobile",
        "voter_id": "elector_id",
    },

    "driving_license": {
        "first_name": "applicant_first",
        "last_name": "applicant_last",
        "date_of_birth": "birth_date",
        "gender": "gender",
        "address": "permanent_address",
        "mobile_number": "mobile_phone",
        "email": "email_id",
        "driving_license_number": "license_number",
    },

    "pension": {
        "full_name": "beneficiary_name",
        "date_of_birth": "birth_dt",
        "mobile_number": "telephone",
        "address": "residential_address",
        "bank_account": "bank_account",
        "bank_ifsc": "bank_code",
    },

    "housing_assistance": {
        "first_name": "applicant_first",
        "last_name": "applicant_last",
        "mobile_number": "phone",
        "address": "current_address",
        "annual_income": "household_income",
        "category": "social_category",
    },

    "health_scheme": {
        "first_name": "beneficiary_first",
        "last_name": "beneficiary_last",
        "date_of_birth": "birth_date",
        "gender": "gender",
        "mobile_number": "mobile_no",
        "address": "address",
    },

    "employment_skill": {
        "first_name": "candidate_first_name",
        "last_name": "candidate_last_name",
        "date_of_birth": "dob",
        "mobile_number": "phone_number",
        "email": "email",
        "address": "address_text",
        "education_level": "education_level",
        "occupation": "job_title",
        "employer_name": "company_name",
        "years_of_experience": "experience_years",
        "skills": "skills",
    },

    "social_welfare": {
        "first_name": "applicant_first",
        "last_name": "applicant_last",
        "mobile_number": "contact_mobile",
        "address": "address_text",
        "annual_income": "annual_household_income",
        "category": "beneficiary_category",
    },
}


def get_target_record(citizen_id, target_form):
    collection_name = FORM_COLLECTIONS.get(target_form)

    if not collection_name:
        return None, None

    client, db = get_mongo()

    try:
        record = db[collection_name].find_one(
            {"citizen_ref": citizen_id},
            {"_id": 0},
        )

        return record, collection_name

    finally:
        client.close()


def create_prefill_payload(citizen_id, target_form):
    consent = load_approved_consent(
        citizen_id,
        target_form,
    )

    if not consent:
        return {
            "error": (
                "No consent record found for this citizen "
                "and form."
            )
        }, 404

    if consent["status"] != "APPROVED":
        return {
            "error": "Consent is not APPROVED.",
            "status": consent["status"],
            "consent_id": consent["consent_id"],
        }, 403

    approved_fields = consent.get(
        "approved_fields"
    ) or []

    profile = load_citizen_profile(citizen_id)

    if not profile:
        return {
            "error": "Citizen not found."
        }, 404

    target_record, collection_name = get_target_record(
        citizen_id,
        target_form,
    )

    reusable_fields = build_reusable_field_map(
        profile
    )

    aliases = TARGET_FIELD_ALIASES.get(
        target_form,
        {}
    )

    prefill = {}
    mapped_fields = []
    skipped_fields = []

    for canonical_field in approved_fields:

        source_value = reusable_fields.get(
            canonical_field
        )

        if source_value is None:
            skipped_fields.append({
                "canonical_field": canonical_field,
                "reason": (
                    "No value available in citizen vault"
                ),
            })
            continue

        target_field = aliases.get(
            canonical_field
        )

        if not target_field:
            skipped_fields.append({
                "canonical_field": canonical_field,
                "reason": (
                    "No target-form mapping configured"
                ),
            })
            continue

        prefill[target_field] = source_value

        mapped_fields.append({
            "canonical_field": canonical_field,
            "target_field": target_field,
        })

    return {
        "citizen_id": citizen_id,
        "target_form": target_form,
        "consent_id": consent["consent_id"],
        "consent_status": consent["status"],
        "purpose": consent["purpose"],
        "approved_fields": approved_fields,
        "prefill": prefill,
        "mapped_fields": mapped_fields,
        "skipped_fields": skipped_fields,
        "target_collection": collection_name,
        "target_record_found": target_record is not None,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "synthetic_data": True,
    }, 200


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "prefill_engine",
        "port": 5008,
    })


@app.get("/forms")
def forms():
    return jsonify({
        "forms": [
            {
                "form_key": key,
                "collection": collection,
                "mapping_fields": len(
                    TARGET_FIELD_ALIASES.get(
                        key,
                        {}
                    )
                ),
            }
            for key, collection
            in FORM_COLLECTIONS.items()
        ],
        "count": len(FORM_COLLECTIONS),
    })


@app.post("/prefill")
def prefill():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": (
                "Request body must be a JSON object."
            )
        }), 400

    citizen_id = data.get("citizen_id")
    target_form = data.get("target_form")

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

    try:
        payload, status_code = create_prefill_payload(
            citizen_id,
            target_form,
        )

        return jsonify(payload), status_code

    except Exception as exc:
        return jsonify({
            "error": str(exc),
            "service": "prefill_engine",
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5008,
        debug=True,
    )