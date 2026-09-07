"""
OmniLink Audit Middleware
Import this in any service to auto-log events
"""

import requests
import os

AUDIT_SERVICE_URL = os.environ.get(
    'AUDIT_SERVICE_URL', 
    'http://localhost:5005'
)

def log_audit_event(
    actor_type: str,
    actor_id: str,
    action: str,
    citizen_id: str = None,
    target_form: str = None,
    fields_affected: dict = None,
    purpose: str = None,
    correlation_id: str = None,
    status: str = 'success'
):
    """Call Audit Service to log an event. Returns True if logged."""
    try:
        payload = {
            'actor_type': actor_type,
            'actor_id': actor_id,
            'action': action,
            'citizen_id': citizen_id,
            'target_form': target_form,
            'fields_affected': fields_affected or {},
            'purpose': purpose,
            'correlation_id': correlation_id,
            'status': status
        }
        
        response = requests.post(
            f"{AUDIT_SERVICE_URL}/audit/log",
            json=payload,
            timeout=5
        )
        
        return response.status_code in [200, 201]
        
    except Exception as e:
        print(f"[Audit] Failed to log event '{action}': {e}")
        return False


# ── CONVENIENCE FUNCTIONS ──────────────────────

def audit_consent_requested(citizen_id, target_form, requested_fields, purpose, consent_id):
    return log_audit_event(
        actor_type='citizen',
        actor_id=citizen_id,
        action='consent_requested',
        citizen_id=citizen_id,
        target_form=target_form,
        fields_affected={'requested_fields': requested_fields},
        purpose=purpose,
        correlation_id=str(consent_id)
    )

def audit_consent_approved(citizen_id, target_form, approved_fields, consent_id):
    return log_audit_event(
        actor_type='citizen',
        actor_id=citizen_id,
        action='consent_approved',
        citizen_id=citizen_id,
        target_form=target_form,
        fields_affected={'approved_fields': approved_fields},
        correlation_id=str(consent_id)
    )

def audit_consent_revoked(citizen_id, target_form, reason, consent_id):
    return log_audit_event(
        actor_type='citizen',
        actor_id=citizen_id,
        action='consent_revoked',
        citizen_id=citizen_id,
        target_form=target_form,
        fields_affected={'reason': reason},
        correlation_id=str(consent_id)
    )

def audit_prefill_generated(citizen_id, target_form, mapped_fields_count, consent_id):
    return log_audit_event(
        actor_type='system',
        actor_id='prefill_engine',
        action='prefill_generated',
        citizen_id=citizen_id,
        target_form=target_form,
        fields_affected={'mapped_fields': mapped_fields_count},
        correlation_id=str(consent_id)
    )

def audit_submission_created(citizen_id, target_form, submission_id):
    return log_audit_event(
        actor_type='citizen',
        actor_id=citizen_id,
        action='submission_created',
        citizen_id=citizen_id,
        target_form=target_form,
        correlation_id=str(submission_id)
    )

def audit_status_changed(officer_id, citizen_id, target_form, new_status, submission_id):
    return log_audit_event(
        actor_type='officer',
        actor_id=officer_id,
        action='status_changed',
        citizen_id=citizen_id,
        target_form=target_form,
        fields_affected={'status': new_status},
        correlation_id=str(submission_id)
    )