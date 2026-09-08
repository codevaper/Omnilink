"""
RBAC Middleware for OmniLink Services
Import this in any service to enforce role-based access
"""

from functools import wraps
from flask import request, jsonify
import jwt
import os

JWT_SECRET = os.getenv("JWT_SECRET", "omnilink-dev-secret-key-change-in-production")


def verify_token(token: str) -> dict:
    """Verify JWT token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise Exception("Token has expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")


def get_token_from_request():
    """Extract token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    return auth_header.replace("Bearer ", "")


def require_role(*allowed_roles):
    """Decorator to require specific role(s)."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_from_request()
            
            if not token:
                return jsonify({
                    "error": "Authentication required."
                }), 401
            
            try:
                payload = verify_token(token)
            except Exception as e:
                return jsonify({"error": str(e)}), 401
            
            if payload["role"] not in allowed_roles:
                return jsonify({
                    "error": "Insufficient permissions.",
                    "required_roles": list(allowed_roles),
                    "your_role": payload["role"],
                }), 403
            
            # Add user info to request context
            request.user = payload
            return f(*args, **kwargs)
        
        return wrapper
    return decorator


def require_citizen(f):
    """Require citizen role."""
    return require_role("citizen")(f)


def require_officer(f):
    """Require officer or admin role."""
    return require_role("officer", "admin")(f)


def require_admin(f):
    """Require admin role."""
    return require_role("admin")(f)


def get_current_user():
    """Get current user from request context (after require_role)."""
    return getattr(request, "user", None)