from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from .models import User, Trip, Scooter
from .utils import login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api")

@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    pwd = data.get("password") or ""
    if not email or not pwd:
        return jsonify(ok=False, error="email_and_password_required"), 400
    if User.query.filter_by(email=email).first():
        return jsonify(ok=False, error="email_taken"), 409
    u = User(email=email, password_hash=generate_password_hash(pwd))
    db.session.add(u)
    db.session.commit()
    session["user_id"] = u.id
    return jsonify(ok=True)

@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    pwd = data.get("password") or ""
    u = User.query.filter_by(email=email).first()
    if not u or not check_password_hash(u.password_hash, pwd):
        return jsonify(ok=False, error="invalid_credentials"), 401
    session["user_id"] = u.id
    return jsonify(ok=True)

@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify(ok=True)

@auth_bp.get("/me")
def me():
    uid = session.get("user_id")
    if not uid:
        return jsonify(ok=False, error="not_logged"), 401
    u = User.query.get(uid)
    t = Trip.query.filter_by(user_id=uid, status="started").first()

    active_trip = None
    if t:
        sc = Scooter.query.get(t.scooter_id)
        active_trip = {
            "id": t.id,
            "scooter_id": t.scooter_id,
            "scooter_code": sc.code if sc else f"#{t.scooter_id}",
            "started_at": t.started_at.isoformat() + "Z",
            "start_lat": t.start_lat,
            "start_lng": t.start_lng
        }

    return jsonify(
        ok=True,
        user={"id": u.id, "email": u.email, "balance_uah": u.balance_uah},
        active_trip=active_trip
    )


@auth_bp.post("/topup")
@login_required
def topup():
    amt = (request.get_json() or {}).get("amount_uah")
    try:
        amt = int(amt)
    except:
        return jsonify(ok=False, error="bad_amount"), 400
    if amt <= 0:
        return jsonify(ok=False, error="amount_must_be_positive"), 400
    u = User.query.get(session["user_id"])
    u.balance_uah += amt
    db.session.commit()
    return jsonify(ok=True, balance_uah=u.balance_uah)
