import re
from difflib import SequenceMatcher

from flask import Flask, jsonify, request
from flask_cors import CORS


app = Flask(__name__)
CORS(app)


CANONICAL_FIELDS = [
    "first_name",
    "last_name",
    "father_or_guardian_name",
    "address_line",
    "phone_number",
    "pan_number",
    "record_id",
    "application_date",
    "income_amount",
]


FIELD_ALIASES = {
    "first_name": [
        "first_name",
        "f_nme",
        "fname",
        "applicant_fname",
        "student_first",
        "first",
        "given_name",
    ],

    "last_name": [
        "last_name",
        "l_nme",
        "lname",
        "applicant_lname",
        "student_last",
        "last",
        "surname",
    ],

    "father_or_guardian_name": [
        "father_or_guardian_name",
        "father_name",
        "guardian_name",
        "fth_nme",
        "father",
        "guardian",
    ],

    "address_line": [
        "address_line",
        "address_line_1",
        "adr_ln1",
        "addr1",
        "address",
        "street_address",
    ],

    "phone_number": [
        "phone_number",
        "ph_no",
        "contact_number",
        "mobile",
        "phone",
        "mobile_number",
    ],

    "pan_number": [
        "pan_number",
        "pan_no",
        "pan_id",
        "pan",
    ],

    "record_id": [
        "record_id",
        "crd_no",
        "permit_id",
        "application_id",
        "id",
    ],

    "application_date": [
        "application_date",
        "created_dt",
        "apply_date",
        "applied_on",
        "date_applied",
    ],

    "income_amount": [
        "income_amount",
        "inc_amt",
        "annual_income",
        "income",
        "yearly_income",
    ],
}


def normalize_field_name(name):
    """
    Convert different field naming styles into a comparable form.
    """
    value = str(name).strip().lower()

    value = re.sub(
        r"([a-z0-9])([A-Z])",
        r"\1_\2",
        value
    )

    value = value.replace("-", "_")
    value = value.replace(" ", "_")

    value = re.sub(
        r"[^a-z0-9_]",
        "",
        value
    )

    value = re.sub(
        r"_+",
        "_",
        value
    )

    return value.strip("_")


def similarity(a, b):
    return SequenceMatcher(
        None,
        normalize_field_name(a),
        normalize_field_name(b)
    ).ratio()


def find_best_mapping(source_field):
    normalized = normalize_field_name(source_field)

    best_canonical = None
    best_alias = None
    best_score = 0.0

    for canonical, aliases in FIELD_ALIASES.items():

        for alias in aliases:

            alias_normalized = normalize_field_name(alias)

            if normalized == alias_normalized:
                return {
                    "canonical_field": canonical,
                    "matched_alias": alias,
                    "confidence": 1.0,
                    "match_type": "exact"
                }

            score = similarity(
                normalized,
                alias_normalized
            )

            if score > best_score:
                best_score = score
                best_canonical = canonical
                best_alias = alias

    if best_score >= 0.72:
        match_type = "fuzzy"

        return {
            "canonical_field": best_canonical,
            "matched_alias": best_alias,
            "confidence": round(best_score, 3),
            "match_type": match_type
        }

    return None


def map_record(source_record):
    canonical_record = {}
    mappings = []
    unmapped_fields = []

    for source_field, value in source_record.items():

        result = find_best_mapping(source_field)

        if result is None:
            unmapped_fields.append(source_field)
            continue

        canonical_field = result["canonical_field"]

        if canonical_field not in canonical_record:
            canonical_record[canonical_field] = value

        mappings.append({
            "source_field": source_field,
            "canonical_field": canonical_field,
            "matched_alias": result["matched_alias"],
            "confidence": result["confidence"],
            "match_type": result["match_type"],
        })

    return {
        "canonical_record": canonical_record,
        "mappings": mappings,
        "unmapped_fields": unmapped_fields,
    }


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "ai_mapper"
    })


@app.post("/map")
def map_endpoint():
    data = request.get_json(silent=True) or {}

    source_record = data.get("record")

    if not isinstance(source_record, dict):
        return jsonify({
            "error": "record must be a JSON object"
        }), 400

    source_system = data.get(
        "source_system",
        "unknown"
    )

    result = map_record(source_record)

    return jsonify({
        "source_system": source_system,
        "canonical_fields": CANONICAL_FIELDS,
        **result
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5005,
        debug=True
    )