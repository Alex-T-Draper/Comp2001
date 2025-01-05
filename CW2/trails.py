from datetime import datetime
from flask import make_response, abort, request, g
from config import db
from models import Trail, trails_schema, trail_schema
from models import LocationPoint, location_point_schema, location_points_schema
from models import User, user_schema, users_schema

def read_all_trails():
    trails = Trail.query.all()
    return trails_schema.dump(trails)

def create_trail():
    # Extract data from the request
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

    # Extract and handle OwnerID explicitly
    owner_id = trail_data.get("OwnerID")
    if not owner_id:
        print("OwnerID is missing. Cannot create trail.")
        abort(400, "OwnerID is required to create a trail.")

    # Owner exists in database
    owner = User.query.filter_by(UserID=owner_id).one_or_none()
    if not owner:
        abort(404, f"User with ID {owner_id} not found.")

    # Remove OwnerID from the payload to avoid schema validation errors
    del trail_data["OwnerID"]

    # Add OwnerID back as part of the Trail model instance creation
    new_trail = Trail(**trail_data, OwnerID=owner_id)

    # Check for existing trail with the same name
    trail_name = trail_data.get("Trail_name")
    existing_trail = Trail.query.filter(Trail.Trail_name == trail_name).one_or_none()
    if existing_trail:
        abort(406, f"Trail with name {trail_name} already exists.")

    db.session.add(new_trail)
    db.session.commit()

    return trail_schema.dump(new_trail), 201

def read_one_trail(trail_name):
    trail = Trail.query.filter(Trail.Trail_name == trail_name).one_or_none()

    if trail is not None:
        return trail_schema.dump(trail)
    else:
        abort(404, f"Trail with name {trail_name} not found")

def update_trail(trail_name, trail):
    existing_trail = Trail.query.filter(Trail.Trail_name == trail_name).one_or_none()

    if existing_trail:
        update_trail = trail_schema.load(trail, session=db.session)
        existing_trail.Trail_Summary = update_trail.Trail_Summary
        existing_trail.Trail_Description = update_trail.Trail_Description
        existing_trail.Difficulty = update_trail.Difficulty
        existing_trail.Location = update_trail.Location
        existing_trail.Length = update_trail.Length
        existing_trail.Elevation_gain = update_trail.Elevation_gain
        existing_trail.Route_type = update_trail.Route_type
        existing_trail.timestamp = update_trail.timestamp

        db.session.merge(existing_trail)
        db.session.commit()
        return trail_schema.dump(existing_trail), 201
    else:
        abort(404, f"Trail with name {trail_name} not found")

def delete_trail(trail_name):
    existing_trail = Trail.query.filter(Trail.Trail_name == trail_name).one_or_none()

    if existing_trail:
        db.session.delete(existing_trail)
        db.session.commit()
        return make_response(f"{trail_name} successfully deleted", 200)
    else:
        abort(404, f"Trail with name {trail_name} not found")

def get_location(location_point_id):
    location_point = LocationPoint.query.filter(LocationPoint.Location_Point == location_point_id).one_or_none()

    if location_point is not None:
        return location_point_schema.dump(location_point)
    else:
        abort(404, f"Location point with ID {location_point_id} not found")

def read_all_locations():
    locations = LocationPoint.query.all()
    if not locations:
        abort(404, "No location points found.")
    return location_points_schema.dump(locations)

def update_location(location_point_id, location_data):
    existing_location_point = LocationPoint.query.filter(LocationPoint.Location_Point == location_point_id).one_or_none()

    if existing_location_point:
        existing_location_point.Latitude = location_data.get("Latitude", existing_location_point.Latitude)
        existing_location_point.Longitude = location_data.get("Longitude", existing_location_point.Longitude)
        existing_location_point.Description = location_data.get("Description", existing_location_point.Description)
        existing_location_point.timestamp = datetime.now()

        db.session.commit()
        return location_point_schema.dump(existing_location_point)
    else:
        abort(404, f"Location point with ID {location_point_id} not found")

def read_all_users():
    users = User.query.all()
    response = []

    for user in users:
        user_data = user_schema.dump(user)

        # Fetch trail-specific roles for the user
        trails = Trail.query.all() 
        trail_roles = []
        for trail in trails:
            role = "admin" if trail.OwnerID == user.UserID else "user"
            trail_roles.append({
                "TrailID": trail.TrailID,
                "Trail_name": trail.Trail_name,
                "Role": role
            })

        # Add trail-specific roles to the user data
        user_data["trail_roles"] = trail_roles
        response.append(user_data)

    return response

def read_one_user(user_id):
    user = User.query.filter(User.UserID == user_id).one_or_none()

    if user is not None:
        return user_schema.dump(user)
    else:
        abort(404, f"User with ID {user_id} not found")

def create_user():
    user_data = request.get_json()
    print("DEBUG: Raw request data:", user_data)

    if not user_data:
        print("No user data received.")
        abort(400, "No data provided or invalid format.")

    print("DEBUG: Final incoming user data:", user_data)

    # Validate required fields
    required_fields = ["Email_address", "Role"]
    for field in required_fields:
        if not user_data.get(field):
            abort(400, f"Missing required field: {field}")

    # Check if the user already exists by email
    email = user_data.get("Email_address")
    existing_user = User.query.filter(User.Email_address == email).one_or_none()

    if existing_user:
        print(f"User with email {email} already exists.")
        abort(406, f"User with email {email} already exists.")

    # Create and save the new user
    new_user = User(**user_data)  # Use keyword arguments for explicit field assignment
    db.session.add(new_user)
    db.session.commit()

    print("DEBUG: User created successfully:", new_user)
    return user_schema.dump(new_user), 201

def update_user(user_id, user_data):
    existing_user = User.query.filter(User.UserID == user_id).one_or_none()

    if existing_user:
        existing_user.Email_address = user_data.get("Email_address", existing_user.Email_address)
        existing_user.Role = user_data.get("Role", existing_user.Role)
        existing_user.timestamp = datetime.now()

        db.session.commit()
        return user_schema.dump(existing_user)
    else:
        abort(404, f"User with ID {user_id} not found")

def delete_user(user_id):
    existing_user = User.query.filter(User.UserID == user_id).one_or_none()

    if existing_user:
        db.session.delete(existing_user)
        db.session.commit()
        return make_response(f"User with ID {user_id} successfully deleted", 200)
    else:
        abort(404, f"User with ID {user_id} not found")

def get_user_role(user_id, trail_id):
    trail = Trail.query.filter_by(TrailID=trail_id).one_or_none()
    if not trail:
        return None  

    # Check if the user is the owner (admin) of the trail
    if trail.OwnerID == user_id:
        return "admin"
    return "user"

