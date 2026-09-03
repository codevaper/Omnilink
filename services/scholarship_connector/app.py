"""
Scholarship connector
-----------------------
Wraps the flat scholarship_applications.csv file and exposes it via the
same normalized REST/JSON shape as the other two connectors. This
simulates a department that only ever exports flat files — realistic
for smaller/older government offices with no real "system" at all.
"""

import os
import csv
from flask import Flask, jsonify, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Default path assumes you run this from services/scholarship_connector/
CSV_PATH = os.getenv(
    "SCHOLARSHIP_CSV_PATH",
    "../../data/scholarship_applications.csv"
)


def load_rows():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def normalize(row):
    """Map messy CSV headers -> canonical field names."""
    return {
        "source_system": "scholarship",
        "source_record_id": row.get("application_id"),
        "first_name": row.get("student_first"),
        "last_name": row.get("student_last"),
        "father_or_guardian_name": row.get("guardian_name"),
        "address_line": row.get("addr1"),
        "phone_number": row.get("mobile"),
        "pan_number": row.get("pan_id"),
        "extra": {
            "scholarship_type": row.get("scholarship_type"),
            "annual_income": row.get("annual_income"),
            "apply_date": row.get("apply_date"),
        },
    }


@app.route("/health")
def health():
    try:
        load_rows()
        return jsonify({
            "status": "ok",
            "service": "scholarship_connector"
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "service": "scholarship_connector",
            "detail": str(e)
        }), 500


@app.route("/records")
def list_records():
    rows = load_rows()
    return jsonify([normalize(r) for r in rows])


@app.route("/records/search")
def search_by_pan():
    pan = request.args.get("pan")

    if not pan:
        return jsonify({
            "error": "pass ?pan=<PAN_NUMBER>"
        }), 400

    rows = load_rows()

    for r in rows:
        if r.get("pan_id") == pan:
            return jsonify(normalize(r))

    return jsonify({"error": "not found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)