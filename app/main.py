import random
from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from . import db
from .models import Scooter

main_bp = Blueprint("main", __name__)

@main_bp.get("/")
def index():
    return render_template("index.html")

@main_bp.get("/init_db")
def init_db():
    db.create_all()
    if Scooter.query.count() == 0:
        base_lat, base_lng = 50.4501, 30.5234  # Київ
        for i in range(20):
            lat = base_lat + random.uniform(-0.02, 0.02)
            lng = base_lng + random.uniform(-0.03, 0.03)
            db.session.add(Scooter(
                code=f"SCT-{1000+i}",
                lat=lat, lng=lng, battery=random.randint(55,100),
                is_locked=True, is_active=True
            ))
        db.session.commit()
    return redirect(url_for("main.index"))

@main_bp.get("/admin/seed")
def admin_seed():
    from .models import Scooter
    from . import db
    lat = float(request.args.get("lat", "50.4501"))
    lng = float(request.args.get("lng", "30.5234"))
    n   = int(request.args.get("n", "20"))
    for i in range(n):
        db.session.add(Scooter(
            code=f"SCT-DEMO-{random.randint(10000,99999)}",
            lat=lat + random.uniform(-0.01, 0.01),     # ~±1.1 км
            lng=lng + random.uniform(-0.015, 0.015),   # ~±1.1 км
            battery=random.randint(60,100),
            is_locked=True,
            is_active=True
        ))
    db.session.commit()
    return jsonify(ok=True, seeded=n, center=[lat,lng])
