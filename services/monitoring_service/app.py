"""
OmniLink Monitoring Service
Provides real-time statistics, SLA tracking, and dashboard data
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone, timedelta
import os

app = Flask(__name__)
CORS(app)

# ── CONFIG ─────────────────────────────────────
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

SUBMISSIONS_COLLECTION = "submitted_applications"
AUDIT_COLLECTION = "application_audit"

SLA_HOURS = 48  # Service Level Agreement: process within 48 hours

# ── HELPERS ────────────────────────────────────
def get_mongo():
    client = MongoClient(MONGO_URI)
    return client, client[MONGO_DB]


def get_pg_connection():
    return psycopg2.connect(**POSTGRES_CONFIG)


def isoformat_datetime(dt):
    if dt and hasattr(dt, "isoformat"):
        return dt.isoformat()
    return dt


def calculate_sla(submitted_at, processed_at):
    """Calculate if SLA was met (processed within 48 hours)."""
    if not submitted_at or not processed_at:
        return None
    
    if hasattr(submitted_at, "isoformat"):
        submitted_at = submitted_at.replace(tzinfo=None)
    if hasattr(processed_at, "isoformat"):
        processed_at = processed_at.replace(tzinfo=None)
    
    processing_time = processed_at - submitted_at
    sla_deadline = timedelta(hours=SLA_HOURS)
    
    return processing_time <= sla_deadline


# ── HEALTH CHECK ───────────────────────────────
@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "monitoring_service",
        "port": 5010,
        "sla_hours": SLA_HOURS,
    })


# ── OVERALL STATISTICS ─────────────────────────
@app.get("/monitor/stats")
def get_overall_stats():
    """Overall statistics for dashboard."""
    client, db = get_mongo()
    
    try:
        # MongoDB: Submissions stats
        total_submissions = db[SUBMISSIONS_COLLECTION].count_documents({})
        
        status_counts = {}
        for status in ["SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED"]:
            status_counts[status.lower()] = db[SUBMISSIONS_COLLECTION].count_documents({"status": status})
        
        # Recent submissions
        recent = list(
            db[SUBMISSIONS_COLLECTION]
            .find({}, {"_id": 0, "submission_id": 1, "citizen_id": 1, "target_form": 1, "status": 1, "created_at": 1})
            .sort("created_at", -1)
            .limit(10)
        )
        for doc in recent:
            doc["created_at"] = isoformat_datetime(doc.get("created_at"))
        
        # Department-wise breakdown
        pipeline = [
            {"$group": {"_id": "$target_form", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        department_stats = list(db[SUBMISSIONS_COLLECTION].aggregate(pipeline))
        
        return jsonify({
            "total_submissions": total_submissions,
            "status_counts": status_counts,
            "department_stats": [
                {"form": d["_id"], "count": d["count"]}
                for d in department_stats
            ],
            "recent_submissions": recent,
            "synthetic_data": True,
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        client.close()


# ── SLA COMPLIANCE ─────────────────────────────
@app.get("/monitor/sla")
def get_sla_compliance():
    """SLA compliance metrics."""
    client, db = get_mongo()
    
    try:
        submissions = list(
            db[SUBMISSIONS_COLLECTION]
            .find({}, {"_id": 0, "submission_id": 1, "target_form": 1, "created_at": 1, "updated_at": 1, "status": 1})
        )
        
        sla_met = 0
        sla_missed = 0
        sla_pending = 0
        processing_times = []
        
        for sub in submissions:
            submitted_at = sub.get("created_at")
            processed_at = sub.get("updated_at")
            status = sub.get("status", "SUBMITTED")
            
            if status in ("APPROVED", "REJECTED") and submitted_at and processed_at:
                sla_result = calculate_sla(submitted_at, processed_at)
                
                if sla_result:
                    sla_met += 1
                else:
                    sla_missed += 1
                
                # Processing time in hours
                if hasattr(submitted_at, "replace") and hasattr(processed_at, "replace"):
                    submitted_naive = submitted_at.replace(tzinfo=None)
                    processed_naive = processed_at.replace(tzinfo=None)
                    hours = (processed_naive - submitted_naive).total_seconds() / 3600
                    processing_times.append(round(hours, 1))
            else:
                sla_pending += 1
        
        total_processed = sla_met + sla_missed
        compliance_pct = round((sla_met / total_processed * 100), 2) if total_processed > 0 else 100.0
        
        avg_processing_hours = round(sum(processing_times) / len(processing_times), 1) if processing_times else 0
        
        return jsonify({
            "sla_hours": SLA_HOURS,
            "total_submissions": len(submissions),
            "sla_met": sla_met,
            "sla_missed": sla_missed,
            "sla_pending": sla_pending,
            "compliance_percentage": compliance_pct,
            "average_processing_hours": avg_processing_hours,
            "processing_times": processing_times[-20:],  # Last 20 for chart
            "synthetic_data": True,
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        client.close()


# ── CITIZEN STATS ──────────────────────────────
@app.get("/monitor/citizens")
def get_citizen_stats():
    """Citizen statistics from PostgreSQL."""
    conn = get_pg_connection()
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Total citizens
            cur.execute("SELECT COUNT(*) as total FROM omnilink_core.citizens")
            total_citizens = cur.fetchone()["total"]
            
            # Quality score distribution
            cur.execute("""
                SELECT quality_category, COUNT(*) as count
                FROM citizen_quality_scores
                GROUP BY quality_category
                ORDER BY quality_category
            """)
            quality_distribution = cur.fetchall()
            
            # Total consent records
            cur.execute("SELECT COUNT(*) as total FROM omnilink_core.consent_records")
            total_consents = cur.fetchone()["total"]
            
            # Consent status breakdown
            cur.execute("""
                SELECT status, COUNT(*) as count
                FROM omnilink_core.consent_records
                GROUP BY status
            """)
            consent_stats = cur.fetchall()
            
        return jsonify({
            "total_citizens": total_citizens,
            "quality_distribution": [
                {"category": q["quality_category"], "count": q["count"]}
                for q in quality_distribution
            ],
            "total_consents": total_consents,
            "consent_stats": [
                {"status": c["status"], "count": c["count"]}
                for c in consent_stats
            ],
            "synthetic_data": True,
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# ── DEPARTMENT BREAKDOWN ───────────────────────
@app.get("/monitor/departments")
def get_department_breakdown():
    """Department-wise submission and SLA stats."""
    client, db = get_mongo()
    
    try:
        submissions = list(
            db[SUBMISSIONS_COLLECTION]
            .find({}, {"_id": 0, "target_form": 1, "status": 1, "created_at": 1, "updated_at": 1})
        )
        
        departments = {}
        
        for sub in submissions:
            form = sub.get("target_form", "unknown")
            
            if form not in departments:
                departments[form] = {
                    "form": form,
                    "total": 0,
                    "approved": 0,
                    "rejected": 0,
                    "pending": 0,
                    "under_review": 0,
                    "sla_met": 0,
                    "sla_missed": 0,
                }
            
            departments[form]["total"] += 1
            status = sub.get("status", "SUBMITTED")
            
            if status == "APPROVED":
                departments[form]["approved"] += 1
            elif status == "REJECTED":
                departments[form]["rejected"] += 1
            elif status == "UNDER_REVIEW":
                departments[form]["under_review"] += 1
            else:
                departments[form]["pending"] += 1
            
            # SLA check
            if status in ("APPROVED", "REJECTED"):
                sla_result = calculate_sla(sub.get("created_at"), sub.get("updated_at"))
                if sla_result:
                    departments[form]["sla_met"] += 1
                elif sla_result is False:
                    departments[form]["sla_missed"] += 1
        
        return jsonify({
            "departments": list(departments.values()),
            "total_departments": len(departments),
            "synthetic_data": True,
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        client.close()


# ── ACTIVITY FEED ──────────────────────────────
@app.get("/monitor/activity")
def get_activity_feed():
    """Recent activity feed for dashboard."""
    client, db = get_mongo()
    
    try:
        activities = list(
            db[AUDIT_COLLECTION]
            .find({}, {"_id": 0, "audit_id": 1, "submission_id": 1, "citizen_id": 1, "action": 1, "new_status": 1, "created_at": 1})
            .sort("created_at", -1)
            .limit(20)
        )
        
        for activity in activities:
            activity["created_at"] = isoformat_datetime(activity.get("created_at"))
        
        return jsonify({
            "activities": activities,
            "count": len(activities),
            "synthetic_data": True,
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        client.close()


# ── FULL DASHBOARD DATA ────────────────────────
@app.get("/monitor/dashboard")
def get_full_dashboard():
    """Complete dashboard data in one call."""
    client, db = get_mongo()
    conn = get_pg_connection()
    
    try:
        # MongoDB stats
        total_submissions = db[SUBMISSIONS_COLLECTION].count_documents({})
        approved = db[SUBMISSIONS_COLLECTION].count_documents({"status": "APPROVED"})
        rejected = db[SUBMISSIONS_COLLECTION].count_documents({"status": "REJECTED"})
        pending = db[SUBMISSIONS_COLLECTION].count_documents({"status": "SUBMITTED"})
        under_review = db[SUBMISSIONS_COLLECTION].count_documents({"status": "UNDER_REVIEW"})
        
        # PostgreSQL stats
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) as total FROM omnilink_core.citizens")
            total_citizens = cur.fetchone()["total"]
            
            cur.execute("SELECT COUNT(*) as total FROM omnilink_core.consent_records")
            total_consents = cur.fetchone()["total"]
        
        return jsonify({
            "overview": {
                "total_citizens": total_citizens,
                "total_submissions": total_submissions,
                "total_consents": total_consents,
            },
            "submission_status": {
                "approved": approved,
                "rejected": rejected,
                "pending": pending,
                "under_review": under_review,
            },
            "synthetic_data": True,
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        client.close()
        conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5010, debug=True)