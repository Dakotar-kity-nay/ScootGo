from flask import Blueprint, request, jsonify, session
from . import db
from .models import Trip, User, Scooter
from .utils import login_required, is_reserved_active, haversine_km, compute_price_uah, now

trips_bp = Blueprint("trips", __name__, url_prefix="/api")

@trips_bp.post("/start_trip")
@login_required
def start_trip():
    data = request.get_json() or {}
    sid = data.get("scooter_id")
    lat = float(data.get("lat"))
    lng = float(data.get("lng"))

    u = User.query.get(session["user_id"])
    s = Scooter.query.get(sid)
    if not s or not s.is_active:
        return jsonify(ok=False, error="not_found"), 404
    if not s.is_locked:
        return jsonify(ok=False, error="already_in_use"), 409
    if is_reserved_active(s) and s.reserved_by != u.id:
        return jsonify(ok=False, error="reserved_by_other"), 409
    if u.balance_uah < 50:
        return jsonify(ok=False, error="insufficient_balance_min_50"), 402

    s.is_locked = False
    s.reserved_by = None
    s.reserved_until = None

    trip = Trip(
        user_id=u.id, scooter_id=s.id, started_at=now(),
        start_lat=lat, start_lng=lng, status="started"
    )
    db.session.add(trip)
    db.session.commit()
    return jsonify(ok=True, trip_id=trip.id)

@trips_bp.post("/end_trip")
@login_required
def end_trip():
    data = request.get_json() or {}
    tid = data.get("trip_id")
    lat = float(data.get("lat"))
    lng = float(data.get("lng"))

    trip = Trip.query.get(tid)
    if not trip or trip.user_id != session["user_id"] or trip.status != "started":
        return jsonify(ok=False, error="trip_not_found_or_not_active"), 404

    s = Scooter.query.get(trip.scooter_id)
    u = User.query.get(session["user_id"])

    trip.ended_at = now()
    trip.end_lat = lat
    trip.end_lng = lng
    trip.duration_sec = max(1, int((trip.ended_at - trip.started_at).total_seconds()))
    trip.distance_km = round(haversine_km(trip.start_lat, trip.start_lng, lat, lng), 3)
    trip.price_uah = compute_price_uah(trip.duration_sec, trip.distance_km)
    trip.status = "ended"

    if u.balance_uah < trip.price_uah:
        pass
    u.balance_uah = max(0, u.balance_uah - trip.price_uah)

    s.lat, s.lng = lat, lng
    s.is_locked = True
    s.battery = max(0, s.battery - min(20, int(trip.duration_sec/60)))

    db.session.commit()
    return jsonify(ok=True, receipt={
        "trip_id": trip.id,
        "duration_sec": trip.duration_sec,
        "distance_km": trip.distance_km,
        "price_uah": trip.price_uah
    })
