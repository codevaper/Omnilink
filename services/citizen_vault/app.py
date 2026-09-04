import os
from datetime import datetime, timezone

import psycopg2
from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient


app = Flask(__name__)
CORS(app)


# =========================================================
# Configuration
# =========================================================

POSTGRES_HOST = os.getenv(
    "POSTGRES_HOST",
    "localhost"
)

POSTGRES_PORT = os.getenv(
    "POSTGRES_PORT",
    "5432"
)

POSTGRES_DB = os.getenv(
    "POSTGRES_DB",
    "ration_card_db"
)

POSTGRES_USER = os.getenv(
    "POSTGRES_USER",
    "omnilinkadmin"
)

POSTGRES_PASSWORD = os.getenv(
    "POSTGRES_PASSWORD",
    "omnilinkpass123"
)

# Optional explicit SSL mode.
# Railway PostgreSQL public TCP proxy requires SSL.
POSTGRES_SSLMODE = os.getenv(
    "POSTGRES_SSLMODE",
    "prefer"
)


MONGO_HOST = os.getenv(
    "MONGO_HOST",
    "localhost"
)

MONGO_PORT = int(
    os.getenv(
        "MONGO_PORT",
        "27017"
    )
)

MONGO_USER = os.getenv(
    "MONGO_USER",
    "omnilinkadmin"
)

MONGO_PASSWORD = os.getenv(
    "MONGO_PASSWORD",
    "omnilinkpass123"
)

MONGO_DB = "omnilink_forms"


# =========================================================
# Database helpers
# =========================================================

def get_postgres_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        sslmode=POSTGRES_SSLMODE,
    )


def get_mongo_database():
    uri = (
        f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}"
        f"@{MONGO_HOST}:{MONGO_PORT}/"
        f"?authSource=admin"
    )

    client = MongoClient(uri)
    return client[MONGO_DB]


# =========================================================
# Helpers
# =========================================================

def serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat()

    return value


def row_to_dict(cursor, row):
    columns = [description[0] for description in cursor.description]

    return {
        column: serialize_value(value)
        for column, value in zip(columns, row)
    }


# =========================================================
# Health
# =========================================================

@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "citizen_vault"
    })


# =========================================================
# Citizens
# =========================================================

@app.get("/citizens")
def list_citizens():
    connection = get_postgres_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                c.citizen_id,
                c.first_name,
                c.middle_name,
                c.last_name,
                c.date_of_birth,
                c.father_name,
                c.gender,
                c.marital_status,
                c.category,

                i.synthetic_aadhaar_number,
                i.pan_number,
                i.voter_id,
                i.driving_license_number,
                i.passport_number,
                i.ration_card_number,

                ct.mobile_number,
                ct.alternate_mobile,
                ct.email,
                ct.emergency_contact_name,
                ct.emergency_contact_phone,

                a.address_type,
                a.full_address,

                f.annual_income,
                f.family_size,
                f.bank_name,
                f.account_number,
                f.ifsc_code,
                f.branch_name,
                f.account_holder_name,

                e.education_level,
                e.occupation,
                e.employer_name,
                e.years_of_experience,
                e.skills

            FROM omnilink_core.citizens c

            LEFT JOIN omnilink_core.identity_details i
                ON i.citizen_id = c.citizen_id

            LEFT JOIN omnilink_core.contact_details ct
                ON ct.citizen_id = c.citizen_id

            LEFT JOIN omnilink_core.address_details a
                ON a.citizen_id = c.citizen_id

            LEFT JOIN omnilink_core.financial_details f
                ON f.citizen_id = c.citizen_id

            LEFT JOIN omnilink_core.education_employment e
                ON e.citizen_id = c.citizen_id

            ORDER BY c.citizen_id
        """)

        rows = cursor.fetchall()

        citizens = [
            row_to_dict(cursor, row)
            for row in rows
        ]

        return jsonify({
            "count": len(citizens),
            "citizens": citizens
        })

    finally:
        connection.close()


# =========================================================
# Single citizen
# =========================================================

@app.get("/citizens/<citizen_id>")
def get_citizen(citizen_id):
    connection = get_postgres_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                c.citizen_id,
                c.first_name,
                c.middle_name,
                c.last_name,
                c.date_of_birth,
                c.father_name,
                c.gender,
                c.marital_status,
                c.category,

                i.synthetic_aadhaar_number,
                i.pan_number,
                i.voter_id,
                i.driving_license_number,
                i.passport_number,
                i.ration_card_number,

                ct.mobile_number,
                ct.alternate_mobile,
                ct.email,
                ct.emergency_contact_name,
                ct.emergency_contact_phone,

                a.address_type,
                a.full_address,

                f.annual_income,
                f.family_size,
                f.bank_name,
                f.account_number,
                f.ifsc_code,
                f.branch_name,
                f.account_holder_name,

                e.education_level,
                e.occupation,
                e.employer_name,
                e.years_of_experience,
                e.skills

            FROM omnilink_core.citizens c

            LEFT JOIN omnilink_core.identity_details i
                ON i.citizen_id = c.citizen_id

            LEFT JOIN omnilink_core.contact_details ct
                ON ct.citizen_id = c.citizen_id

            LEFT JOIN omnilink_core.address_details a
                ON a.citizen_id = c.citizen_id

            LEFT JOIN omnilink_core.financial_details f
                ON f.citizen_id = c.citizen_id

            LEFT JOIN omnilink_core.education_employment e
                ON e.citizen_id = c.citizen_id

            WHERE c.citizen_id = %s
        """, (citizen_id,))

        row = cursor.fetchone()

        if row is None:
            return jsonify({
                "error": "Citizen not found"
            }), 404

        return jsonify(row_to_dict(cursor, row))

    finally:
        connection.close()


# =========================================================
# Startup
# =========================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5006"))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )