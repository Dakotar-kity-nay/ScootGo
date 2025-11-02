from datetime import datetime
from . import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    balance_uah = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Scooter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    battery = db.Column(db.Integer, default=100)     # %
    is_locked = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    reserved_by = db.Column(db.Integer, nullable=True)
    reserved_until = db.Column(db.DateTime, nullable=True)

class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    scooter_id = db.Column(db.Integer, db.ForeignKey("scooter.id"), nullable=False)

    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)

    start_lat = db.Column(db.Float, nullable=False)
    start_lng = db.Column(db.Float, nullable=False)
    end_lat = db.Column(db.Float, nullable=True)
    end_lng = db.Column(db.Float, nullable=True)

    duration_sec = db.Column(db.Integer, nullable=True)
    distance_km = db.Column(db.Float, nullable=True)
    price_uah = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default="started")
