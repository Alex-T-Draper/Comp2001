from datetime import datetime
from flask import make_response, abort, request
from config import db
from models import Trail, trails_schema, trail_schema
from models import LocationPoint, location_point_schema, location_points_schema, TrailLocationPt
from authentication import require_auth_and_role

def read_all_trails():
    trails = Trail.query.all()
    return trails_schema.dump(trails)

def create_trail():
    user = require_auth_and_role("admin")
    if not user:
        abort(403, "Unable to authenticate user.")

    trail_data = request.get_json()
    print("DEBUG: Raw request data:", trail_data)

    if not trail_data:
        print("No trail data received.")
        abort(400, "No data provided or invalid format.")

    print("DEBUG: Final incoming trail data:", trail_data)

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

    # Create and save the new trail
    trail_data["OwnerID"] = user["UserID"]
    new_trail = trail_schema.load(trail_data, session=db.session)
    db.session.add(new_trail)
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

def get_location(location_point_id):
    location_point = LocationPoint.query.filter(LocationPoint.Location_Point == location_point_id).one_or_none()

    if location_point is not None:
        return location_point_schema.dump(location_point)
    else:
        abort(404, f"Location point with ID {location_point_id} not found")

def read_all_locations():
    location_points = LocationPoint.query.all()
    return location_points_schema.dump(location_points)

def update_location(location_point_id):
    require_auth_and_role("admin")  # Ensure only admins can update location points
    request_data = request.get_json()
    print("DEBUG: Raw request data:", request_data)

    # Fetch the existing location point
    existing_location_point = LocationPoint.query.filter(LocationPoint.Location_Point == location_point_id).one_or_none()

    if not existing_location_point:
        abort(404, f"Location point with ID {location_point_id} not found.")

    # Update only the provided fields
    existing_location_point.Latitude = request_data.get("Latitude", existing_location_point.Latitude)
    existing_location_point.Longitude = request_data.get("Longitude", existing_location_point.Longitude)
    existing_location_point.Description = request_data.get("Description", existing_location_point.Description)
    existing_location_point.timestamp = datetime.now()

    # Save changes to the database
    db.session.commit()

    # Return the updated location
    return location_point_schema.dump(existing_location_point), 200