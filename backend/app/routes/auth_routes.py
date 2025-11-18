# backend/app/routes/auth_routes.py

from flask import Blueprint, request, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import IntegrityError

from app.database import db
from app.models.models import AppUser

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def serialize_user(user: AppUser):
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return AppUser.query.get(user_id)


def require_admin():
    """Utility to check admin-only access inside admin endpoints."""
    user = get_current_user()
    return bool(user and user.role == "admin")


# -----------------------------------------------------------------------------
# Register (creator / normal user)
# -----------------------------------------------------------------------------
@auth_bp.post("/register")
def register():
    """
    Register a normal user (creator).
    Admins can be set manually in DB for now (update app_user.role to 'admin').
    """
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    display_name = (data.get("display_name") or "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Basic length guard
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    try:
        user = AppUser(
            email=email,
            display_name=display_name or None,
            password_hash=generate_password_hash(password),
            role="creator",  # 🔒 ignore 'role' from client for security
        )
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Email already registered"}), 409

    # Optionally auto-login newly registered user
    session["user_id"] = str(user.id)
    session["role"] = user.role

    return jsonify({"user": serialize_user(user)}), 201


# -----------------------------------------------------------------------------
# Login
# -----------------------------------------------------------------------------
@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = AppUser.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    # For "real" users we store hashed passwords.
    # Smoke-test users (created in job_routes) use plain text; we keep a fallback:
# For "real" users we store hashed passwords.
# Smoke-test users (created in job_routes) use plain text; we keep a fallback:
# Universal password check (supports pbkdf2, scrypt, etc.)
    try:
        password_ok = check_password_hash(user.password_hash, password)
    except Exception:
        # Fallback for smoke-test users with plain-text pwd
        password_ok = (user.password_hash == password)



    if not password_ok:
        return jsonify({"error": "Invalid email or password"}), 401

    # Store session
    session["user_id"] = str(user.id)
    session["role"] = user.role

    return jsonify({"user": serialize_user(user)}), 200


# -----------------------------------------------------------------------------
# Who am I?
# -----------------------------------------------------------------------------
@auth_bp.get("/me")
def me():
    user = get_current_user()
    if not user:
        return jsonify({"user": None})
    return jsonify({"user": serialize_user(user)})


# -----------------------------------------------------------------------------
# Logout
# -----------------------------------------------------------------------------
@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


# -----------------------------------------------------------------------------
# Admin-only protected check (optional API endpoint)
# -----------------------------------------------------------------------------
@auth_bp.get("/admin/check")
def admin_check():
    if not require_admin():
        return jsonify({"error": "Admin privileges required"}), 403
    return jsonify({"status": "ok", "admin": True})
