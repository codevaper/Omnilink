import os

from flask import Flask, jsonify, request
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "ration_card_db"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def normalize(row):
    """Map messy ration_crds columns to OmniLink's canonical field names."""
    return {
        "source_system": "ration_card",
        "source_record_id": row["crd_no"],
        "first_name": row["f_nme"],
        "last_name": row["l_nme"],
        "father_or_guardian_name": row["fth_nme"],
        "address_line": row["adr_ln1"],
        "phone_number": row["ph_no"],
        "pan_number": row["pan_no"],
        "extra": {
            "family_size": row["fml_sz"],
            "income_amount": (
                float(row["inc_amt"])
                if row["inc_amt"] is not None
                else None
            ),
            "created_dt": (
                row["created_dt"].isoformat()
                if row["created_dt"]
                else None
            ),
        },
    }


@app.route("/health")
def health():
    try:
        conn = get_connection()
        conn.close()
        return jsonify({
            "status": "ok",
            "service": "ration_card_connector"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "service": "ration_card_connector",
            "detail": str(e)
        }), 500


@app.route("/records")
def list_records():
    conn = get_connection()
    cur = conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    )

    cur.execute("SELECT * FROM ration_crds ORDER BY id;")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify([normalize(row) for row in rows])


@app.route("/records/search")
def search_by_pan():
    pan = request.args.get("pan")

    if not pan:
        return jsonify({
            "error": "pass ?pan=<PAN_NUMBER>"
        }), 400

    conn = get_connection()
    cur = conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    )

    cur.execute(
        "SELECT * FROM ration_crds WHERE pan_no = %s;",
        (pan,)
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "not found"}), 404

    return jsonify(normalize(row))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)