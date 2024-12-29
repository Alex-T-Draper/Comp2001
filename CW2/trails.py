from datetime import datetime
from flask import make_response, abort
from config import db
from models import Trail, trails_schema, trail_schema
from models import LocationPoint, location_point_schema
from models import User, user_schema, users_schema

def read_all_trails():
    trails = Trail.query.all()
    return trails_schema.dump(trails)

def create_trail(trail):
    trail_name = trail.get("Trail_name")

    existing_trail = Trail.query.filter(Trail.Trail_name == trail_name).one_or_none()

    if existing_trail is None:
        new_trail = trail_schema.load(trail, session=db.session)
        db.session.add(new_trail)
        db.session.commit()
        return trail_schema.dump(new_trail), 201
    else:
        abort(406, f"Trail with name {trail_name} already exists")

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
    return users_schema.dump(users)

def read_one_user(user_id):
    user = User.query.filter(User.UserID == user_id).one_or_none()

    if user is not None:
        return user_schema.dump(user)
    else:
        abort(404, f"User with ID {user_id} not found")

def create_user(user):
    email = user.get("Email_address")

    existing_user = User.query.filter(User.Email_address == email).one_or_none()

    if existing_user is None:
        new_user = user_schema.load(user, session=db.session)
        db.session.add(new_user)
        db.session.commit()
        return user_schema.dump(new_user), 201
    else:
        abort(406, f"User with email {email} already exists")

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
