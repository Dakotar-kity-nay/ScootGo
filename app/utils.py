import math
from datetime import datetime
from functools import wraps
from flask import jsonify, session
from .models import Scooter

def now():
    return datetime.utcnow()

def login_required(f):
    @wraps(f)
    def _wrap(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "auth_required"}), 401
        return f(*args, **kwargs)
    return _wrap

def is_reserved_active(scooter: Scooter) -> bool:
    return scooter.reserved_by is not None and scooter.reserved_until and scooter.reserved_until > now()

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    dp = math.radians(lat2 - lat1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def compute_price_uah(duration_sec, distance_km):
    # Тариф MVP:
    # - розблокування 10 грн
    # - 3 грн/хв
    # - 2 грн/км
    unlock = 10
    per_min = 3
    per_km = 2
    minutes = math.ceil(duration_sec / 60)
    price = unlock + per_min * minutes + per_km * round(distance_km, 2)
    return int(price)
