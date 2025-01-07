# app.py

from flask import render_template, jsonify
import config
from models import Trail, Feature, TrailFeature, LocationPoint, TrailLocationPt
from config import db

config.connex_app.add_api(config.basedir / "swagger.yml")

app = config.app

@app.route("/")
def home():
    trails = Trail.query.all()
    enriched_trails = []

    for trail in trails:
        # Fetch features
        features = (
            db.session.query(Feature.Trail_Feature)
            .join(TrailFeature, TrailFeature.Trail_FeatureID == Feature.Trail_FeatureID)
            .filter(TrailFeature.TrailID == trail.TrailID)
            .all()
        )
        feature_list = [feature.Trail_Feature for feature in features]

        # Fetch location points
        location_points = (
            db.session.query(LocationPoint, TrailLocationPt.Order_no)
            .join(TrailLocationPt, TrailLocationPt.Location_Point == LocationPoint.Location_Point)
            .filter(TrailLocationPt.TrailID == trail.TrailID)
            .order_by(TrailLocationPt.Order_no)
            .all()
        )
        location_list = [
            {
                "Order_no": lp.Order_no,
                "Latitude": lp.LocationPoint.Latitude,
                "Longitude": lp.LocationPoint.Longitude,
                "Description": lp.LocationPoint.Description,
            }
            for lp in location_points
        ]

        # Enrich trail data
        enriched_trails.append({
            "Trail_name": trail.Trail_name,
            "Trail_Summary": trail.Trail_Summary,
            "Trail_Description": trail.Trail_Description,
            "Difficulty": trail.Difficulty,
            "Location": trail.Location,
            "Length": trail.Length,
            "Elevation_gain": trail.Elevation_gain,
            "Route_type": trail.Route_type,
            "Features": feature_list,
            "LocationPoints": location_list,
        })

    return render_template("home.html", trails=enriched_trails)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
