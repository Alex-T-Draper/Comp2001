from datetime import datetime
from flask import make_response, abort, request
from config import db
from models import Trail, trails_schema, trail_schema
from models import LocationPoint, location_point_schema, location_points_schema, TrailLocationPt
from models import User, user_schema, users_schema

def read_all_trails():
    trails = Trail.query.all()
    return trails_schema.dump(trails)

def create_trail(adminID):
    trail_data = request.get_json()
    print("DEBUG: Raw request data:", trail_data)

    if not trail_data:
        print("No trail data received.")
        abort(400, "No data provided or invalid format.")

    print("DEBUG: Final incoming trail data:", trail_data)

    # Validate the admin's role using adminID
    admin_user = User.query.filter_by(UserID=adminID).one_or_none()
    if not admin_user:
        abort(404, f"Admin user with ID {adminID} not found.")
    if admin_user.Role != "admin":
        abort(403, "Only admins can create trails.")

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

    # Set the OwnerID programmatically
    trail_data["OwnerID"] = adminID

    # Remove OwnerID from the schema load
    trail_data_without_owner_id = {k: v for k, v in trail_data.items() if k != "OwnerID"}

    # Create and save the new trail
    new_trail = trail_schema.load(trail_data_without_owner_id, session=db.session)
    new_trail.OwnerID = adminID
    db.session.add(new_trail)
    db.session.commit()

    return trail_schema.dump(new_trail), 201


def read_one_trail(trail_name):
    trail = Trail.query.filter(Trail.Trail_name == trail_name).one_or_none()

    if trail is not None:
        return trail_schema.dump(trail)
    else:
        abort(404, f"Trail with name {trail_name} not found")

def update_trail(trail_name, adminID):
    trail_data = request.get_json()
    print("DEBUG: Raw request data:", trail_data)

    # Validate the admin's role using adminID
    admin_user = User.query.filter_by(UserID=adminID).one_or_none()
    if not admin_user:
        abort(404, f"Admin user with ID {adminID} not found.")
    if admin_user.Role != "admin":
        abort(403, "Only admins can update trails.")

    # Fetch the existing trail
    existing_trail = Trail.query.filter(Trail.Trail_name == trail_name).one_or_none()
    if not existing_trail:
        abort(404, f"Trail with name {trail_name} not found.")

    # Update only provided fields
    for key, value in trail_data.items():
        setattr(existing_trail, key, value)

    db.session.commit()
    return trail_schema.dump(existing_trail), 200

def delete_trail(trail_name, adminID):
    # Validate the admin's role using adminID
    admin_user = User.query.filter_by(UserID=adminID).one_or_none()
    if not admin_user:
        abort(404, f"Admin user with ID {adminID} not found.")
    if admin_user.Role != "admin":
        abort(403, "Only admins can delete trails.")

    # Fetch and delete the trail
    existing_trail = Trail.query.filter(Trail.Trail_name == trail_name).one_or_none()
    if not existing_trail:
        abort(404, f"Trail with name {trail_name} not found.")

    db.session.delete(existing_trail)
    db.session.commit()
    return make_response(f"{trail_name} successfully deleted", 200)

def get_location(location_point_id):
    location_point = LocationPoint.query.filter(LocationPoint.Location_Point == location_point_id).one_or_none()

    if location_point is not None:
        return location_point_schema.dump(location_point)
    else:
        abort(404, f"Location point with ID {location_point_id} not found")

def read_all_locations():
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



def update_location(location_point_id, adminID):
    request_data = request.get_json()
    print("DEBUG: Raw request data:", request_data)

    # Validate the admin's role using adminID
    admin_user = User.query.filter_by(UserID=adminID).one_or_none()
    if not admin_user:
        abort(404, f"Admin user with ID {adminID} not found.")
    if admin_user.Role != "admin":
        abort(403, "Only admins can update locations.")

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

def read_all_users():
    users = User.query.all()
    return users_schema.dump(users)

def read_one_user(user_id):
    user = User.query.filter(User.UserID == user_id).one_or_none()

    if user is not None:
        return user_schema.dump(user)
    else:
        abort(404, f"User with ID {user_id} not found")

def create_user(adminID):
    user_data = request.get_json()
    print("DEBUG: Raw request data:", user_data)

    if not user_data:
        print("No user data received.")
        abort(400, "No data provided or invalid format.")

    # Validate the admin's role using adminID
    admin_user = User.query.filter_by(UserID=adminID).one_or_none()
    if not admin_user:
        abort(404, f"Admin user with ID {adminID} not found.")
    if admin_user.Role != "admin":
        abort(403, "Only admins can create users.")

    # Check for existing email
    email = user_data.get("Email_address")
    existing_user = User.query.filter_by(Email_address=email).one_or_none()
    if existing_user:
        abort(406, f"User with email {email} already exists.")

    # Create and save the new user
    new_user = user_schema.load(user_data, session=db.session)
    db.session.add(new_user)
    db.session.commit()
    return user_schema.dump(new_user), 201

def update_user(user_id, adminID):
    # Get the incoming data from the request
    user_data = request.get_json()
    print("DEBUG: Raw request data:", user_data)

    if not user_data:
        abort(400, "No data provided or invalid format.")

    # Validate the admin's role using adminID
    admin_user = User.query.filter_by(UserID=adminID).one_or_none()
    if not admin_user:
        abort(404, f"Admin user with ID {adminID} not found.")
    if admin_user.Role != "admin":
        abort(403, "Only admins can update users.")

    # Find the user to be updated
    existing_user = User.query.filter(User.UserID == user_id).one_or_none()
    if not existing_user:
        abort(404, f"User with ID {user_id} not found.")

    # Update fields only if they are provided in the request
    existing_user.Email_address = user_data.get("Email_address", existing_user.Email_address)
    existing_user.Role = user_data.get("Role", existing_user.Role)
    existing_user.timestamp = datetime.now()

    # Save changes to the database
    db.session.commit()

    # Return the updated user
    return user_schema.dump(existing_user), 201

def delete_user(user_id, adminID):
    # Validate the admin's role using adminID
    admin_user = User.query.filter_by(UserID=adminID).one_or_none()
    if not admin_user:
        abort(404, f"Admin user with ID {adminID} not found.")
    if admin_user.Role != "admin":
        abort(403, "Only admins can delete users.")

    # Find the user to be deleted
    existing_user = User.query.filter(User.UserID == user_id).one_or_none()
    if not existing_user:
        abort(404, f"User with ID {user_id} not found.")

    # Delete the user
    db.session.delete(existing_user)
    db.session.commit()
    return make_response(f"User with ID {user_id} successfully deleted", 200)

def get_user_role(user_id):
    # Fetch the user from the database
    user = User.query.filter_by(UserID=user_id).one_or_none()
    
    if not user:
        abort(404, f"User with ID {user_id} not found.")
    
    # Return the user's role
    return user.Role

