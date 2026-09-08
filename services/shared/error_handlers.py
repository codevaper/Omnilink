"""
OmniLink Shared Error Handlers
Import this in any Flask service for consistent error handling
"""

from flask import jsonify, request
import logging
import traceback

logger = logging.getLogger("omnilink")

# ── ERROR RESPONSE TEMPLATES ──────────────────
ERROR_TEMPLATES = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    503: "Service Unavailable",
}


def register_error_handlers(app):
    """Register all error handlers on a Flask app."""
    
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            "error": ERROR_TEMPLATES[400],
            "message": str(e.description) if hasattr(e, 'description') else "Invalid request.",
            "status": 400,
            "service": app.name,
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({
            "error": ERROR_TEMPLATES[401],
            "message": "Authentication required.",
            "status": 401,
            "service": app.name,
        }), 401
    
    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({
            "error": ERROR_TEMPLATES[403],
            "message": "Insufficient permissions.",
            "status": 403,
            "service": app.name,
        }), 403
    
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "error": ERROR_TEMPLATES[404],
            "message": "Resource not found.",
            "path": request.path,
            "status": 404,
            "service": app.name,
        }), 404
    
    @app.errorhandler(409)
    def conflict(e):
        return jsonify({
            "error": ERROR_TEMPLATES[409],
            "message": str(e.description) if hasattr(e, 'description') else "Resource conflict.",
            "status": 409,
            "service": app.name,
        }), 409
    
    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({
            "error": ERROR_TEMPLATES[422],
            "message": str(e.description) if hasattr(e, 'description') else "Validation failed.",
            "status": 422,
            "service": app.name,
        }), 422
    
    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({
            "error": ERROR_TEMPLATES[429],
            "message": "Rate limit exceeded. Please try again later.",
            "status": 429,
            "service": app.name,
        }), 429
    
    @app.errorhandler(500)
    def internal_error(e):
        logger.error("Internal server error: %s", traceback.format_exc())
        return jsonify({
            "error": ERROR_TEMPLATES[500],
            "message": "An unexpected error occurred. Please try again.",
            "status": 500,
            "service": app.name,
            "request_id": request.headers.get("X-Request-ID", "unknown"),
        }), 500
    
    @app.errorhandler(503)
    def service_unavailable(e):
        return jsonify({
            "error": ERROR_TEMPLATES[503],
            "message": "Service temporarily unavailable. Please retry.",
            "status": 503,
            "service": app.name,
        }), 503
    
    @app.errorhandler(Exception)
    def handle_unexpected(e):
        logger.error("Unexpected error: %s", traceback.format_exc())
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred.",
            "status": 500,
            "service": app.name,
        }), 500
    
    return app