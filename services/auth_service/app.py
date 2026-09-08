"""
OmniLink Audit Service
Tracks every action: consent, prefill, submission, status changes
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os
import sys
import json
from datetime import datetime

# Add parent directory for shared imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.error_handlers import register_error_handlers

app = Flask(__name__)
CORS(app)

# Register global error handlers
register_error_handlers(app)

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost:5432/omnilink')

def get_db():
    return psycopg2.connect(DATABASE_URL)

# ── HEALTH CHECK ───────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'Audit Service Online',
        'timestamp': datetime.now().isoformat(),
        'service': 'omnilink-audit'
    })

# ── LOG AUDIT EVENT ────────────────────────────
@app.route('/audit/log', methods=['POST'])
def log_audit():
    data = request.get_json(silent=True)
    
    if not isinstance(data, dict):
        return jsonify({'error': 'Request body must be a JSON object.'}), 400
    
    required_fields = ['actor_type', 'actor_id', 'action']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required.'}), 400
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO audit_logs (
                actor_type, actor_id, action, citizen_id, 
                target_form, fields_affected, purpose, 
                correlation_id, ip_address, metadata, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, timestamp
        """, (
            data['actor_type'],
            data['actor_id'],
            data['action'],
            data.get('citizen_id'),
            data.get('target_form'),
            json.dumps(data.get('fields_affected', {})),
            data.get('purpose'),
            data.get('correlation_id'),
            request.remote_addr,
            json.dumps(data.get('metadata', {})),
            data.get('status', 'success')
        ))
        
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'audit_id': result[0],
            'timestamp': result[1].isoformat(),
            'status': 'logged'
        }), 201
        
    except Exception as e:
        print(f"[Audit] Error logging: {e}")
        return jsonify({'error': str(e)}), 500

# ── GET AUDIT FOR CITIZEN ──────────────────────
@app.route('/audit/citizen/<citizen_id>', methods=['GET'])
def get_citizen_audit(citizen_id):
    limit = int(request.args.get('limit', 50))
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, timestamp, actor_type, actor_id, action, 
                   target_form, fields_affected, purpose, 
                   correlation_id, status
            FROM audit_logs
            WHERE citizen_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """, (citizen_id, limit))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        events = [{
            'audit_id': row[0],
            'timestamp': row[1].isoformat() if hasattr(row[1], 'isoformat') else row[1],
            'actor_type': row[2],
            'actor_id': row[3],
            'action': row[4],
            'target_form': row[5],
            'fields_affected': row[6] if isinstance(row[6], dict) else json.loads(row[6] or '{}'),
            'purpose': row[7],
            'correlation_id': row[8],
            'status': row[9]
        } for row in rows]
        
        return jsonify({
            'citizen_id': citizen_id,
            'total_events': len(events),
            'events': events
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── GET ALL AUDIT EVENTS ───────────────────────
@app.route('/audit/all', methods=['GET'])
def get_all_audit():
    limit = int(request.args.get('limit', 100))
    action_filter = request.args.get('action')
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        query = """
            SELECT id, timestamp, actor_type, actor_id, action, 
                   citizen_id, target_form, purpose, correlation_id, status
            FROM audit_logs
        """
        params = []
        
        if action_filter:
            query += " WHERE action = %s"
            params.append(action_filter)
        
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        events = [{
            'audit_id': row[0],
            'timestamp': row[1].isoformat() if hasattr(row[1], 'isoformat') else row[1],
            'actor_type': row[2],
            'actor_id': row[3],
            'action': row[4],
            'citizen_id': row[5],
            'target_form': row[6],
            'purpose': row[7],
            'correlation_id': row[8],
            'status': row[9]
        } for row in rows]
        
        return jsonify({
            'total_events': len(events),
            'events': events
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── GET QUALITY SCORE ──────────────────────────
@app.route('/quality/<citizen_id>', methods=['GET'])
def get_quality_score(citizen_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT citizen_id, quality_score, quality_category, 
                   missing_fields, invalid_fields, last_checked
            FROM citizen_quality_scores
            WHERE citizen_id = %s
        """, (citizen_id,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Citizen not found.'}), 404
        
        return jsonify({
            'citizen_id': row[0],
            'quality_score': row[1],
            'quality_category': row[2],
            'missing_fields': row[3] if isinstance(row[3], list) else json.loads(row[3] or '[]'),
            'invalid_fields': row[4] if isinstance(row[4], dict) else json.loads(row[4] or '{}'),
            'last_checked': row[5].isoformat() if hasattr(row[5], 'isoformat') else row[5]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5005))
    app.run(debug=False, host='0.0.0.0', port=port)