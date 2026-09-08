"""
OmniLink Connector Service
Reusable connectors for legacy and modern systems
- REST Connector (modern APIs)
- CSV Connector (legacy file exports)
- SOAP Connector (legacy web services)
- Database Connector (legacy databases)

NOTE: This service runs server-side. Browser/Bolt NEVER connects here directly.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import csv
import io
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# After app = Flask(__name__) and CORS:
register_error_handlers(app)

app = Flask(__name__)
CORS(app)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.error_handlers import register_error_handlers
register_error_handlers(app)

# ── CONFIG ─────────────────────────────────────
POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "ration_card_db"),
    "user": os.getenv("POSTGRES_USER", "omnilinkadmin"),
    "password": os.getenv("POSTGRES_PASSWORD", "omnilinkpass123"),
}

# ── CANONICAL FIELD MAPPING ───────────────────
CANONICAL_FIELDS = {
    "first_name": ["first_name", "student_first", "patient_first", "applicant_first", "member_first", "beneficiary_first", "firstName"],
    "last_name": ["last_name", "student_last", "patient_last", "applicant_last", "member_last", "beneficiary_last", "lastName"],
    "date_of_birth": ["date_of_birth", "birth_date", "dob", "DOB", "dateOfBirth"],
    "mobile_number": ["mobile_number", "contact_mobile", "phone", "mobile", "phoneNumber"],
    "email": ["email", "contact_email", "email_address", "emailAddress"],
    "address": ["address", "home_address", "residence", "permanent_address", "currentAddress"],
    "annual_income": ["annual_income", "income", "family_income", "yearlyIncome"],
    "bank_account": ["bank_account", "bank_acc", "account_no", "accountNumber"],
    "bank_ifsc": ["bank_ifsc", "ifsc", "ifsc_code", "IFSC"],
}


def map_to_canonical(data: dict) -> dict:
    """Map legacy field names to canonical field names."""
    canonical = {}
    
    for canonical_name, possible_names in CANONICAL_FIELDS.items():
        for legacy_name in possible_names:
            if legacy_name in data:
                canonical[canonical_name] = data[legacy_name]
                break
    
    return canonical


# ── HEALTH CHECK ───────────────────────────────
@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "connector_service",
        "connectors": ["rest", "csv", "soap", "database"],
    })


# ══════════════════════════════════════════════
# 1. REST CONNECTOR
# ══════════════════════════════════════════════

@app.post("/connector/rest/fetch", methods=["POST"])
def rest_connector():
    """Connect to a modern REST API and map to canonical format."""
    data = request.get_json(silent=True)
    
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400
    
    url = data.get("url")
    headers = data.get("headers", {})
    params = data.get("params", {})
    
    if not url:
        return jsonify({"error": "url is required."}), 400
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        response_data = response.json()
        
        # Map to canonical
        if isinstance(response_data, list):
            canonical_data = [map_to_canonical(item) for item in response_data]
        else:
            canonical_data = map_to_canonical(response_data)
        
        return jsonify({
            "connector": "rest",
            "status": "success",
            "source": url,
            "records": len(canonical_data) if isinstance(canonical_data, list) else 1,
            "canonical_data": canonical_data,
            "mapping": CANONICAL_FIELDS,
            "synthetic_data": True,
        })
        
    except Exception as e:
        return jsonify({
            "connector": "rest",
            "status": "error",
            "error": str(e),
        }), 500


# ══════════════════════════════════════════════
# 2. CSV CONNECTOR
# ══════════════════════════════════════════════

@app.post("/connector/csv/parse", methods=["POST"])
def csv_connector():
    """Parse legacy CSV file and map to canonical format."""
    
    if "file" not in request.files:
        return jsonify({"error": "No CSV file uploaded."}), 400
    
    file = request.files["file"]
    
    try:
        # Read CSV content
        content = file.read().decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(content))
        
        records = []
        mapping_used = {}
        
        for row in csv_reader:
            # Map legacy CSV headers to canonical
            canonical_record = map_to_canonical(dict(row))
            records.append(canonical_record)
            
            # Track which legacy fields mapped to which canonical fields
            for legacy_key in row.keys():
                for canonical_name, possible_names in CANONICAL_FIELDS.items():
                    if legacy_key in possible_names:
                        mapping_used[legacy_key] = canonical_name
        
        return jsonify({
            "connector": "csv",
            "status": "success",
            "filename": file.filename,
            "records": len(records),
            "canonical_data": records,
            "mapping_used": mapping_used,
            "synthetic_data": True,
        })
        
    except Exception as e:
        return jsonify({
            "connector": "csv",
            "status": "error",
            "error": str(e),
        }), 500


# ══════════════════════════════════════════════
# 3. SOAP CONNECTOR (Simulated Legacy SOAP)
# ══════════════════════════════════════════════

@app.post("/connector/soap/parse", methods=["POST"])
def soap_connector():
    """Parse legacy SOAP XML response and map to canonical format."""
    data = request.get_json(silent=True)
    
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400
    
    xml_content = data.get("xml", "")
    
    if not xml_content:
        return jsonify({"error": "xml is required."}), 400
    
    try:
        # Parse XML
        root = ET.fromstring(xml_content)
        
        # Extract all leaf elements
        def extract_elements(element, prefix=""):
            result = {}
            for child in element:
                name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                
                if len(child) > 0:
                    result.update(extract_elements(child, prefix + name + "_"))
                else:
                    result[prefix + name] = child.text
            return result
        
        xml_data = extract_elements(root)
        
        # Map to canonical
        canonical_data = map_to_canonical(xml_data)
        
        return jsonify({
            "connector": "soap",
            "status": "success",
            "raw_xml": xml_content,
            "parsed_fields": xml_data,
            "canonical_data": canonical_data,
            "synthetic_data": True,
        })
        
    except Exception as e:
        return jsonify({
            "connector": "soap",
            "status": "error",
            "error": str(e),
        }), 500


@app.get("/connector/soap/sample", methods=["GET"])
def soap_sample():
    """Return sample SOAP XML for demo."""
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetCitizenResponse>
      <Citizen>
        <FirstName>Priya</FirstName>
        <LastName>Sharma</LastName>
        <DOB>1992-05-18</DOB>
        <Phone>9876543210</Phone>
        <Email>priya.sharma@example.com</Email>
        <HomeAddress>Pune, Maharashtra</HomeAddress>
        <AccountNumber>1234567890</AccountNumber>
        <IFSC>HDFC0001234</IFSC>
      </Citizen>
    </GetCitizenResponse>
  </soap:Body>
</soap:Envelope>"""
    
    return jsonify({
        "sample_xml": sample_xml,
        "description": "Simulated legacy SOAP response from a government system",
    })


# ══════════════════════════════════════════════
# 4. DATABASE CONNECTOR (Server-Side Only)
# ══════════════════════════════════════════════

@app.post("/connector/database/query", methods=["POST"])
def database_connector():
    """
    Query legacy database (server-side only).
    Bolt/browser NEVER calls this directly with credentials.
    Credentials are in environment variables, not in the request.
    """
    data = request.get_json(silent=True)
    
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400
    
    query_type = data.get("query_type", "select")
    table = data.get("table", "omnilink_core.citizens")
    limit = int(data.get("limit", 10))
    
    # SECURITY: Only allow SELECT queries
    if query_type.lower() != "select":
        return jsonify({"error": "Only SELECT queries are allowed."}), 403
    
    # SECURITY: Only allow specific tables
    allowed_tables = [
        "omnilink_core.citizens",
        "omnilink_core.consent_records",
        "omnilink_core.address_details",
        "omnilink_core.contact_details",
        "citizen_quality_scores",
        "officers",
        "audit_logs",
    ]
    
    if table not in allowed_tables:
        return jsonify({
            "error": "Table not allowed.",
            "allowed_tables": allowed_tables,
        }), 403
    
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT * FROM {table} LIMIT %s", (limit,))
                rows = cur.fetchall()
        finally:
            conn.close()
        
        # Convert to JSON-serializable
        records = []
        for row in rows:
            record = dict(row)
            for key, value in record.items():
                if hasattr(value, "isoformat"):
                    record[key] = value.isoformat()
            records.append(record)
        
        # Map to canonical if citizens table
        canonical_data = [map_to_canonical(r) for r in records] if "citizens" in table else records
        
        return jsonify({
            "connector": "database",
            "status": "success",
            "table": table,
            "records": len(records),
            "canonical_data": canonical_data,
            "raw_data": records,
            "synthetic_data": True,
        })
        
    except Exception as e:
        return jsonify({
            "connector": "database",
            "status": "error",
            "error": str(e),
        }), 500


@app.get("/connector/database/tables", methods=["GET"])
def database_tables():
    """List allowed tables for demo."""
    return jsonify({
        "allowed_tables": [
            "omnilink_core.citizens",
            "omnilink_core.consent_records",
            "omnilink_core.address_details",
            "omnilink_core.contact_details",
            "citizen_quality_scores",
            "officers",
            "audit_logs",
        ],
        "note": "Database connector is server-side only. Credentials never exposed.",
    })


# ── SAMPLE CSV CONTENT ─────────────────────────
@app.get("/connector/csv/sample", methods=["GET"])
def csv_sample():
    """Return sample CSV for demo."""
    sample_csv = """first_name,last_name,dob,mobile,email,address,income,account_no,ifsc
Amit,Patel,1988-03-15,9876543210,amit.patel@example.com,Mumbai,450000,1234567890,HDFC0001234
Sneha,Reddy,1992-07-22,9876543211,sneha.reddy@example.com,Hyderabad,600000,2345678901,ICIC0002345
Ravi,Kumar,1975-11-30,9876543212,ravi.kumar@example.com,Delhi,350000,3456789012,SBI0003456"""
    
    return jsonify({
        "sample_csv": sample_csv,
        "description": "Simulated legacy CSV export from a government department",
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5008, debug=True)