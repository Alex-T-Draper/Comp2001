from datetime import datetime
from math import radians, cos, sin, sqrt, atan2
from flask import make_response, abort, request
from config import db
from models import (
    Trail, trails_schema, trail_schema,
    LocationPoint, location_point_schema, location_points_schema,
    TrailLocationPt, trail_location_pt_schema, Feature, TrailFeature, feature_schema
)
from authentication import require_auth, require_auth_and_role

def get_all_trails():
    # Fetch all trails
    trails = Trail.query.all()
    if not trails:
        abort(404, "No trails found")

    # Return basic trail information
    return [
        {
            "Trail_name": trail.Trail_name,
            "Trail_Summary": trail.Trail_Summary,
            "Trail_Description": trail.Trail_Description,
            "Difficulty": trail.Difficulty,
            "Location": trail.Location,
            "Length": trail.Length,
            "Elevation_gain": trail.Elevation_gain,
            "Route_type": trail.Route_type,
        }
        for trail in trails
    ]

def get_all_trails_details():
    user = require_auth()
    if not user:
        abort(401, "Authentication required.")

    trails = Trail.query.all()
    if not trails:
        abort(404, "No trails found")

    all_trails_with_details = []

    for trail in trails:
        # Fetch associated features
        features = db.session.query(Feature).join(TrailFeature).filter(
            TrailFeature.TrailID == trail.TrailID
        ).all()

        # Fetch associated location points with order numbers
        location_points = db.session.query(LocationPoint, TrailLocationPt.Order_no).join(
            TrailLocationPt, TrailLocationPt.Location_Point == LocationPoint.Location_Point
        ).filter(TrailLocationPt.TrailID == trail.TrailID).order_by(TrailLocationPt.Order_no).all()

        # Format location points
        formatted_location_points = [
            {
                "Location_Point": lp.Location_Point,
                "Latitude": lp.Latitude,
                "Longitude": lp.Longitude,
                "Description": lp.Description,
                "Order_no": order_no,
                "timestamp": lp.timestamp,
            }
            for lp, order_no in location_points
        ]

        # Format features
        formatted_features = [
            {
                "Trail_FeatureID": feature.Trail_FeatureID,
                "Trail_Feature": feature.Trail_Feature,
            }
            for feature in features
        ]

        # Format the trail details
        formatted_trail = {
            "TrailID": trail.TrailID,
            "Trail_name": trail.Trail_name,
            "Trail_Summary": trail.Trail_Summary,
            "Trail_Description": trail.Trail_Description,
            "Difficulty": trail.Difficulty,
            "Location": trail.Location,
            "Length": trail.Length,
            "Elevation_gain": trail.Elevation_gain,
            "Route_type": trail.Route_type,
            "OwnerID": trail.OwnerID,
            "Features": formatted_features,
            "LocationPoints": formatted_location_points,
            "timestamp": trail.timestamp,
        }

        all_trails_with_details.append(formatted_trail)

    return all_trails_with_details


def create_trail():
    user = require_auth_and_role("admin")  # Ensure only admin users can create trails
    if not user:
        abort(403, "Unable to authenticate user.")

    trail_data = request.get_json()
    print("DEBUG: Raw request data:", trail_data)

    if not trail_data:
        print("No trail data received.")
        abort(400, "No data provided or invalid format.")

    # Validate required fields
    required_fields = ["Trail_name", "Location", "Difficulty", "Length"]
    for field in required_fields:
        if not trail_data.get(field):
            abort(400, f"Missing required field: {field}")

    location_points = trail_data.pop("LocationPoints", [])
    if not location_points or len(location_points) == 0:
        abort(400, "At least one location point is required.")

    # Check for duplicate trail name
    trail_name = trail_data.get("Trail_name")
    existing_trail = Trail.query.filter(Trail.Trail_name == trail_name).one_or_none()
    if existing_trail:
        abort(406, f"Trail with name {trail_name} already exists.")

    # Create the trail object (without OwnerID)
    new_trail = trail_schema.load(trail_data, session=db.session)

    # Assign the owner to the trail
    new_trail.OwnerID = user["UserID"]

    # Add the trail to the session
    db.session.add(new_trail)
    db.session.flush()

    # Handle LocationPoints and check distances
    MAX_DISTANCE = 10.0
    location_point_details = []
    for index, loc in enumerate(location_points):
        latitude = loc.get("Latitude")
        longitude = loc.get("Longitude")
        description = loc.get("Description")

        if latitude is None or longitude is None or description is None:
            abort(400, "Each location point must have Latitude, Longitude, and Description.")

        # Check if the location point already exists
        existing_point = LocationPoint.query.filter_by(Latitude=latitude, Longitude=longitude).one_or_none()
        if existing_point:
            location_point_id = existing_point.Location_Point
        else:
            # Validate distances with all existing points in the trail
            for existing_loc in location_point_details:
                distance = calculate_distance(
                    latitude, longitude,
                    existing_loc["Latitude"], existing_loc["Longitude"]
                )
                if distance > MAX_DISTANCE:
                    abort(400, {
                        "detail": f"Location point exceeds the maximum distance of {MAX_DISTANCE} km from another point.",
                        "from": {
                            "Latitude": existing_loc["Latitude"],
                            "Longitude": existing_loc["Longitude"]
                        },
                        "to": {
                            "Latitude": latitude,
                            "Longitude": longitude
                        },
                        "distance_km": round(distance, 2)
                    })

            # Create a new location point
            new_location_point = LocationPoint(
                Latitude=latitude,
                Longitude=longitude,
                Description=description,
                timestamp=datetime.now()
            )
            db.session.add(new_location_point)
            db.session.flush()  # Get the new location point ID
            location_point_id = new_location_point.Location_Point

        # Add the location point to the trail
        new_trail_location = TrailLocationPt(
            TrailID=new_trail.TrailID,
            Location_Point=location_point_id,
            Order_no=index + 1
        )
        db.session.add(new_trail_location)

        # Append details for the response
        location_point_details.append({
            "Location_Point": location_point_id,
            "Latitude": latitude,
            "Longitude": longitude,
            "Description": description,
            "Order_no": index + 1
        })

    db.session.commit()

    # Construct enhanced response
    response_data = trail_schema.dump(new_trail)
    response_data["LocationPoints"] = location_point_details

    return response_data, 201

def get_one_trail(trail_id):
    user = require_auth()
    if not user:
        abort(401, "Authentication required.")
        
    trail = Trail.query.filter(Trail.TrailID == trail_id).one_or_none()
    if trail is not None:
        return trail_schema.dump(trail)
    else:
        abort(404, f"Trail with ID {trail_id} not found")

def update_trail(trail_id):
    user = require_auth_and_role("admin")  
    if not user:
        abort(403, "Unable to authenticate user.")

    trail_data = request.get_json()

    # Fetch the existing trail
    existing_trail = Trail.query.filter(Trail.TrailID == trail_id).one_or_none()
    if not existing_trail:
        abort(404, f"Trail with ID {trail_id} not found.")

    # Update only provided fields
    for key, value in trail_data.items():
        setattr(existing_trail, key, value)

    db.session.commit()
    return trail_schema.dump(existing_trail), 200

def delete_trail(trail_id):
    user = require_auth_and_role("admin")  
    if not user:
        abort(403, "Unable to authenticate user.")

    existing_trail = Trail.query.filter(Trail.TrailID == trail_id).one_or_none()
    if not existing_trail:
        abort(404, f"Trail with ID {trail_id} not found.")

    # Delete associated TrailFeature entries
    TrailFeature.query.filter_by(TrailID=trail_id).delete()

    # Delete associated TrailLocationPt entries
    trail_location_pts = TrailLocationPt.query.filter_by(TrailID=trail_id).all()
    for trail_location_pt in trail_location_pts:
        location_point = LocationPoint.query.filter(LocationPoint.Location_Point == trail_location_pt.Location_Point).one_or_none()
        if location_point:
            # Check if the location point is linked to other trails
            linked_trails_count = TrailLocationPt.query.filter_by(Location_Point=location_point.Location_Point).count()
            if linked_trails_count == 1:
                db.session.delete(location_point)

    db.session.delete(existing_trail)
    db.session.commit()
    return make_response(f"Trail with ID {trail_id} successfully deleted", 200)

def get_location_point(location_point_id):
    user = require_auth()
    if not user:
        abort(401, "Authentication required.")

    location_point = LocationPoint.query.filter(LocationPoint.Location_Point == location_point_id).one_or_none()

    if location_point is not None:
        return location_point_schema.dump(location_point)
    else:
        abort(404, f"Location point with ID {location_point_id} not found")

def get_all_features():
    user = require_auth()
    if not user:
        abort(401, "Authentication required.")

    # Fetch all features from the database
    features = Feature.query.all()
    if not features:
        return {"message": "No features found in the database."}, 200
    
    # Serialize and return features
    return [{"FeatureID": feature.Trail_FeatureID, "Feature": feature.Trail_Feature} for feature in features], 200

def get_feature_by_id(feature_id):
    user = require_auth()
    if not user:
        abort(401, "Authentication required.")

    # Fetch the feature with the given ID
    feature = Feature.query.filter(Feature.Trail_FeatureID == feature_id).one_or_none()
    if not feature:
        abort(404, f"Feature with ID {feature_id} not found.")
    
    # Serialize and return the feature
    return {"FeatureID": feature.Trail_FeatureID, "Feature": feature.Trail_Feature}, 200

def delete_feature_by_id(feature_id):
    user = require_auth_and_role("admin")  
    if not user:
        abort(403, "Unable to authenticate user.")

    # Fetch the feature with the given ID
    feature = Feature.query.filter(Feature.Trail_FeatureID == feature_id).one_or_none()
    if not feature:
        abort(404, f"Feature with ID {feature_id} not found.")

    # Delete all associations in TrailFeature
    TrailFeature.query.filter_by(Trail_FeatureID=feature_id).delete()

    # Delete the feature itself
    db.session.delete(feature)
    db.session.commit()

    return make_response(f"Feature with ID {feature_id} and its associations successfully deleted.", 200)

def get_all_location_points():
    user = require_auth()
    if not user:
        abort(401, "Authentication required.")

    # Query all location points
    location_points = LocationPoint.query.all()

    # Check if any location points exist
    if not location_points:
        abort(404, "No location points found")

    # Return serialized location points
    return location_points_schema.dump(location_points)

def update_location_point(location_point_id):
    user = require_auth_and_role("admin")  
    if not user:
        abort(403, "Unable to authenticate user.")

    # Fetch the existing location point
    location_point = LocationPoint.query.filter(LocationPoint.Location_Point == location_point_id).one_or_none()
    if not location_point:
        abort(404, f"Location point with ID {location_point_id} not found.")

    # Parse the request data
    request_data = request.get_json()
    new_lat = request_data.get("Latitude", location_point.Latitude)
    new_lon = request_data.get("Longitude", location_point.Longitude)
    new_description = request_data.get("Description", location_point.Description)

    # Check if the updated point exceeds 10 km for any associated trail
    MAX_DISTANCE = 10.0
    associated_trails = db.session.query(TrailLocationPt).filter_by(Location_Point=location_point_id).all()

    affected_trails = []  # List to track affected trails

    for trail_loc_pt in associated_trails:
        # Fetch all points in the trail, excluding the current point
        trail_points = db.session.query(LocationPoint).join(TrailLocationPt).filter(
            TrailLocationPt.TrailID == trail_loc_pt.TrailID,
            TrailLocationPt.Location_Point != location_point_id
        ).all()

        # Check distances to all other points in the trail
        for point in trail_points:
            distance = calculate_distance(new_lat, new_lon, point.Latitude, point.Longitude)
            if distance > MAX_DISTANCE:
                affected_trails.append({
                    "TrailID": trail_loc_pt.TrailID,
                    "Distance": round(distance, 2),
                    "Affected_Point_Latitude": point.Latitude,
                    "Affected_Point_Longitude": point.Longitude
                })

    if affected_trails:
        # If there are affected trails, return a detailed error response
        abort(400, {
            "detail": f"Updating this point would cause distances exceeding {MAX_DISTANCE} km.",
            "affected_trails": affected_trails,
            "status": 400,
            "title": "Bad Request",
            "type": "about:blank"
        })

    # Update the location point details
    location_point.Latitude = new_lat
    location_point.Longitude = new_lon
    location_point.Description = new_description
    location_point.timestamp = datetime.now()

    db.session.commit()

    return location_point_schema.dump(location_point), 200

def get_point_locations_for_trail(trail_id):
    user = require_auth()
    if not user:
        abort(401, "Authentication required.")

    # Check if the trail exists
    trail = Trail.query.filter(Trail.TrailID == trail_id).one_or_none()
    if not trail:
        abort(404, f"Trail with ID {trail_id} not found.")

    # Query all location points associated with the trail
    trail_location_points = db.session.query(LocationPoint).join(TrailLocationPt).filter(
        TrailLocationPt.TrailID == trail_id
    ).order_by(TrailLocationPt.Order_no).all()

    # Return the location points as JSON
    return location_points_schema.dump(trail_location_points)

def add_location_point():
    user = require_auth_and_role("admin")  
    if not user:
        abort(403, "Unable to authenticate user.")

    # Parse request data
    request_data = request.get_json()
    if not request_data:
        abort(400, "No data provided.")

    # Validate required fields
    required_fields = ["Latitude", "Longitude", "Description"]
    for field in required_fields:
        if not request_data.get(field):
            abort(400, f"Missing required field: {field}")

    # Extract data
    latitude = request_data["Latitude"]
    longitude = request_data["Longitude"]
    description = request_data["Description"]

    # Check if the location point already exists
    existing_point = LocationPoint.query.filter_by(Latitude=latitude, Longitude=longitude).one_or_none()
    if existing_point:
        return location_point_schema.dump(existing_point), 200 

    # Create a new location point
    new_point = LocationPoint(
        Latitude=latitude,
        Longitude=longitude,
        Description=description,
        timestamp=datetime.now()
    )
    db.session.add(new_point)
    db.session.commit()

    return location_point_schema.dump(new_point), 201

def delete_location_point(location_point_id):
    user = require_auth_and_role("admin")  
    if not user:
        abort(403, "Unable to authenticate user.")

    # Fetch the location point
    location_point = LocationPoint.query.filter(LocationPoint.Location_Point == location_point_id).one_or_none()
    if not location_point:
        abort(404, f"Location point with ID {location_point_id} not found.")

    # Check if the location point is linked to any trail
    linked_trails_count = TrailLocationPt.query.filter_by(Location_Point=location_point_id).count()
    if linked_trails_count > 0:
        abort(400, f"Location point ID {location_point_id} is still associated with one or more trails.")

    # Delete the location point
    db.session.delete(location_point)
    db.session.commit()

    return {"message": f"Location point with ID {location_point_id} successfully deleted."}, 200


def update_trail_location_point(trail_id, location_point_id):
    user = require_auth_and_role("admin")  
    if not user:
        abort(403, "Unable to authenticate user.")

    # Fetch the trail
    trail = Trail.query.filter(Trail.TrailID == trail_id).one_or_none()
    if not trail:
        abort(404, f"Trail with ID {trail_id} not found.")

    # Fetch the location point relationship
    trail_location = TrailLocationPt.query.filter_by(
        TrailID=trail_id, Location_Point=location_point_id
    ).one_or_none()
    if not trail_location:
        abort(404, f"Location point with ID {location_point_id} not found in trail ID {trail_id}.")

    # Parse the request data
    request_data = request.get_json()
    new_order_no = request_data.get("Order_no")
    if not new_order_no:
        abort(400, "Order_no is required.")

    # Validate the new order number
    max_order_no = db.session.query(db.func.max(TrailLocationPt.Order_no)).filter_by(TrailID=trail_id).scalar() or 0
    if new_order_no < 1 or new_order_no > max_order_no:
        abort(400, f"Order_no must be between 1 and {max_order_no}.")

    # Adjust order numbers if necessary
    current_order_no = trail_location.Order_no
    if new_order_no != current_order_no:
        if new_order_no > current_order_no:
            db.session.query(TrailLocationPt).filter(
                TrailLocationPt.TrailID == trail_id,
                TrailLocationPt.Order_no > current_order_no,
                TrailLocationPt.Order_no <= new_order_no
            ).update({"Order_no": TrailLocationPt.Order_no - 1}, synchronize_session=False)
        elif new_order_no < current_order_no:
            db.session.query(TrailLocationPt).filter(
                TrailLocationPt.TrailID == trail_id,
                TrailLocationPt.Order_no >= new_order_no,
                TrailLocationPt.Order_no < current_order_no
            ).update({"Order_no": TrailLocationPt.Order_no + 1}, synchronize_session=False)

        trail_location.Order_no = new_order_no

    db.session.commit()

    return trail_location_pt_schema.dump(trail_location), 200

def add_location_point_to_trail(trail_id, location_point_id):
    user = require_auth_and_role("admin")  
    if not user:
        abort(403, "Unable to authenticate user.")

    # Fetch the trail
    trail = Trail.query.filter(Trail.TrailID == trail_id).one_or_none()
    if not trail:
        abort(404, f"Trail with ID {trail_id} not found.")

    # Fetch the location point
    location_point = LocationPoint.query.filter(LocationPoint.Location_Point == location_point_id).one_or_none()
    if not location_point:
        abort(404, f"Location point with ID {location_point_id} not found.")

    # Check if the location point is already associated with the trail
    existing_relation = TrailLocationPt.query.filter_by(
        TrailID=trail_id,
        Location_Point=location_point_id
    ).one_or_none()
    if existing_relation:
        abort(400, f"Location point ID {location_point_id} is already associated with trail ID {trail_id}.")

    # Fetch the optional Order_no from query parameters
    order_no = request.args.get("Order_no", type=int)  # Optional, defaults to None

    # Determine the maximum existing order number for the trail
    max_order_no = db.session.query(db.func.max(TrailLocationPt.Order_no)).filter_by(TrailID=trail_id).scalar() or 0

    if order_no:
        # Validate the provided Order_no
        if order_no < 1 or order_no > max_order_no + 1:
            abort(400, f"Order_no must be between 1 and {max_order_no + 1}.")

        # Adjust order numbers for insertion
        db.session.query(TrailLocationPt).filter(
            TrailLocationPt.TrailID == trail_id,
            TrailLocationPt.Order_no >= order_no
        ).update({"Order_no": TrailLocationPt.Order_no + 1}, synchronize_session=False)
    else:
        # Default to the next available position
        order_no = max_order_no + 1

    # Validate distances with all existing points
    MAX_DISTANCE = 10.0  # Maximum allowable distance in km
    existing_points = db.session.query(LocationPoint).join(TrailLocationPt).filter(
        TrailLocationPt.TrailID == trail_id
    ).all()

    for existing_point in existing_points:
        distance = calculate_distance(
            existing_point.Latitude, existing_point.Longitude,
            location_point.Latitude, location_point.Longitude
        )
        if distance > MAX_DISTANCE:
            abort(400, f"Distance to an existing point exceeds {MAX_DISTANCE} km: {distance:.2f} km.")

    # Create the trail-location relationship
    new_trail_location_pt = TrailLocationPt(
        TrailID=trail_id,
        Location_Point=location_point_id,
        Order_no=order_no,
    )
    db.session.add(new_trail_location_pt)
    db.session.commit()

    return location_point_schema.dump(location_point), 201

def delete_location_point_from_trail(trail_id, location_point_id):
    user = require_auth_and_role("admin")  
    if not user:
        abort(403, "Unable to authenticate user.")

    # Check if the trail exists
    trail = Trail.query.filter(Trail.TrailID == trail_id).one_or_none()
    if not trail:
        abort(404, f"Trail with ID {trail_id} not found.")

    # Fetch the location point relationship
    trail_location_pt = TrailLocationPt.query.filter_by(
        TrailID=trail_id, Location_Point=location_point_id
    ).one_or_none()
    if not trail_location_pt:
        abort(404, f"Location point with ID {location_point_id} not found in trail ID {trail_id}.")

    # Check if the trail has at least one other location point
    location_count = TrailLocationPt.query.filter_by(TrailID=trail_id).count()
    if location_count <= 1:
        abort(400, "A trail must have at least one location point.")

    # Delete the relationship
    db.session.delete(trail_location_pt)

    # Reorder remaining points in the trail
    remaining_points = TrailLocationPt.query.filter_by(TrailID=trail_id).order_by(TrailLocationPt.Order_no).all()
    for index, point in enumerate(remaining_points):
        point.Order_no = index + 1

    db.session.commit()

    return make_response(f"Location point with ID {location_point_id} successfully removed from trail {trail_id}", 200)

def get_features_for_trail(trail_id):
    user = require_auth()
    if not user:
        abort(401, "Authentication required.")

    # Check if the trail exists
    trail = Trail.query.filter(Trail.TrailID == trail_id).one_or_none()
    if not trail:
        abort(404, f"Trail with ID {trail_id} not found.")

    # Fetch the features associated with the trail
    features = db.session.query(Feature).join(TrailFeature).filter(
        TrailFeature.TrailID == trail_id
    ).all()

    # Return the features as JSON
    return [{"FeatureID": feature.Trail_FeatureID, "Feature": feature.Trail_Feature} for feature in features], 200

def add_feature_to_trail(trail_id, feature_id):
    user = require_auth_and_role("admin")  
    if not user:
        abort(403, "Unable to authenticate user.")

    # Check if the trail exists
    trail = Trail.query.filter(Trail.TrailID == trail_id).one_or_none()
    if not trail:
        abort(404, f"Trail with ID {trail_id} not found.")

    # Check if the feature exists
    feature = Feature.query.filter(Feature.Trail_FeatureID == feature_id).one_or_none()
    if not feature:
        abort(404, f"Feature with ID {feature_id} not found.")

    # Check if the feature is already associated with the trail
    existing_trail_feature = TrailFeature.query.filter_by(
        TrailID=trail_id, Trail_FeatureID=feature_id
    ).one_or_none()
    if existing_trail_feature:
        abort(400, f"Feature '{feature.Trail_Feature}' is already associated with this trail.")

    # Link the feature to the trail
    new_trail_feature = TrailFeature(
        TrailID=trail_id,
        Trail_FeatureID=feature_id
    )
    db.session.add(new_trail_feature)
    db.session.commit()

    return make_response(
        f"Feature '{feature.Trail_Feature}' successfully added to trail {trail.Trail_name}", 201
    )

def add_new_feature():
    user = require_auth_and_role("admin")  
    if not user:
        abort(403, "Unable to authenticate user.")

    request_data = request.get_json()
    feature_name = request_data.get("Trail_Feature")
    if not feature_name:
        abort(400, "Feature name is required.")

    existing_feature = Feature.query.filter_by(Trail_Feature=feature_name).one_or_none()
    if existing_feature:
        abort(400, "Feature already exists.")

    new_feature = Feature(Trail_Feature=feature_name)
    db.session.add(new_feature)
    db.session.commit()

    return feature_schema.dump(new_feature), 201

def update_feature(feature_id):
    user = require_auth_and_role("admin")  
    if not user:
        abort(403, "Unable to authenticate user.")

    # Check if the feature exists
    feature = Feature.query.filter(Feature.Trail_FeatureID == feature_id).one_or_none()
    if not feature:
        abort(404, f"Feature with ID {feature_id} not found.")

    # Parse the request data
    request_data = request.get_json()
    new_feature_name = request_data.get("Trail_Feature")
    if not new_feature_name:
        abort(400, "Feature name is required.")

    # Check if the new feature name already exists
    existing_feature = Feature.query.filter_by(Trail_Feature=new_feature_name).one_or_none()
    if existing_feature:
        abort(400, f"Feature with name '{new_feature_name}' already exists.")

    # Update the feature
    feature.Trail_Feature = new_feature_name
    db.session.commit()

    return make_response(f"Feature successfully updated to '{new_feature_name}'", 200)

def delete_feature_from_trail(trail_id, feature_id):
    user = require_auth_and_role("admin")  
    if not user:
        abort(403, "Unable to authenticate user.")

    # Check if the trail exists
    trail = Trail.query.filter(Trail.TrailID == trail_id).one_or_none()
    if not trail:
        abort(404, f"Trail with ID {trail_id} not found.")

    # Check if the feature exists
    feature = Feature.query.filter(Feature.Trail_FeatureID == feature_id).one_or_none()
    if not feature:
        abort(404, f"Feature with ID {feature_id} not found.")

    # Check if the feature is associated with the trail
    trail_feature = TrailFeature.query.filter_by(
        TrailID=trail_id, Trail_FeatureID=feature_id
    ).one_or_none()
    if not trail_feature:
        abort(404, f"Feature '{feature.Trail_Feature}' is not associated with trail {trail.Trail_name}.")

    # Remove the association without deleting the feature
    db.session.delete(trail_feature)
    db.session.commit()

    return make_response(f"Feature '{feature.Trail_Feature}' successfully removed from trail {trail.Trail_name}", 200)

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c