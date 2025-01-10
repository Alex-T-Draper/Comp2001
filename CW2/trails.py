from datetime import datetime
from math import radians, cos, sin, sqrt, atan2
from flask import make_response, abort, request
from config import db
from models import (
    Trail, trails_schema, trail_schema,
    LocationPoint, location_point_schema, location_points_schema,
    TrailLocationPt, Feature, TrailFeature, feature_schema
)
from authentication import require_auth_and_role

def get_all_trails():
    trails = Trail.query.all()
    if not trails:
        abort(404, "No trails found")
    return trails_schema.dump(trails)

def get_all_trails_with_details():
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
                "timestamp": lp.timestamp
            }
            for lp, order_no in location_points
        ]

        # Format features 
        formatted_features = [
            {
                "Trail_FeatureID": feature.Trail_FeatureID,  
                "Trail_Feature": feature.Trail_Feature
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
            "Features": formatted_features,  
            "LocationPoints": formatted_location_points,  
            "timestamp": trail.timestamp
        }

        all_trails_with_details.append(formatted_trail)

    return all_trails_with_details

def create_trail():
    user = require_auth_and_role("admin")
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

    # Check for duplicate trail name
    trail_name = trail_data.get("Trail_name")
    existing_trail = Trail.query.filter(Trail.Trail_name == trail_name).one_or_none()
    if existing_trail:
        abort(406, f"Trail with name {trail_name} already exists.")

    # Extract and validate LocationPoints separately
    location_points = trail_data.pop("LocationPoints", [])
    if not isinstance(location_points, list):
        abort(400, "LocationPoints must be a list.")

    MAX_DISTANCE = 10.0
    for i in range(1, len(location_points)):
        prev = location_points[i - 1]
        curr = location_points[i]

        distance = calculate_distance(
            prev["Latitude"], prev["Longitude"],
            curr["Latitude"], curr["Longitude"]
        )
        if distance > MAX_DISTANCE:
            abort(400, f"Distance between location point {i} and {i+1} exceeds {MAX_DISTANCE} km.")

    # Create the trail
    trail_data["OwnerID"] = user["UserID"]
    new_trail = trail_schema.load(trail_data, session=db.session)
    db.session.add(new_trail)
    db.session.flush()  # Get the TrailID for relationships

    # Add LocationPoints
    for i, loc_data in enumerate(location_points):
        new_location = LocationPoint(
            Latitude=loc_data["Latitude"],
            Longitude=loc_data["Longitude"],
            Description=loc_data["Description"],
            timestamp=datetime.now(),
        )
        db.session.add(new_location)
        db.session.flush()

        new_trail_location_pt = TrailLocationPt(
            TrailID=new_trail.TrailID,
            Location_Point=new_location.Location_Point,
            Order_no=i + 1,
        )
        db.session.add(new_trail_location_pt)

    db.session.commit()
    return trail_schema.dump(new_trail), 201

def get_one_trail(trail_id):
    trail = Trail.query.filter(Trail.TrailID == trail_id).one_or_none()
    if trail is not None:
        return trail_schema.dump(trail)
    else:
        abort(404, f"Trail with ID {trail_id} not found")

def update_trail(trail_id):
    require_auth_and_role("admin")
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
    require_auth_and_role("admin")
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

def get_location_points(location_point_id):
    location_point = LocationPoint.query.filter(LocationPoint.Location_Point == location_point_id).one_or_none()

    if location_point is not None:
        return location_point_schema.dump(location_point)
    else:
        abort(404, f"Location point with ID {location_point_id} not found")

def get_all_features():
    # Fetch all features from the database
    features = Feature.query.all()
    if not features:
        return {"message": "No features found in the database."}, 200
    
    # Serialize and return features
    return [{"FeatureID": feature.Trail_FeatureID, "Feature": feature.Trail_Feature} for feature in features], 200

def get_feature_by_id(feature_id):
    # Fetch the feature with the given ID
    feature = Feature.query.filter(Feature.Trail_FeatureID == feature_id).one_or_none()
    if not feature:
        abort(404, f"Feature with ID {feature_id} not found.")
    
    # Serialize and return the feature
    return {"FeatureID": feature.Trail_FeatureID, "Feature": feature.Trail_Feature}, 200

def delete_feature_by_id(feature_id):
    require_auth_and_role("admin")

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
    # Fetch all TrailLocationPt and LocationPoint data
    trail_location_pts = db.session.query(TrailLocationPt).all()

    # Check if no location points exist
    if not trail_location_pts:
        return {"message": "No location points found in the database."}, 200

    # Initialize a dictionary to organise data by TrailID
    response_data = {}
    
    for trail_location_pt in trail_location_pts:
        # Get the associated LocationPoint data
        location_point = db.session.query(LocationPoint).filter_by(
            Location_Point=trail_location_pt.Location_Point
        ).one_or_none()

        if not location_point:
            continue

        # Add to the response under the appropriate TrailID
        trail_id = trail_location_pt.TrailID
        if trail_id not in response_data:
            response_data[trail_id] = []

        response_data[trail_id].append({
            "Location_Point": location_point.Location_Point,
            "Latitude": location_point.Latitude,
            "Longitude": location_point.Longitude,
            "Description": location_point.Description,
            "Order_no": trail_location_pt.Order_no,
        })

    # Format the response for clarity
    formatted_response = [
        {"TrailID": trail_id, "Locations": locations}
        for trail_id, locations in response_data.items()
    ]

    return formatted_response

def get_point_locations_for_trail(trail_id):
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

def update_location_point(trail_id, location_point_id):
    require_auth_and_role("admin")
    request_data = request.get_json()

    # Fetch the existing location point
    existing_location_point = LocationPoint.query.filter(LocationPoint.Location_Point == location_point_id).one_or_none()
    if not existing_location_point:
        abort(404, f"Location point with ID {location_point_id} not found.")

    # Fetch its trail-location relationship
    trail_location = TrailLocationPt.query.filter_by(Location_Point=location_point_id).one_or_none()
    if not trail_location:
        abort(404, "Location point is not associated with any trail.")

    trail_id = trail_location.TrailID
    current_order_no = trail_location.Order_no

    # Get new latitude, longitude, and order number
    new_lat = request_data.get("Latitude", existing_location_point.Latitude)
    new_lon = request_data.get("Longitude", existing_location_point.Longitude)
    new_order_no = request_data.get("Order_no", current_order_no)
    max_order_no = db.session.query(db.func.max(TrailLocationPt.Order_no)).filter_by(TrailID=trail_id).scalar() or 0

    # Check if the coordinates already exist in the trail (excluding the current point)
    duplicate_point = db.session.query(LocationPoint.Location_Point).join(TrailLocationPt).filter(
        TrailLocationPt.TrailID == trail_id,
        LocationPoint.Latitude == new_lat,
        LocationPoint.Longitude == new_lon,
        LocationPoint.Location_Point != location_point_id
    ).first()
    if duplicate_point:
        abort(400, f"A location point with the same coordinates already exists in trail ID {trail_id}.")

    # Validate the new order number if it changes
    if new_order_no != current_order_no:
        if new_order_no < 1 or new_order_no > max_order_no:
            abort(400, f"Order_no must be between 1 and {max_order_no}.")

    # Fetch neighboring points for distance validation
    prev_point = db.session.query(LocationPoint).join(TrailLocationPt).filter(
        TrailLocationPt.TrailID == trail_id,
        TrailLocationPt.Order_no == (new_order_no - 1)
    ).one_or_none()

    next_point = db.session.query(LocationPoint).join(TrailLocationPt).filter(
        TrailLocationPt.TrailID == trail_id,
        TrailLocationPt.Order_no == (new_order_no + 1)
    ).one_or_none()

    MAX_DISTANCE = 10.0

    # Validate distance to previous point
    if prev_point:
        distance = calculate_distance(
            prev_point.Latitude, prev_point.Longitude,
            new_lat, new_lon
        )
        if distance > MAX_DISTANCE:
            abort(400, f"Distance to previous point exceeds {MAX_DISTANCE} km.")

    # Validate distance to next point
    if next_point:
        distance = calculate_distance(
            new_lat, new_lon,
            next_point.Latitude, next_point.Longitude
        )
        if distance > MAX_DISTANCE:
            abort(400, f"Distance to next point exceeds {MAX_DISTANCE} km.")

    # Adjust order numbers if necessary
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

    # Update the location point details
    existing_location_point.Latitude = new_lat
    existing_location_point.Longitude = new_lon
    existing_location_point.Description = request_data.get("Description", existing_location_point.Description)
    existing_location_point.timestamp = datetime.now()

    db.session.commit()

    return location_point_schema.dump(existing_location_point), 200

def add_location_point_to_trail(trail_id):
    require_auth_and_role("admin")

    # Fetch the trail
    trail = Trail.query.filter(Trail.TrailID == trail_id).one_or_none()
    if not trail:
        abort(404, f"Trail with ID {trail_id} not found.")

    # Get the request data
    request_data = request.get_json()
    print("DEBUG: Raw request data:", request_data)

    # Validate required fields for the location point
    required_fields = ["Latitude", "Longitude", "Description"]
    for field in required_fields:
        if not request_data.get(field):
            abort(400, f"Missing required field: {field}")

    new_lat = request_data["Latitude"]
    new_lon = request_data["Longitude"]
    order_no = request_data.get("Order_no")  # Fetch order number, default to None if not provided

    # Check if the coordinates already exist in the trail
    duplicate_point = db.session.query(LocationPoint.Location_Point).join(TrailLocationPt).filter(
        TrailLocationPt.TrailID == trail_id,
        LocationPoint.Latitude == new_lat,
        LocationPoint.Longitude == new_lon
    ).first()
    if duplicate_point:
        abort(400, f"A location point with the same coordinates already exists in trail ID {trail_id}.")

    # Determine the maximum existing order number
    max_order_no = db.session.query(db.func.max(TrailLocationPt.Order_no)).filter_by(TrailID=trail_id).scalar() or 0

    if order_no:
        # Check if the order number is already in use
        existing_order = db.session.query(TrailLocationPt.Order_no).filter_by(TrailID=trail_id, Order_no=order_no).scalar()
        if existing_order:
            abort(400, f"Order_no {order_no} is already in use for trail ID {trail_id}.")
        # Adjust order numbers for insertion
        db.session.query(TrailLocationPt).filter(
            TrailLocationPt.TrailID == trail_id, TrailLocationPt.Order_no >= order_no
        ).update({"Order_no": TrailLocationPt.Order_no + 1}, synchronize_session=False)
    else:
        # Default order_no to the next available position
        order_no = max_order_no + 1

    # Fetch neighboring points for validation
    prev_point = db.session.query(LocationPoint).join(TrailLocationPt).filter(
        TrailLocationPt.TrailID == trail_id,
        TrailLocationPt.Order_no == (order_no - 1)
    ).one_or_none()

    next_point = db.session.query(LocationPoint).join(TrailLocationPt).filter(
        TrailLocationPt.TrailID == trail_id,
        TrailLocationPt.Order_no == order_no
    ).one_or_none()

    MAX_DISTANCE = 10.0

    # Validate distance to previous point
    if prev_point:
        distance = calculate_distance(
            prev_point.Latitude, prev_point.Longitude,
            new_lat, new_lon
        )
        if distance > MAX_DISTANCE:
            abort(400, f"Distance to previous point exceeds {MAX_DISTANCE} km.")

    # Validate distance to next point
    if next_point:
        distance = calculate_distance(
            new_lat, new_lon,
            next_point.Latitude, next_point.Longitude
        )
        if distance > MAX_DISTANCE:
            abort(400, f"Distance to next point exceeds {MAX_DISTANCE} km.")

    # Create the new location point
    new_location = LocationPoint(
        Latitude=new_lat,
        Longitude=new_lon,
        Description=request_data["Description"],
        timestamp=datetime.now(),
    )
    db.session.add(new_location)
    db.session.flush()

    # Create the trail-location relationship
    new_trail_location_pt = TrailLocationPt(
        TrailID=trail_id,
        Location_Point=new_location.Location_Point,
        Order_no=order_no,
    )
    db.session.add(new_trail_location_pt)
    db.session.commit()

    return location_point_schema.dump(new_location), 201

def delete_location_point_from_trail(trail_id, location_point_id):
    require_auth_and_role("admin")

    # Check if the trail exists
    trail = Trail.query.filter(Trail.TrailID == trail_id).one_or_none()
    if not trail:
        abort(404, f"Trail with ID {trail_id} not found.")

    # Fetch the location point relationship
    trail_location_pt = TrailLocationPt.query.filter_by(Location_Point=location_point_id).one_or_none()
    if not trail_location_pt:
        abort(404, f"Location point with ID {location_point_id} not found in any trail.")

    # Check if the trail has at least one other location point
    trail_id = trail_location_pt.TrailID
    location_count = TrailLocationPt.query.filter_by(TrailID=trail_id).count()
    if location_count <= 1:
        abort(400, "A trail must have at least one location point.")

    # Delete the location point relationship and the location point itself
    db.session.delete(trail_location_pt)

    # Fetch and delete the actual location point
    location_point = LocationPoint.query.filter_by(Location_Point=location_point_id).one_or_none()
    if location_point:
        db.session.delete(location_point)

    remaining_points = TrailLocationPt.query.filter_by(TrailID=trail_id).order_by(TrailLocationPt.Order_no).all()
    for index, point in enumerate(remaining_points):
        point.Order_no = index + 1

    db.session.commit()

    return make_response(f"Location point with ID {location_point_id} successfully deleted from trail {trail_id}", 200)

def get_features_for_trail(trail_id):
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
    require_auth_and_role("admin")

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
    require_auth_and_role("admin")

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
    require_auth_and_role("admin")

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
