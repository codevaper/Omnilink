"""
OmniLink Shared Validators
Input validation helpers for all services
"""

import re
from datetime import datetime


def validate_citizen_id(citizen_id):
    """Validate citizen ID format: CIT-XXXXXX."""
    if not citizen_id:
        return False, "citizen_id is required."
    
    if not re.match(r"^CIT-\d{6}$", citizen_id.upper()):
        return False, "Invalid citizen_id format. Expected CIT-XXXXXX."
    
    return True, None


def validate_mobile_number(mobile):
    """Validate Indian mobile number."""
    if not mobile:
        return False, "mobile_number is required."
    
    if not re.match(r"^[6-9]\d{9}$", str(mobile)):
        return False, "Mobile number must be 10 digits starting with 6-9."
    
    return True, None


def validate_email(email):
    """Validate email format."""
    if not email:
        return False, "email is required."
    
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return False, "Invalid email format."
    
    return True, None


def validate_pan(pan):
    """Validate PAN format: ABCDE1234F."""
    if not pan:
        return False, "pan_number is required."
    
    if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan.upper()):
        return False, "PAN must match format ABCDE1234F."
    
    return True, None


def validate_ifsc(ifsc):
    """Validate IFSC format: ABCD0123456."""
    if not ifsc:
        return False, "bank_ifsc is required."
    
    if not re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", ifsc.upper()):
        return False, "IFSC must match format ABCD0123456."
    
    return True, None


def validate_bank_account(account):
    """Validate bank account number."""
    if not account:
        return False, "bank_account is required."
    
    if not re.match(r"^\d{9,18}$", str(account)):
        return False, "Bank account must be 9-18 digits."
    
    return True, None


def validate_date_of_birth(dob):
    """Validate date of birth."""
    if not dob:
        return False, "date_of_birth is required."
    
    try:
        parsed = datetime.fromisoformat(str(dob))
    except ValueError:
        return False, "date_of_birth must be in ISO format (YYYY-MM-DD)."
    
    if parsed > datetime.now():
        return False, "date_of_birth cannot be in the future."
    
    return True, None


def validate_request_data(data, required_fields):
    """Validate that required fields exist in request data."""
    if not isinstance(data, dict):
        return False, "Request body must be a JSON object."
    
    missing = [field for field in required_fields if field not in data]
    
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    
    return True, None