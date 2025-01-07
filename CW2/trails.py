from datetime import datetime
from flask import make_response, abort, request
from config import db
from models import Trail, trails_schema, trail_schema
from models import LocationPoint, location_point_schema, location_points_schema, TrailLocationPt, Feature, TrailFeature
from authentication import require_auth_and_role
from math import radians, cos, sin, sqrt, atan2

def read_all_trails():
    trails = Trail.query.all()
    if not trails:
        abort(404, "No trails found")
    return trails_schema.dump(trails)

def read_trail_admin(trail_id):
    require_auth_and_role("admin")

    # Check if the trail exists
    trail = Trail.query.filter(Trail.TrailID == trail_id).one_or_none()
    if not trail:
        abort(404, f"Trail with ID {trail_id} not found.")

    # Fetch associated features
    features = db.session.query(Feature).join(TrailFeature).filter(
        TrailFeature.TrailID == trail_id
    ).all()

    # Fetch associated location points with order numbers
    location_points = db.session.query(LocationPoint, TrailLocationPt.Order_no).join(
        TrailLocationPt, TrailLocationPt.Location_Point == LocationPoint.Location_Point
    ).filter(TrailLocationPt.TrailID == trail_id).order_by(TrailLocationPt.Order_no).all()

    # Format location points to include order number
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

    # Format the response
    response = {
        "Trail": trail_schema.dump(trail),
        "OwnerID": trail.OwnerID,
        "Features": [feature.Trail_Feature for feature in features],
        "LocationPoints": formatted_location_points
    }
    return response

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
    if len(trail_data["Trail_name"]) < 3 or len(trail_data["Trail_name"]) > 100:
        abort(400, "Trail_name must be between 3 and 100 characters.")

    required_fields = ["Trail_name", "Location", "Difficulty", "Length", "LocationPoints"]
    for field in required_fields:
        if not trail_data.get(field):
            abort(400, f"Missing required field: {field}")

    # Check for duplicate trail name
    trail_name = trail_data.get("Trail_name")
    existing_trail = Trail.query.filter(Trail.Trail_name == trail_name).one_or_none()
    if existing_trail:
        abort(406, f"Trail with name {trail_name} already exists.")

    # Validate and process LocationPoints
    location_points = trail_data.get("LocationPoints")
    if not isinstance(location_points, list) or len(location_points) == 0:
        abort(400, "At least one LocationPoint is required.")

    MAX_DISTANCE = 10.0  # Maximum allowed distance in kilometers

    # Validate distances between consecutive location points
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

    # Add LocationPoints and establish relationships
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

def read_one_trail(trail_id):
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

    db.session.delete(existing_trail)
    db.session.commit()
    return make_response(f"Trail with ID {trail_id} successfully deleted", 200)

def get_location_points(location_point_id):
    location_point = LocationPoint.query.filter(LocationPoint.Location_Point == location_point_id).one_or_none()

    if location_point is not None:
        return location_point_schema.dump(location_point)
    else:
        abort(404, f"Location point with ID {location_point_id} not found")

def read_all_location_points():
    # Fetch all TrailLocationPt and LocationPoint data
    trail_location_pts = db.session.query(TrailLocationPt).all()

    # Initialize a dictionary to organize data by TrailID
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

def update_location_point(location_point_id):
    require_auth_and_role("admin")
    request_data = request.get_json()
    print("DEBUG: Raw request data:", request_data)

    # Fetch the existing location point
    existing_location_point = LocationPoint.query.filter(LocationPoint.Location_Point == location_point_id).one_or_none()
    if not existing_location_point:
        abort(404, f"Location point with ID {location_point_id} not found.")

    # Fetch neighboring points
    trail_location = TrailLocationPt.query.filter_by(Location_Point=location_point_id).one_or_none()
    if not trail_location:
        abort(404, "Location point is not associated with any trail.")

    trail_id = trail_location.TrailID
    order_no = trail_location.Order_no

    prev_point = db.session.query(LocationPoint).join(TrailLocationPt).filter(
        TrailLocationPt.TrailID == trail_id,
        TrailLocationPt.Order_no == order_no - 1
    ).one_or_none()

    next_point = db.session.query(LocationPoint).join(TrailLocationPt).filter(
        TrailLocationPt.TrailID == trail_id,
        TrailLocationPt.Order_no == order_no + 1
    ).one_or_none()

    MAX_DISTANCE = 10.0

    # Validate distance to previous point
    if prev_point:
        distance = calculate_distance(
            prev_point.Latitude, prev_point.Longitude,
            request_data.get("Latitude", existing_location_point.Latitude),
            request_data.get("Longitude", existing_location_point.Longitude)
        )
        if distance > MAX_DISTANCE:
            abort(400, f"Distance to previous point exceeds {MAX_DISTANCE} km.")

    # Validate distance to next point
    if next_point:
        distance = calculate_distance(
            request_data.get("Latitude", existing_location_point.Latitude),
            request_data.get("Longitude", existing_location_point.Longitude),
            next_point.Latitude, next_point.Longitude
        )
        if distance > MAX_DISTANCE:
            abort(400, f"Distance to next point exceeds {MAX_DISTANCE} km.")

    # Update location point
    existing_location_point.Latitude = request_data.get("Latitude", existing_location_point.Latitude)
    existing_location_point.Longitude = request_data.get("Longitude", existing_location_point.Longitude)
    existing_location_point.Description = request_data.get("Description", existing_location_point.Description)
    existing_location_point.timestamp = datetime.now()

    db.session.commit()

    return location_point_schema.dump(existing_location_point), 200

def add_location_point_to_trail(trail_id):
    require_auth_and_role("admin")

    if not isinstance(trail_id, int) or trail_id <= 0:
        abort(400, description="trail_id must be a positive integer.")
        
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

    # Fetch the last location point in the trail
    last_point = db.session.query(LocationPoint).join(TrailLocationPt).filter(
        TrailLocationPt.TrailID == trail_id
    ).order_by(TrailLocationPt.Order_no.desc()).first()

    if last_point:
        # Calculate distance to the new point
        distance = calculate_distance(
            last_point.Latitude, last_point.Longitude, new_lat, new_lon
        )
        MAX_DISTANCE = 10.0 
        if distance > MAX_DISTANCE:
            abort(400, f"New location point is too far from the last point ({distance:.2f} km). Maximum allowed is {MAX_DISTANCE} km.")

    # Create the new location point
    new_location = LocationPoint(
        Latitude=new_lat,
        Longitude=new_lon,
        Description=request_data["Description"],
        timestamp=datetime.now(),
    )
    db.session.add(new_location)
    db.session.flush()

    # Establish the relationship with the trail
    max_order_no = db.session.query(db.func.max(TrailLocationPt.Order_no)).filter_by(TrailID=trail_id).scalar() or 0
    new_trail_location_pt = TrailLocationPt(
        TrailID=trail_id,
        Location_Point=new_location.Location_Point,
        Order_no=max_order_no + 1,
    )
    db.session.add(new_trail_location_pt)
    db.session.commit()

    return location_point_schema.dump(new_location), 201

def delete_location_point_from_trail(location_point_id):
    require_auth_and_role("admin")

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

    db.session.commit()

    return make_response(f"Location point with ID {location_point_id} successfully deleted from trail {trail_id}", 200)

def add_feature_to_trail(trail_id):
    require_auth_and_role("admin")

    # Check if the trail exists
    trail = Trail.query.filter(Trail.TrailID == trail_id).one_or_none()
    if not trail:
        abort(404, f"Trail with ID {trail_id} not found.")

    # Parse request data
    request_data = request.get_json()
    feature_name = request_data.get("Trail_Feature")
    if not feature_name:
        abort(400, "Feature name is required.")

    # Check if the feature already exists
    existing_feature = Feature.query.filter_by(Trail_Feature=feature_name).one_or_none()
    if not existing_feature:
        # Create the feature if it doesn't exist
        new_feature = Feature(Trail_Feature=feature_name)
        db.session.add(new_feature)
        db.session.flush()  # Generate Trail_FeatureID
        feature_id = new_feature.Trail_FeatureID
    else:
        feature_id = existing_feature.Trail_FeatureID

    # Link the feature to the trail in the TrailFeature table
    existing_trail_feature = TrailFeature.query.filter_by(
        TrailID=trail_id, Trail_FeatureID=feature_id
    ).one_or_none()

    if existing_trail_feature:
        abort(400, f"Feature '{feature_name}' is already associated with this trail.")

    new_trail_feature = TrailFeature(
        TrailID=trail_id,
        Trail_FeatureID=feature_id
    )
    db.session.add(new_trail_feature)
    db.session.commit()

    return make_response(f"Feature '{feature_name}' successfully added to trail {trail.Trail_name}", 201)

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

    # Remove the association
    db.session.delete(trail_feature)

    # Check if the feature is linked to other trails
    linked_trails_count = TrailFeature.query.filter_by(Trail_FeatureID=feature_id).count()
    if linked_trails_count == 0:
        # If no other trails use this feature, delete the feature
        db.session.delete(feature)

    db.session.commit()

    return make_response(f"Feature '{feature.Trail_Feature}' successfully deleted from trail {trail.Trail_name}", 200)



def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c
