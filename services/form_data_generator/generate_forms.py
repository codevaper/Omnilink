import os
import random
from datetime import date, timedelta
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from pymongo import MongoClient


# =========================================================
# Configuration
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "ration_card_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "omnilinkadmin")
POSTGRES_PASSWORD = os.getenv(
    "POSTGRES_PASSWORD",
    "omnilinkpass123"
)

MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(
    os.getenv("MONGO_PORT", "27017")
)
MONGO_USER = os.getenv("MONGO_USER", "omnilinkadmin")
MONGO_PASSWORD = os.getenv(
    "MONGO_PASSWORD",
    "omnilinkpass123"
)

MONGO_DB = "omnilink_forms"

random.seed(20260903)


# =========================================================
# Source data
# =========================================================

def get_postgres_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


def load_citizens():
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

            a.house_number,
            a.street,
            a.locality,
            a.city,
            a.district,
            a.state,
            a.postal_code,
            a.landmark,
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

        JOIN omnilink_core.identity_details i
            ON c.citizen_id = i.citizen_id

        JOIN omnilink_core.contact_details ct
            ON c.citizen_id = ct.citizen_id

        JOIN omnilink_core.address_details a
            ON c.citizen_id = a.citizen_id
            AND a.address_type = 'current'

        JOIN omnilink_core.financial_details f
            ON c.citizen_id = f.citizen_id

        JOIN omnilink_core.education_employment e
            ON c.citizen_id = e.citizen_id

        ORDER BY c.citizen_id;
        """
    )

    rows = cursor.fetchall()

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

        "house_number",
        "street",
        "locality",
        "city",
        "district",
        "state",
        "postal_code",
        "landmark",
        "full_address",

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

    citizens = []

    for row in rows:
        citizens.append(
            dict(zip(columns, row))
        )

    cursor.close()
    connection.close()

    return citizens


# =========================================================
# Formatting helpers
# =========================================================

def formatted_name(citizen):
    parts = [
        citizen["first_name"],
        citizen["middle_name"],
        citizen["last_name"],
    ]

    return " ".join(
        str(part)
        for part in parts
        if part
    )


def format_date_iso(value):
    return value.isoformat()


def format_date_slash(value):
    return value.strftime("%d/%m/%Y")


def format_date_text(value):
    return value.strftime("%d-%b-%Y")


def format_phone_full(value):
    return value.replace(
        "-SYN-",
        " "
    )


def select_citizens(citizens, percentage):
    count = max(
        1,
        int(len(citizens) * percentage)
    )

    return random.sample(
        citizens,
        count
    )


# =========================================================
# Form builders
# =========================================================

def build_ration(c):
    return {
        "citizen_ref": c["citizen_id"],
        "f_nme": c["first_name"],
        "m_name": c["middle_name"],
        "l_nme": c["last_name"],
        "fth_nme": c["father_name"],
        "dob": format_date_slash(c["date_of_birth"]),
        "gender_code": c["gender"][0],
        "adr_ln1": c["full_address"],
        "dist_name": c["district"],
        "state_nm": c["state"],
        "pin_cd": c["postal_code"],
        "ph_no": c["mobile_number"],
        "crd_no": c["ration_card_number"],
        "pan_no": c["pan_number"],
        "fml_sz": c["family_size"],
        "inc_amt": float(c["annual_income"]),
        "category_code": c["category"],
        "card_category": random.choice(
            ["Priority", "General", "Special"]
        ),
        "gas_connection": random.choice(
            [True, False]
        ),
        "household_type": random.choice(
            ["Urban", "Rural", "Semi-Urban"]
        ),
    }


def build_scholarship(c):
    return {
        "citizen_ref": c["citizen_id"],
        "student_first": c["first_name"],
        "student_middle": c["middle_name"],
        "student_last": c["last_name"],
        "guardian_name": c["father_name"],
        "birth_date": format_date_text(
            c["date_of_birth"]
        ),
        "student_gender": c["gender"],
        "home_address": c["full_address"],
        "district_name": c["district"],
        "state_name": c["state"],
        "mobile": c["mobile_number"],
        "contact_email": c["email"],
        "pan_id": c["pan_number"],
        "annual_income": float(c["annual_income"]),
        "student_category": c["category"],
        "bank_acc": c["account_number"],
        "bank_ifsc": c["ifsc_code"],
        "course_name": random.choice(
            [
                "BSc Computer Science",
                "BA Economics",
                "BCom",
                "BTech",
                "Diploma in Nursing",
                "MA Education",
                "ITI Electrical",
            ]
        ),
        "institution_name": random.choice(
            [
                "National College",
                "City Government College",
                "Central Institute",
                "State Technical College",
                "District Education Centre",
            ]
        ),
        "year_of_study": random.randint(1, 5),
        "hostel_required": random.choice(
            [True, False]
        ),
    }


def build_municipal(c):
    return {
        "citizen_ref": c["citizen_id"],
        "applicant_fname": c["first_name"],
        "applicant_lname": c["last_name"],
        "father_or_owner": c["father_name"],
        "property_address": c["full_address"],
        "property_district": c["district"],
        "property_state": c["state"],
        "postal_code": c["postal_code"],
        "contact_number": c["mobile_number"],
        "taxpayer_pan": c["pan_number"],
        "property_id": (
            f"SYN-PROP-{c['citizen_id'][-6:]}"
        ),
        "permit_id": (
            f"SYN-PERMIT-{c['citizen_id'][-6:]}"
        ),
        "permit_type": random.choice(
            [
                "Residential Construction",
                "Renovation",
                "Commercial Construction",
                "Boundary Modification",
            ]
        ),
        "built_up_area": random.randint(
            450,
            3200
        ),
        "floor_count": random.randint(
            1,
            4
        ),
        "owner_occupation": c["occupation"],
        "application_dt": format_date_iso(
            date.today() -
            timedelta(
                days=random.randint(0, 900)
            )
        ),
    }


def build_voter(c):
    return {
        "citizen_ref": c["citizen_id"],
        "applicant_name": formatted_name(c),
        "dob": format_date_iso(
            c["date_of_birth"]
        ),
        "sex": c["gender"],
        "relation_name": c["father_name"],
        "residential_address": c["full_address"],
        "phone": c["mobile_number"],
        "email_address": c["email"],
        "epic_no": c["voter_id"],
        "constituency": random.choice(
            [
                "Central",
                "North",
                "South",
                "East",
                "West",
            ]
        ),
        "polling_booth": (
            f"SYN-BOOTH-{random.randint(100, 999)}"
        ),
        "form_reference": (
            f"SYN-VFORM-{c['citizen_id'][-6:]}"
        ),
    }


def build_driving(c):
    return {
        "citizen_ref": c["citizen_id"],
        "full_name": formatted_name(c),
        "birth_date": format_date_slash(
            c["date_of_birth"]
        ),
        "residential_address": c["full_address"],
        "mobile_no": c["mobile_number"],
        "license_id": c["driving_license_number"],
        "bloodgroup": c["blood_group"],
        "emergency_person": c[
            "emergency_contact_name"
        ],
        "emergency_phone": c[
            "emergency_contact_phone"
        ],
        "vehicle_class": random.choice(
            [
                "LMV",
                "MCWG",
                "LMV+MCWG",
                "Transport",
            ]
        ),
        "training_center": random.choice(
            [
                "City Driving School",
                "SafeRoad Institute",
                "Government Motor Training Centre",
            ]
        ),
        "test_status": random.choice(
            [
                "Pending",
                "Passed",
                "Scheduled",
            ]
        ),
    }


def build_pension(c):
    return {
        "citizen_ref": c["citizen_id"],
        "beneficiary_name": formatted_name(c),
        "birth_dt": format_date_text(
            c["date_of_birth"]
        ),
        "husband_or_wife": c["spouse_name"],
        "telephone": c["mobile_number"],
        "current_residence": c["full_address"],
        "district": c["district"],
        "state": c["state"],
        "yearly_earnings": float(
            c["annual_income"]
        ),
        "bank_account": c["account_number"],
        "bank_code": c["ifsc_code"],
        "account_name": c["account_holder_name"],
        "retirement_scheme": random.choice(
            [
                "Senior Pension",
                "Widow Support",
                "Disability Pension",
                "Social Security Pension",
            ]
        ),
        "retirement_year": random.randint(
            2015,
            2035
        ),
    }


def build_housing(c):
    return {
        "citizen_ref": c["citizen_id"],
        "applicant_name": formatted_name(c),
        "guardian": c["father_name"],
        "residence": c["full_address"],
        "contact": c["mobile_number"],
        "family_members": c["family_size"],
        "income_per_year": float(
            c["annual_income"]
        ),
        "social_category": c["category"],
        "home_ownership": random.choice(
            [
                "No House",
                "Shared",
                "Owned",
            ]
        ),
        "house_condition": random.choice(
            [
                "Temporary",
                "Semi-Permanent",
                "Permanent",
            ]
        ),
        "land_area_sqft": random.randint(
            400,
            5000
        ),
        "bank_details": {
            "account": c["account_number"],
            "ifsc": c["ifsc_code"],
        },
        "housing_scheme": random.choice(
            [
                "Urban Housing Support",
                "Rural Housing Support",
                "Affordable Home Initiative",
            ]
        ),
    }


def build_health(c):
    return {
        "citizen_ref": c["citizen_id"],
        "patient_name": formatted_name(c),
        "birth_date": format_date_iso(
            c["date_of_birth"]
        ),
        "sex": c["gender"],
        "home_addr": c["full_address"],
        "mobile": c["mobile_number"],
        "blood_type": c["blood_group"],
        "family_identifier": (
            f"SYN-FAM-{c['citizen_id'][-6:]}"
        ),
        "disability": c[
            "disability_status"
        ],
        "emergency_name": c[
            "emergency_contact_name"
        ],
        "emergency_number": c[
            "emergency_contact_phone"
        ],
        "scheme_name": random.choice(
            [
                "Basic Health Coverage",
                "Family Health Support",
                "Community Care Scheme",
            ]
        ),
        "preferred_hospital": random.choice(
            [
                "District Hospital",
                "Community Health Centre",
                "Government General Hospital",
            ]
        ),
    }


def build_employment(c):
    return {
        "citizen_ref": c["citizen_id"],
        "candidate_name": formatted_name(c),
        "birth": format_date_slash(
            c["date_of_birth"]
        ),
        "sex": c["gender"],
        "qualification": c["education_level"],
        "job_title": c["occupation"],
        "current_employer": c[
            "employer_name"
        ],
        "experience_years": c[
            "years_of_experience"
        ],
        "skill_set": c["skills"],
        "residential": c["full_address"],
        "mobile_phone": c["mobile_number"],
        "email_id": c["email"],
        "annual_salary": float(
            c["annual_income"]
        ),
        "preferred_sector": random.choice(
            [
                "Government",
                "Private",
                "Public Sector",
                "Self Employment",
            ]
        ),
        "job_preference": random.choice(
            [
                "Full Time",
                "Part Time",
                "Contract",
            ]
        ),
    }


def build_welfare(c):
    return {
        "citizen_ref": c["citizen_id"],
        "name_of_beneficiary": formatted_name(c),
        "age_dob": format_date_text(
            c["date_of_birth"]
        ),
        "spouse": c["spouse_name"],
        "parent_guardian": c["father_name"],
        "contact_mobile": c["mobile_number"],
        "postal_address": c["full_address"],
        "yearly_income": float(
            c["annual_income"]
        ),
        "household_count": c["family_size"],
        "category": c["category"],
        "disability_flag": c[
            "disability_status"
        ],
        "beneficiary_type": random.choice(
            [
                "Senior Citizen",
                "Family Assistance",
                "Women Support",
                "Disability Support",
            ]
        ),
        "benefit_program": random.choice(
            [
                "Community Support",
                "Social Assistance",
                "Family Welfare Benefit",
            ]
        ),
        "preferred_language": c[
            "preferred_language"
        ],
    }


# =========================================================
# Form configuration
# =========================================================

FORMS = [
    (
        "ration_card_forms",
        "Ration Card",
        build_ration,
        0.80,
    ),
    (
        "scholarship_forms",
        "Scholarship",
        build_scholarship,
        0.62,
    ),
    (
        "municipal_permit_forms",
        "Municipal Permit",
        build_municipal,
        0.58,
    ),
    (
        "voter_registration_forms",
        "Voter Registration",
        build_voter,
        0.78,
    ),
    (
        "driving_license_forms",
        "Driving Licence",
        build_driving,
        0.52,
    ),
    (
        "pension_forms",
        "Pension",
        build_pension,
        0.35,
    ),
    (
        "housing_assistance_forms",
        "Housing Assistance",
        build_housing,
        0.47,
    ),
    (
        "health_scheme_forms",
        "Health Scheme",
        build_health,
        0.73,
    ),
    (
        "employment_skill_forms",
        "Employment / Skill",
        build_employment,
        0.66,
    ),
    (
        "social_welfare_forms",
        "Social Welfare",
        build_welfare,
        0.42,
    ),
]


# =========================================================
# MongoDB
# =========================================================

def get_mongo_database():
    mongo_uri = (
        f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}"
        f"@{MONGO_HOST}:{MONGO_PORT}"
        "/?authSource=admin"
    )

    client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=10000
    )

    client.admin.command("ping")

    return client[MONGO_DB]


def create_catalog(database, citizens):
    collection = database["form_catalog"]

    collection.drop()

    catalog_entries = []

    for collection_name, form_name, _, percentage in FORMS:

        estimated_count = int(
            len(citizens) * percentage
        )

        catalog_entries.append({
            "form_code": collection_name,
            "form_name": form_name,
            "departmental_collection": collection_name,
            "estimated_records": estimated_count,
            "citizen_count": estimated_count,
            "schema_style": "department-specific",
            "uses_canonical_schema": False,
            "synthetic_data": True,
        })

    collection.insert_many(
        catalog_entries
    )


def create_forms(database, citizens):

    totals = []

    for (
        collection_name,
        form_name,
        builder,
        percentage,
    ) in FORMS:

        collection = database[
            collection_name
        ]

        collection.drop()

        selected = select_citizens(
            citizens,
            percentage
        )

        documents = []

        for citizen in selected:

            document = builder(
                citizen
            )

            document["form_name"] = form_name

            document["source_department"] = (
                form_name
            )

            document["synthetic_record"] = True

            documents.append(
                document
            )

        if documents:
            result = collection.insert_many(
                documents
            )

            collection.create_index(
                "citizen_ref"
            )

            totals.append(
                (
                    form_name,
                    len(result.inserted_ids)
                )
            )

    return totals


# =========================================================
# Main
# =========================================================

def main():

    print("=" * 60)
    print("OmniLink Departmental Form Generator")
    print("=" * 60)

    print()
    print("Loading 150 citizen profiles...")

    citizens = load_citizens()

    print(
        f"Loaded {len(citizens)} citizens."
    )

    if len(citizens) != 150:
        raise RuntimeError(
            "Expected exactly 150 citizens."
        )

    print()
    print(
        "Connecting to MongoDB..."
    )

    database = get_mongo_database()

    print(
        f"Using MongoDB database: {MONGO_DB}"
    )

    create_catalog(
        database,
        citizens
    )

    totals = create_forms(
        database,
        citizens
    )

    print()
    print("=" * 60)
    print("Departmental datasets created")
    print("=" * 60)

    total_records = 0

    for form_name, count in totals:

        print(
            f"{form_name:<32} {count:>4} records"
        )

        total_records += count

    print("-" * 60)

    print(
        f"{'TOTAL FORM RECORDS':<32}"
        f"{total_records:>4}"
    )

    print()
    print(
        "MongoDB database:"
        f" {MONGO_DB}"
    )

    print(
        "Citizens used:"
        f" {len(citizens)}"
    )

    print()
    print(
        "All generated data is synthetic."
    )


if __name__ == "__main__":
    main()