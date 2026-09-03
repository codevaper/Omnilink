import os
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]
MEDIA_DIR = BASE_DIR / "data" / "citizen_media"

load_dotenv(BASE_DIR / ".env")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "ration_card_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "omnilinkadmin")
POSTGRES_PASSWORD = os.getenv(
    "POSTGRES_PASSWORD",
    "omnilinkpass123"
)

SCHEMA = "omnilink_core"
CITIZEN_COUNT = 150

random.seed(20260903)


# ---------------------------------------------------------
# Synthetic reference data
# ---------------------------------------------------------

FIRST_NAMES_MALE = [
    "Aarav", "Aditya", "Akash", "Amit", "Arjun",
    "Dev", "Dhruv", "Karan", "Manish", "Mohit",
    "Nikhil", "Rahul", "Raj", "Rohan", "Sameer",
    "Sanjay", "Shivam", "Varun", "Vikas", "Vivek"
]

FIRST_NAMES_FEMALE = [
    "Aanya", "Ananya", "Anjali", "Divya", "Isha",
    "Kavya", "Meera", "Neha", "Nisha", "Pooja",
    "Priya", "Radhika", "Riya", "Sakshi", "Shreya",
    "Simran", "Sneha", "Sunita", "Tanvi", "Zoya"
]

LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Kumar", "Gupta",
    "Verma", "Mehta", "Shah", "Joshi", "Mishra",
    "Yadav", "Reddy", "Nair", "Iyer", "Chopra",
    "Malhotra", "Kapoor", "Bansal", "Sinha", "Das",
    "Rao", "Agarwal", "Desai", "Jain", "Kulkarni",
    "Menon", "Pillai", "Banerjee", "Ghosh", "Saxena"
]

CITIES = [
    ("New Delhi", "Delhi", "Delhi"),
    ("Jaipur", "Jaipur", "Rajasthan"),
    ("Lucknow", "Lucknow", "Uttar Pradesh"),
    ("Bhopal", "Bhopal", "Madhya Pradesh"),
    ("Ahmedabad", "Ahmedabad", "Gujarat"),
    ("Mumbai", "Mumbai", "Maharashtra"),
    ("Pune", "Pune", "Maharashtra"),
    ("Bengaluru", "Bengaluru Urban", "Karnataka"),
    ("Hyderabad", "Hyderabad", "Telangana"),
    ("Chennai", "Chennai", "Tamil Nadu"),
    ("Kolkata", "Kolkata", "West Bengal"),
    ("Kochi", "Ernakulam", "Kerala"),
    ("Bhubaneswar", "Khordha", "Odisha"),
    ("Patna", "Patna", "Bihar"),
    ("Chandigarh", "Chandigarh", "Chandigarh"),
]

STREETS = [
    "MG Road",
    "Station Road",
    "Lake View Road",
    "Park Street",
    "Gandhi Nagar",
    "Shanti Nagar",
    "Nehru Colony",
    "Green Avenue",
    "Civil Lines",
    "Indira Nagar",
    "Model Town",
    "Ashok Vihar",
    "Rajendra Nagar",
    "Sector 12",
    "Sector 21",
]

OCCUPATIONS = [
    "Teacher",
    "Software Developer",
    "Accountant",
    "Shop Owner",
    "Electrician",
    "Nurse",
    "Driver",
    "Farmer",
    "Engineer",
    "Tailor",
    "Consultant",
    "Administrative Assistant",
    "Sales Executive",
    "Technician",
    "Small Business Owner",
]

EMPLOYERS = [
    "Sunrise Services",
    "Greenfield Enterprises",
    "Metro Works",
    "Bright Future Academy",
    "Civic Solutions",
    "Urban Tech Systems",
    "Community Health Centre",
    "National Trading House",
    "BlueSky Industries",
    "Independent",
]

EDUCATION = [
    "Secondary",
    "Higher Secondary",
    "Diploma",
    "Bachelor's",
    "Master's",
    "Professional",
]

MARITAL_STATUSES = [
    "Single",
    "Married",
    "Widowed",
    "Divorced",
]

CATEGORIES = [
    "General",
    "OBC",
    "SC",
    "ST",
]

BLOOD_GROUPS = [
    "A+",
    "A-",
    "B+",
    "B-",
    "O+",
    "O-",
    "AB+",
    "AB-",
]

LANGUAGES = [
    "Hindi",
    "English",
    "Bengali",
    "Gujarati",
    "Marathi",
    "Tamil",
    "Telugu",
    "Kannada",
    "Malayalam",
    "Odia",
]


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def random_date(start_year=1960, end_year=2005):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)

    days = (end - start).days

    return start + timedelta(
        days=random.randint(0, days)
    )


def safe(value):
    return value.replace("'", "''")


def write_svg(path, title, subtitle, seed_text):
    path.parent.mkdir(parents=True, exist_ok=True)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
width="600" height="400" viewBox="0 0 600 400">
<rect width="600" height="400" fill="#f4f6f8"/>
<rect x="25" y="25" width="550" height="350"
rx="18" fill="white" stroke="#c7cdd4"/>
<circle cx="300" cy="145" r="75" fill="#d9dee5"/>
<circle cx="300" cy="125" r="28" fill="#aeb6c0"/>
<path d="M220 205 C240 170 360 170 380 205
L410 285 L190 285 Z"
fill="#c2c9d1"/>
<text x="300" y="325"
text-anchor="middle"
font-family="Arial"
font-size="22"
font-weight="bold"
fill="#27313c">{title}</text>
<text x="300" y="350"
text-anchor="middle"
font-family="Arial"
font-size="13"
fill="#66717d">{subtitle}</text>
<text x="300" y="48"
text-anchor="middle"
font-family="Arial"
font-size="11"
fill="#8b949e">{seed_text}</text>
</svg>
"""

    path.write_text(
        svg,
        encoding="utf-8"
    )


def write_signature(path, name, citizen_id):
    path.parent.mkdir(parents=True, exist_ok=True)

    signature_seed = sum(
        ord(char)
        for char in name
    ) % 6

    paths = [
        "M40 90 C100 20 120 130 190 65 S300 110 380 45",
        "M35 105 C80 30 135 120 205 55 S315 125 400 55",
        "M45 80 C90 120 140 25 200 85 S300 35 410 90",
        "M35 95 C120 40 145 125 225 70 S320 115 420 50",
        "M40 70 C125 130 160 30 245 85 S340 35 420 100",
        "M35 100 C105 35 155 115 230 60 S320 125 425 65",
    ]

    selected = paths[signature_seed]

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
width="500" height="180" viewBox="0 0 500 180">
<rect width="500" height="180" fill="white"/>
<path d="{selected}"
fill="none"
stroke="#1f2937"
stroke-width="4"
stroke-linecap="round"/>
<text x="250" y="155"
text-anchor="middle"
font-family="Arial"
font-size="12"
fill="#6b7280">
Synthetic signature - {citizen_id}
</text>
</svg>
"""

    path.write_text(
        svg,
        encoding="utf-8"
    )


# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

def get_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


def create_schema(cursor):
    cursor.execute(
        f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE;"
    )

    cursor.execute(
        f"CREATE SCHEMA {SCHEMA};"
    )

    cursor.execute(
        f"""
        CREATE TABLE {SCHEMA}.citizens (
            citizen_id VARCHAR(32) PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            middle_name VARCHAR(100),
            last_name VARCHAR(100) NOT NULL,
            date_of_birth DATE NOT NULL,
            gender VARCHAR(30) NOT NULL,
            marital_status VARCHAR(30),
            father_name VARCHAR(150),
            mother_name VARCHAR(150),
            spouse_name VARCHAR(150),
            nationality VARCHAR(50) NOT NULL,
            category VARCHAR(30),
            disability_status BOOLEAN NOT NULL DEFAULT FALSE,
            blood_group VARCHAR(10),
            preferred_language VARCHAR(50),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    cursor.execute(
        f"""
        CREATE TABLE {SCHEMA}.identity_details (
            citizen_id VARCHAR(32) PRIMARY KEY
                REFERENCES {SCHEMA}.citizens(citizen_id)
                ON DELETE CASCADE,
            synthetic_aadhaar_number VARCHAR(60) UNIQUE NOT NULL,
            pan_number VARCHAR(60) UNIQUE NOT NULL,
            voter_id VARCHAR(60) UNIQUE NOT NULL,
            driving_license_number VARCHAR(60) UNIQUE NOT NULL,
            passport_number VARCHAR(60) UNIQUE NOT NULL,
            ration_card_number VARCHAR(60) UNIQUE NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    cursor.execute(
        f"""
        CREATE TABLE {SCHEMA}.contact_details (
            citizen_id VARCHAR(32) PRIMARY KEY
                REFERENCES {SCHEMA}.citizens(citizen_id)
                ON DELETE CASCADE,
            mobile_number VARCHAR(40) NOT NULL,
            alternate_mobile VARCHAR(40),
            email VARCHAR(160) NOT NULL,
            emergency_contact_name VARCHAR(150),
            emergency_contact_phone VARCHAR(40),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    cursor.execute(
        f"""
        CREATE TABLE {SCHEMA}.address_details (
            address_id SERIAL PRIMARY KEY,
            citizen_id VARCHAR(32) NOT NULL
                REFERENCES {SCHEMA}.citizens(citizen_id)
                ON DELETE CASCADE,
            address_type VARCHAR(30) NOT NULL,
            house_number VARCHAR(30),
            street VARCHAR(150),
            locality VARCHAR(150),
            city VARCHAR(100),
            district VARCHAR(100),
            state VARCHAR(100),
            postal_code VARCHAR(30),
            landmark VARCHAR(150),
            full_address TEXT NOT NULL,
            is_primary BOOLEAN NOT NULL DEFAULT FALSE
        );
        """
    )

    cursor.execute(
        f"""
        CREATE TABLE {SCHEMA}.financial_details (
            citizen_id VARCHAR(32) PRIMARY KEY
                REFERENCES {SCHEMA}.citizens(citizen_id)
                ON DELETE CASCADE,
            annual_income NUMERIC(12,2) NOT NULL,
            family_size INTEGER NOT NULL,
            bank_name VARCHAR(150),
            account_number VARCHAR(80),
            ifsc_code VARCHAR(40),
            branch_name VARCHAR(150),
            account_holder_name VARCHAR(150),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    cursor.execute(
        f"""
        CREATE TABLE {SCHEMA}.education_employment (
            citizen_id VARCHAR(32) PRIMARY KEY
                REFERENCES {SCHEMA}.citizens(citizen_id)
                ON DELETE CASCADE,
            education_level VARCHAR(80),
            occupation VARCHAR(120),
            employer_name VARCHAR(150),
            years_of_experience INTEGER,
            skills TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    cursor.execute(
        f"""
        CREATE TABLE {SCHEMA}.media_assets (
            media_id SERIAL PRIMARY KEY,
            citizen_id VARCHAR(32) NOT NULL
                REFERENCES {SCHEMA}.citizens(citizen_id)
                ON DELETE CASCADE,
            media_type VARCHAR(50) NOT NULL,
            file_path TEXT NOT NULL,
            mime_type VARCHAR(100) NOT NULL,
            verification_required BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    cursor.execute(
        f"""
        CREATE INDEX idx_addresses_citizen
        ON {SCHEMA}.address_details(citizen_id);
        """
    )

    cursor.execute(
        f"""
        CREATE INDEX idx_media_citizen
        ON {SCHEMA}.media_assets(citizen_id);
        """
    )


# ---------------------------------------------------------
# Citizen generation
# ---------------------------------------------------------

def generate_citizen(index):
    citizen_id = f"CIT-{index:06d}"

    gender = random.choice(
        ["Male", "Female"]
    )

    if gender == "Male":
        first_name = random.choice(FIRST_NAMES_MALE)
    else:
        first_name = random.choice(FIRST_NAMES_FEMALE)

    middle_name = random.choice(
        [
            None,
            "Kumar",
            "Raj",
            "Dev",
            "Kiran",
            "Prakash",
            "Anil",
            "Ravi",
            "Shree",
        ]
    )

    last_name = random.choice(LAST_NAMES)

    dob = random_date()

    father_name = (
        f"{random.choice(FIRST_NAMES_MALE)} "
        f"{last_name}"
    )

    mother_name = (
        f"{random.choice(FIRST_NAMES_FEMALE)} "
        f"{last_name}"
    )

    marital_status = random.choice(
        MARITAL_STATUSES
    )

    spouse_name = None

    if marital_status == "Married":
        spouse_first = (
            random.choice(FIRST_NAMES_FEMALE)
            if gender == "Male"
            else random.choice(FIRST_NAMES_MALE)
        )

        spouse_name = (
            f"{spouse_first} {last_name}"
        )

    city, district, state = random.choice(
        CITIES
    )

    street = random.choice(STREETS)

    house_number = str(
        random.randint(1, 999)
    )

    locality = random.choice(
        [
            "Central Colony",
            "Green Park",
            "Shanti Enclave",
            "New Market",
            "Lake District",
            "Sunrise Layout",
            "Civic Nagar",
            "Indira Colony",
        ]
    )

    landmark = random.choice(
        [
            "Near Community Centre",
            "Near City Park",
            "Opposite Municipal School",
            "Near Main Bus Stand",
            "Behind Public Library",
        ]
    )

    postal_code = (
        f"SYN-{state[:3].upper()}-"
        f"{index:04d}"
    )

    full_address = (
        f"{house_number}, {street}, "
        f"{locality}, {city}, {district}, "
        f"{state}, {postal_code}"
    )

    mobile = (
        f"+91-SYN-{index:06d}"
    )

    alternate_mobile = (
        f"+91-ALT-{index:06d}"
    )

    email = (
        f"citizen{index:04d}@omnilink.test"
    )

    emergency_contact_name = (
        f"{random.choice(FIRST_NAMES_MALE + FIRST_NAMES_FEMALE)} "
        f"{random.choice(LAST_NAMES)}"
    )

    emergency_contact_phone = (
        f"+91-EMG-{index:06d}"
    )

    annual_income = random.choice(
        [
            90000,
            120000,
            160000,
            220000,
            280000,
            350000,
            450000,
            600000,
            850000,
            1200000,
        ]
    )

    family_size = random.randint(
        1,
        7
    )

    bank_name = random.choice(
        [
            "SYN National Bank",
            "SYN Citizens Bank",
            "SYN Cooperative Bank",
            "SYN Unity Bank",
            "SYN People's Bank",
        ]
    )

    account_number = (
        f"SYN-ACCT-{index:08d}"
    )

    ifsc_code = (
        f"SYNIFSC{index:06d}"
    )

    branch_name = (
        f"{city} Central Synthetic Branch"
    )

    education_level = random.choice(
        EDUCATION
    )

    occupation = random.choice(
        OCCUPATIONS
    )

    employer_name = random.choice(
        EMPLOYERS
    )

    years_experience = random.randint(
        0,
        25
    )

    skills = ", ".join(
        random.sample(
            [
                "Communication",
                "Computer Basics",
                "Accounting",
                "Teaching",
                "Retail",
                "Data Entry",
                "Customer Service",
                "Driving",
                "Electrical Work",
                "Programming",
                "Documentation",
                "Project Coordination",
                "Healthcare Support",
                "Agriculture",
            ],
            k=3
        )
    )

    # Deliberately synthetic identifiers.
    identity = {
        "synthetic_aadhaar_number":
            f"SYN-AADHAAR-{index:06d}",
        "pan_number":
            f"SYN-PAN-{index:06d}",
        "voter_id":
            f"SYN-VOTER-{index:06d}",
        "driving_license_number":
            f"SYN-DL-{index:06d}",
        "passport_number":
            f"SYN-PASS-{index:06d}",
        "ration_card_number":
            f"SYN-RATION-{index:06d}",
    }

    return {
        "citizen_id": citizen_id,
        "first_name": first_name,
        "middle_name": middle_name,
        "last_name": last_name,
        "date_of_birth": dob,
        "gender": gender,
        "marital_status": marital_status,
        "father_name": father_name,
        "mother_name": mother_name,
        "spouse_name": spouse_name,
        "nationality": "Indian",
        "category": random.choice(CATEGORIES),
        "disability_status": random.random() < 0.06,
        "blood_group": random.choice(BLOOD_GROUPS),
        "preferred_language": random.choice(LANGUAGES),
        "identity": identity,
        "contact": {
            "mobile_number": mobile,
            "alternate_mobile": alternate_mobile,
            "email": email,
            "emergency_contact_name":
                emergency_contact_name,
            "emergency_contact_phone":
                emergency_contact_phone,
        },
        "address": {
            "house_number": house_number,
            "street": street,
            "locality": locality,
            "city": city,
            "district": district,
            "state": state,
            "postal_code": postal_code,
            "landmark": landmark,
            "full_address": full_address,
        },
        "financial": {
            "annual_income": annual_income,
            "family_size": family_size,
            "bank_name": bank_name,
            "account_number": account_number,
            "ifsc_code": ifsc_code,
            "branch_name": branch_name,
            "account_holder_name":
                f"{first_name} {last_name}",
        },
        "education": {
            "education_level": education_level,
            "occupation": occupation,
            "employer_name": employer_name,
            "years_of_experience":
                years_experience,
            "skills": skills,
        },
    }


# ---------------------------------------------------------
# Insert
# ---------------------------------------------------------

def insert_citizen(cursor, citizen):
    citizen_id = citizen["citizen_id"]

    cursor.execute(
        f"""
        INSERT INTO {SCHEMA}.citizens (
            citizen_id,
            first_name,
            middle_name,
            last_name,
            date_of_birth,
            gender,
            marital_status,
            father_name,
            mother_name,
            spouse_name,
            nationality,
            category,
            disability_status,
            blood_group,
            preferred_language
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s
        );
        """,
        (
            citizen_id,
            citizen["first_name"],
            citizen["middle_name"],
            citizen["last_name"],
            citizen["date_of_birth"],
            citizen["gender"],
            citizen["marital_status"],
            citizen["father_name"],
            citizen["mother_name"],
            citizen["spouse_name"],
            citizen["nationality"],
            citizen["category"],
            citizen["disability_status"],
            citizen["blood_group"],
            citizen["preferred_language"],
        )
    )

    identity = citizen["identity"]

    cursor.execute(
        f"""
        INSERT INTO {SCHEMA}.identity_details (
            citizen_id,
            synthetic_aadhaar_number,
            pan_number,
            voter_id,
            driving_license_number,
            passport_number,
            ration_card_number
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s);
        """,
        (
            citizen_id,
            identity["synthetic_aadhaar_number"],
            identity["pan_number"],
            identity["voter_id"],
            identity["driving_license_number"],
            identity["passport_number"],
            identity["ration_card_number"],
        )
    )

    contact = citizen["contact"]

    cursor.execute(
        f"""
        INSERT INTO {SCHEMA}.contact_details (
            citizen_id,
            mobile_number,
            alternate_mobile,
            email,
            emergency_contact_name,
            emergency_contact_phone
        )
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (
            citizen_id,
            contact["mobile_number"],
            contact["alternate_mobile"],
            contact["email"],
            contact["emergency_contact_name"],
            contact["emergency_contact_phone"],
        )
    )

    address = citizen["address"]

    cursor.execute(
        f"""
        INSERT INTO {SCHEMA}.address_details (
            citizen_id,
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
        )
        VALUES (
            %s, 'current', %s, %s, %s, %s, %s,
            %s, %s, %s, %s, TRUE
        );
        """,
        (
            citizen_id,
            address["house_number"],
            address["street"],
            address["locality"],
            address["city"],
            address["district"],
            address["state"],
            address["postal_code"],
            address["landmark"],
            address["full_address"],
        )
    )

    # A second address for roughly 70% of citizens.
    if random.random() < 0.70:
        permanent_city, permanent_district, permanent_state = (
            random.choice(CITIES)
        )

        permanent_street = random.choice(
            STREETS
        )

        permanent_house = str(
            random.randint(1, 999)
        )

        permanent_locality = random.choice(
            [
                "Village Centre",
                "Old Town",
                "Main Bazaar",
                "Riverside Colony",
                "Temple Road",
            ]
        )

        permanent_postal = (
            f"SYN-{permanent_state[:3].upper()}-"
            f"P{citizen_id[-3:]}"
        )

        permanent_full = (
            f"{permanent_house}, {permanent_street}, "
            f"{permanent_locality}, {permanent_city}, "
            f"{permanent_district}, {permanent_state}, "
            f"{permanent_postal}"
        )

        cursor.execute(
            f"""
            INSERT INTO {SCHEMA}.address_details (
                citizen_id,
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
            )
            VALUES (
                %s, 'permanent', %s, %s, %s, %s,
                %s, %s, %s, %s, %s, FALSE
            );
            """,
            (
                citizen_id,
                permanent_house,
                permanent_street,
                permanent_locality,
                permanent_city,
                permanent_district,
                permanent_state,
                permanent_postal,
                "Near Main Road",
                permanent_full,
            )
        )

    financial = citizen["financial"]

    cursor.execute(
        f"""
        INSERT INTO {SCHEMA}.financial_details (
            citizen_id,
            annual_income,
            family_size,
            bank_name,
            account_number,
            ifsc_code,
            branch_name,
            account_holder_name
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            citizen_id,
            financial["annual_income"],
            financial["family_size"],
            financial["bank_name"],
            financial["account_number"],
            financial["ifsc_code"],
            financial["branch_name"],
            financial["account_holder_name"],
        )
    )

    education = citizen["education"]

    cursor.execute(
        f"""
        INSERT INTO {SCHEMA}.education_employment (
            citizen_id,
            education_level,
            occupation,
            employer_name,
            years_of_experience,
            skills
        )
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (
            citizen_id,
            education["education_level"],
            education["occupation"],
            education["employer_name"],
            education["years_of_experience"],
            education["skills"],
        )
    )


def create_media(citizen):
    citizen_id = citizen["citizen_id"]

    citizen_media_dir = (
        MEDIA_DIR / citizen_id
    )

    citizen_media_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    photo_path = (
        citizen_media_dir /
        "profile.svg"
    )

    signature_path = (
        citizen_media_dir /
        "signature.svg"
    )

    id_proof_path = (
        citizen_media_dir /
        "identity_reference.svg"
    )

    address_proof_path = (
        citizen_media_dir /
        "address_reference.svg"
    )

    full_name = (
        f"{citizen['first_name']} "
        f"{citizen['last_name']}"
    )

    write_svg(
        photo_path,
        full_name,
        "Synthetic profile image",
        citizen_id
    )

    write_signature(
        signature_path,
        full_name,
        citizen_id
    )

    write_svg(
        id_proof_path,
        "Synthetic Identity Reference",
        "Non-verifiable prototype asset",
        citizen_id
    )

    write_svg(
        address_proof_path,
        "Synthetic Address Reference",
        "Non-verifiable prototype asset",
        citizen_id
    )

    return [
        (
            "profile_photo",
            photo_path.relative_to(BASE_DIR).as_posix(),
            "image/svg+xml",
        ),
        (
            "signature_image",
            signature_path.relative_to(BASE_DIR).as_posix(),
            "image/svg+xml",
        ),
        (
            "identity_reference",
            id_proof_path.relative_to(BASE_DIR).as_posix(),
            "image/svg+xml",
        ),
        (
            "address_reference",
            address_proof_path.relative_to(BASE_DIR).as_posix(),
            "image/svg+xml",
        ),
    ]


def main():
    MEDIA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = None

    try:
        connection = get_connection()

        cursor = connection.cursor()

        print("Connected to PostgreSQL.")
        print(
            f"Creating {CITIZEN_COUNT} synthetic citizens..."
        )

        create_schema(cursor)

        for index in range(1, CITIZEN_COUNT + 1):

            citizen = generate_citizen(index)

            insert_citizen(
                cursor,
                citizen
            )

            media_items = create_media(
                citizen
            )

            for media_type, file_path, mime_type in media_items:

                cursor.execute(
                    f"""
                    INSERT INTO {SCHEMA}.media_assets (
                        citizen_id,
                        media_type,
                        file_path,
                        mime_type,
                        verification_required
                    )
                    VALUES (%s, %s, %s, %s, FALSE);
                    """,
                    (
                        citizen["citizen_id"],
                        media_type,
                        file_path,
                        mime_type,
                    )
                )

            if index % 25 == 0:
                print(
                    f"Generated {index}/{CITIZEN_COUNT}"
                )

        connection.commit()

        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM {SCHEMA}.citizens;
            """
        )

        citizen_count = cursor.fetchone()[0]

        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM {SCHEMA}.media_assets;
            """
        )

        media_count = cursor.fetchone()[0]

        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM {SCHEMA}.address_details;
            """
        )

        address_count = cursor.fetchone()[0]

        cursor.close()

        print()
        print("======================================")
        print("OmniLink Citizen Registry created")
        print("======================================")
        print(f"Citizens : {citizen_count}")
        print(f"Addresses: {address_count}")
        print(f"Media    : {media_count}")
        print(f"Schema   : {SCHEMA}")
        print()
        print("All identifiers are synthetic.")
        print("No real citizen data was generated.")

    except Exception as exc:
        if connection:
            connection.rollback()

        print()
        print("ERROR:")
        print(str(exc))

        raise

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    main()