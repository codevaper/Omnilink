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
    )


def get_mongo_database():
    uri = (
        f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}"
        f"@{MONGO_HOST}:{MONGO_PORT}/"
        f"?authSource=admin"
    )

    client = MongoClient(
        uri,
        serverSelectionTimeoutMS=5000
    )

    client.admin.command("ping")

    return client[MONGO_DB]


# =========================================================
# Canonical citizen profile
# =========================================================

def get_citizen_profile(citizen_id):

    connection = get_postgres_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            c.citizen_id,
            c.first_name,
            c.middle_name,
            c.last_name,
            c.date_of_birth,
            c.gender,
            c.marital_status,
            c.father_name,
            c.mother_name,
            c.spouse_name,
            c.nationality,
            c.category,
            c.disability_status,
            c.blood_group,
            c.preferred_language,

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

        JOIN omnilink_core.identity_details i
            ON c.citizen_id = i.citizen_id

        JOIN omnilink_core.contact_details ct
            ON c.citizen_id = ct.citizen_id

        JOIN omnilink_core.financial_details f
            ON c.citizen_id = f.citizen_id

        JOIN omnilink_core.education_employment e
            ON c.citizen_id = e.citizen_id

        WHERE c.citizen_id = %s;
        """,
        (citizen_id,)
    )

    row = cursor.fetchone()

    if row is None:
        cursor.close()
        connection.close()
        return None

    columns = [
        "citizen_id",
        "first_name",
        "middle_name",
        "last_name",
        "date_of_birth",
        "gender",
        "marital_status",
        "father_name",
        "mother_name",
        "spouse_name",
        "nationality",
        "category",
        "disability_status",
        "blood_group",
        "preferred_language",

        "synthetic_aadhaar_number",
        "pan_number",
        "voter_id",
        "driving_license_number",
        "passport_number",
        "ration_card_number",

        "mobile_number",
        "alternate_mobile",
        "email",
        "emergency_contact_name",
        "emergency_contact_phone",

        "annual_income",
        "family_size",
        "bank_name",
        "account_number",
        "ifsc_code",
        "branch_name",
        "account_holder_name",

        "education_level",
        "occupation",
        "employer_name",
        "years_of_experience",
        "skills",
    ]

    profile = dict(
        zip(columns, row)
    )

    cursor.execute(
        """
        SELECT
            address_type,
            house_number,
            street,
            locality,
            city,
            district,
            state,
            postal_code,
            landmark,
            full_address,
            is_primary
        FROM omnilink_core.address_details
        WHERE citizen_id = %s
        ORDER BY is_primary DESC, address_id;
        """,
        (citizen_id,)
    )

    address_rows = cursor.fetchall()

    addresses = []

    for address in address_rows:

        (
            address_type,
            house_number,
            street,
            locality,
            city,
            district,
            state,
            postal_code,
            landmark,
            full_address,
            is_primary,
        ) = address

        addresses.append({
            "address_type": address_type,
            "house_number": house_number,
            "street": street,
            "locality": locality,
            "city": city,
            "district": district,
            "state": state,
            "postal_code": postal_code,
            "landmark": landmark,
            "full_address": full_address,
            "is_primary": is_primary,
        })

    profile["addresses"] = addresses

    cursor.execute(
        """
        SELECT
            media_type,
            file_path,
            mime_type,
            verification_required
        FROM omnilink_core.media_assets
        WHERE citizen_id = %s
        ORDER BY media_id;
        """,
        (citizen_id,)
    )

    media_rows = cursor.fetchall()

    media = []

    for media_item in media_rows:

        (
            media_type,
            file_path,
            mime_type,
            verification_required,
        ) = media_item

        media.append({
            "media_type": media_type,
            "file_path": file_path,
            "mime_type": mime_type,
            "verification_required": (
                verification_required
            ),
        })

    profile["media_assets"] = media

    cursor.close()
    connection.close()

    return profile


# =========================================================
# Departmental source information
# =========================================================

def get_department_records(citizen_id):

    database = get_mongo_database()

    collections = [
        (
            "ration_card_forms",
            "Ration Card"
        ),
        (
            "scholarship_forms",
            "Scholarship"
        ),
        (
            "municipal_permit_forms",
            "Municipal Permit"
        ),
        (
            "voter_registration_forms",
            "Voter Registration"
        ),
        (
            "driving_license_forms",
            "Driving Licence"
        ),
        (
            "pension_forms",
            "Pension"
        ),
        (
            "housing_assistance_forms",
            "Housing Assistance"
        ),
        (
            "health_scheme_forms",
            "Health Scheme"
        ),
        (
            "employment_skill_forms",
            "Employment / Skill"
        ),
        (
            "social_welfare_forms",
            "Social Welfare"
        ),
    ]

    records = []

    for collection_name, department_name in collections:

        collection = database[
            collection_name
        ]

        document = collection.find_one(
            {
                "citizen_ref": citizen_id
            }
        )

        if document:

            document["_id"] = str(
                document["_id"]
            )

            records.append({
                "department": department_name,
                "collection": collection_name,
                "record": document,
            })

    return records


# =========================================================
# Canonical reusable fields
# =========================================================

def build_reusable_profile(profile):

    return {
        "citizen_id":
            profile["citizen_id"],

        "name": {
            "first_name":
                profile["first_name"],
            "middle_name":
                profile["middle_name"],
            "last_name":
                profile["last_name"],
            "full_name":
                " ".join(
                    value
                    for value in [
                        profile["first_name"],
                        profile["middle_name"],
                        profile["last_name"],
                    ]
                    if value
                ),
        },

        "identity": {
            "date_of_birth":
                profile["date_of_birth"].isoformat(),

            "gender":
                profile["gender"],

            "father_name":
                profile["father_name"],

            "mother_name":
                profile["mother_name"],

            "spouse_name":
                profile["spouse_name"],

            "synthetic_aadhaar_number":
                profile["synthetic_aadhaar_number"],

            "pan_number":
                profile["pan_number"],

            "voter_id":
                profile["voter_id"],

            "driving_license_number":
                profile[
                    "driving_license_number"
                ],

            "passport_number":
                profile["passport_number"],

            "ration_card_number":
                profile["ration_card_number"],
        },

        "contact": {
            "mobile_number":
                profile["mobile_number"],

            "alternate_mobile":
                profile["alternate_mobile"],

            "email":
                profile["email"],

            "emergency_contact_name":
                profile[
                    "emergency_contact_name"
                ],

            "emergency_contact_phone":
                profile[
                    "emergency_contact_phone"
                ],
        },

        "addresses":
            profile["addresses"],

        "financial": {
            "annual_income":
                float(profile["annual_income"]),

            "family_size":
                profile["family_size"],

            "bank_name":
                profile["bank_name"],

            "account_number":
                profile["account_number"],

            "ifsc_code":
                profile["ifsc_code"],

            "branch_name":
                profile["branch_name"],

            "account_holder_name":
                profile["account_holder_name"],
        },

        "education_employment": {
            "education_level":
                profile["education_level"],

            "occupation":
                profile["occupation"],

            "employer_name":
                profile["employer_name"],

            "years_of_experience":
                profile[
                    "years_of_experience"
                ],

            "skills":
                profile["skills"],
        },

        "other": {
            "nationality":
                profile["nationality"],

            "category":
                profile["category"],

            "disability_status":
                profile[
                    "disability_status"
                ],

            "blood_group":
                profile["blood_group"],

            "preferred_language":
                profile[
                    "preferred_language"
                ],
        },

        "media_assets":
            profile["media_assets"],
    }


# =========================================================
# Routes
# =========================================================

@app.get("/health")
def health():

    return jsonify({
        "status": "ok",
        "service": "citizen_vault"
    })


@app.get("/citizens/<citizen_id>")
def get_citizen(citizen_id):

    try:

        profile = get_citizen_profile(
            citizen_id
        )

    except Exception as exc:

        return jsonify({
            "error":
                "Could not load citizen profile",
            "details":
                str(exc)
        }), 500

    if profile is None:

        return jsonify({
            "error":
                "Citizen not found",
            "citizen_id":
                citizen_id
        }), 404

    return jsonify({

        "citizen": build_reusable_profile(
            profile
        ),

        "source_records":
            get_department_records(
                citizen_id
            ),

        "retrieved_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "synthetic_data":
            True
    })


@app.get("/citizens")
def list_citizens():

    connection = get_postgres_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            citizen_id,
            first_name,
            middle_name,
            last_name,
            date_of_birth,
            gender
        FROM omnilink_core.citizens
        ORDER BY citizen_id;
        """
    )

    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    citizens = []

    for row in rows:

        (
            citizen_id,
            first_name,
            middle_name,
            last_name,
            date_of_birth,
            gender,
        ) = row

        full_name = " ".join(
            value
            for value in [
                first_name,
                middle_name,
                last_name
            ]
            if value
        )

        citizens.append({
            "citizen_id":
                citizen_id,

            "full_name":
                full_name,

            "date_of_birth":
                date_of_birth.isoformat(),

            "gender":
                gender,
        })

    return jsonify({
        "count":
            len(citizens),

        "citizens":
            citizens,

        "synthetic_data":
            True
    })


# =========================================================
# Main
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5006,
        debug=True
    )