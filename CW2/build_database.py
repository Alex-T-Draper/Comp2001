from datetime import datetime
from config import app, db
from models import User, Trail, Feature, TrailFeature, LocationPoint, TrailLocationPt

# Sample data
USERS_TRAILS = [
    {
        "email": "grace@plymouth.ac.uk",
        "role": "admin",
        "trails": [
            {
                "Trail_name": "Forest Walk",
                "Trail_Summary": "A peaceful trail through the forest.",
                "Trail_Description": "Great spot to see deer early morning!",
                "Difficulty": "Moderate",
                "Location": "Dartmoor Forest",
                "Length": 5.2,
                "Elevation_gain": 200,
                "Route_type": "Loop",
                "features": ["Deer Watching", "Rocky Path"],
                "locations": [
                    {"Latitude": 50.123, "Longitude": -3.789, "Description": "Trailhead"},
                    {"Latitude": 50.124, "Longitude": -3.790, "Description": "Deer Spot"},
                ],
            },
            {
                "Trail_name": "River Walk",
                "Trail_Summary": "A scenic walk along the river.",
                "Trail_Description": "Great for spotting birds and wildflowers.",
                "Difficulty": "Easy",
                "Location": "Tavy Valley",
                "Length": 3.8,
                "Elevation_gain": 50,
                "Route_type": "Out & Back",
                "features": ["Bird Watching", "Waterfront"],
                "locations": [
                    {"Latitude": 50.135, "Longitude": -3.754, "Description": "River Bridge"},
                    {"Latitude": 50.136, "Longitude": -3.755, "Description": "Picnic Spot"},
                ],
            },
        ],
    },
    {
        "email": "tim@plymouth.ac.uk",
        "role": "user",
        "trails": [
            {
                "Trail_name": "Coastal Path",
                "Trail_Summary": "A rugged path along the coastline.",
                "Trail_Description": "Challenging terrain with breathtaking views.",
                "Difficulty": "Hard",
                "Location": "South Devon Coast",
                "Length": 12.5,
                "Elevation_gain": 400,
                "Route_type": "Point to Point",
                "features": ["Cliffs", "Sea Views", "Historical Sites"],
                "locations": [
                    {"Latitude": 50.245, "Longitude": -3.875, "Description": "Starting Point"},
                    {"Latitude": 50.255, "Longitude": -3.895, "Description": "Lighthouse"},
                    {"Latitude": 50.265, "Longitude": -3.915, "Description": "End Point"},
                ],
            }
        ],
    },
    {
        "email": "ada@plymouth.ac.uk",
        "role": "user",
        "trails": [
            {
                "Trail_name": "Mountain Loop",
                "Trail_Summary": "A challenging hike with stunning views.",
                "Trail_Description": "Bring proper hiking boots!",
                "Difficulty": "Hard",
                "Location": "Exmoor National Park",
                "Length": 15.0,
                "Elevation_gain": 800,
                "Route_type": "Loop",
                "features": ["Panoramic Views", "Wildlife"],
                "locations": [
                    {"Latitude": 51.123, "Longitude": -3.789, "Description": "Mountain Base"},
                    {"Latitude": 51.125, "Longitude": -3.790, "Description": "Summit"},
                    {"Latitude": 51.128, "Longitude": -3.785, "Description": "Lake View"},
                ],
            },
            {
                "Trail_name": "Woodland Stroll",
                "Trail_Summary": "An easy trail through lush woodlands.",
                "Trail_Description": "Great for families and kids.",
                "Difficulty": "Easy",
                "Location": "Haldon Forest",
                "Length": 2.5,
                "Elevation_gain": 100,
                "Route_type": "Loop",
                "features": ["Shaded Path", "Wildflowers"],
                "locations": [
                    {"Latitude": 50.680, "Longitude": -3.515, "Description": "Visitor Center"},
                    {"Latitude": 50.682, "Longitude": -3.516, "Description": "Play Area"},
                ],
            },
        ],
    },
]

with app.app_context():
    db.drop_all()
    db.create_all()
    print("Tables created successfully!")

    for user_data in USERS_TRAILS:
        # Create the user
        new_user = User(
            Email_address=user_data["email"],
            Role=user_data["role"],
            timestamp=datetime.now()
        )
        db.session.add(new_user)
        db.session.flush() 

        # Insert each Trail
        for trail_data in user_data["trails"]:
            new_trail = Trail(
                Trail_name=trail_data["Trail_name"],
                Trail_Summary=trail_data["Trail_Summary"],
                Trail_Description=trail_data["Trail_Description"],
                Difficulty=trail_data["Difficulty"],
                Location=trail_data["Location"],
                Length=trail_data["Length"],
                Elevation_gain=trail_data["Elevation_gain"],
                Route_type=trail_data["Route_type"],
                OwnerID=new_user.UserID, 
                timestamp=datetime.now()
            )
            db.session.add(new_trail)
            db.session.flush()  

            # Insert bridging rows for each Feature
            for feat_name in trail_data["features"]:
                # Check if this feature already exists
                existing_feat = db.session.query(Feature).filter_by(Trail_Feature=feat_name).first()
                if not existing_feat:
                    existing_feat = Feature(Trail_Feature=feat_name)
                    db.session.add(existing_feat)
                    db.session.flush()

                # Insert bridging row in cw2_trail_feature
                new_trail_feature = TrailFeature(
                    TrailID=new_trail.TrailID,
                    Trail_FeatureID=existing_feat.Trail_FeatureID
                )
                db.session.add(new_trail_feature)

            # Insert location points & bridging rows
            for i, loc_data in enumerate(trail_data["locations"]):
                new_loc = LocationPoint(
                    Latitude=loc_data["Latitude"],
                    Longitude=loc_data["Longitude"],
                    Description=loc_data["Description"],
                    timestamp=datetime.now()
                )
                db.session.add(new_loc)
                db.session.flush()

                # Insert bridging row in cw2_trail_location_pt
                new_trail_loc_pt = TrailLocationPt(
                    TrailID=new_trail.TrailID,
                    Location_Point=new_loc.Location_Point,
                    Order_no=i + 1
                )
                db.session.add(new_trail_loc_pt)

    db.session.commit()
    print("Database initialized and populated with sample data.")
