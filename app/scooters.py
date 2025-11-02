from flask import Blueprint, request, jsonify, session
from .models import Scooter, Trip
from .utils import is_reserved_active, haversine_km, login_required, now
from . import db

scooters_bp = Blueprint("scooters", __name__, url_prefix="/api")

@scooters_bp.get("/scooters")
def scooters():
    # 1) безпечний парсинг параметрів
    try:
        lat = float(request.args.get("lat", "50.4501"))
        lng = float(request.args.get("lng", "30.5234"))
        radius = float(request.args.get("radius_km", "1.0"))
    except ValueError:
        return jsonify(ok=False, error="bad_coords"), 400

    uid = session.get("user_id")

    # 2) забираємо всі активні самокати та активні трипи (один запит на тип)
    all_scooters = Scooter.query.filter_by(is_active=True).all()
    active_trips = {t.scooter_id: t for t in Trip.query.filter_by(status="started").all()}

    # 3) формуємо список відповіді
    items = []
    for s in all_scooters:
        # визначення статусу
        t = active_trips.get(s.id)
        if t:
            status = "in_trip_me" if uid and t.user_id == uid else "in_trip_other"
        else:
            if is_reserved_active(s):
                status = "reserved_me" if uid and s.reserved_by == uid else "reserved_other"
            else:
                status = "available"

        # фільтр по радіусу (radius<=0 показуємо все)
        d = haversine_km(lat, lng, s.lat, s.lng)
        if radius <= 0 or d <= radius:
            items.append({
                "id": s.id,
                "code": s.code,
                "lat": s.lat,
                "lng": s.lng,
                "battery": s.battery,
                "status": status,
                "reserved_until": s.reserved_until.isoformat() + "Z" if s.reserved_until else None
            })

    # 4) ГАРАНТОВАНО повертаємо JSON
    return jsonify(ok=True, items=items)


@scooters_bp.post("/reserve")
@login_required
def reserve():
    data = request.get_json() or {}
    sid = data.get("scooter_id")
    s = Scooter.query.get(sid)
    if not s or not s.is_active:
        return jsonify(ok=False, error="not_found"), 404
    if not s.is_locked:
        return jsonify(ok=False, error="already_in_use"), 409
    if is_reserved_active(s) and s.reserved_by != session["user_id"]:
        return jsonify(ok=False, error="reserved_by_other"), 409

    from datetime import timedelta
    s.reserved_by = session["user_id"]
    s.reserved_until = now() + timedelta(minutes=4)
    db.session.commit()
    return jsonify(ok=True, reserved_until=s.reserved_until.isoformat() + "Z")
