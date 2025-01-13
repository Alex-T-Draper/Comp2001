from flask import request, abort
from models import User

# List of users to authenticate
password_list = [
    {'email': 'grace@plymouth.ac.uk', 'password': 'ISAD123!'},
    {'email': 'tim@plymouth.ac.uk', 'password': 'COMP2001!'},
    {'email': 'ada@plymouth.ac.uk', 'password': 'insecurePassword'}
]

def authenticate_user(username=None, password=None):
    auth = request.authorization
    if not auth:
        print("DEBUG: Missing authorization header.")
        abort(401, "Authentication required.")

    email = auth.username or username
    pwd = auth.password or password
    print(f"DEBUG: Authenticating user with email: {email}")

    # Validate the password using the predefined list
    valid_user = next((u for u in password_list if u['email'] == email and u['password'] == pwd), None)
    if not valid_user:
        print("DEBUG: Password validation failed.")
        abort(401, "Invalid credentials.")

    # Fetch the user's role and ID from the database
    user = User.query.filter_by(Email_address=email).one_or_none()
    if not user:
        print("DEBUG: User not found in the database.")
        abort(401, "User not found in the database.")

    print(f"DEBUG: User authenticated successfully with email: {email}, role: {user.Role}, UserID: {user.UserID}")
    return {"email": user.Email_address, "role": user.Role, "UserID": user.UserID}

def require_auth(): 
    user = authenticate_user() 
    if not user:
        abort(401, "Authentication required.")

    return user

def require_auth_and_role(role="admin"):
    user = authenticate_user()
    print(f"DEBUG: Retrieved user: {user}")
    if role == "admin" and user.get("role") != "admin":
        print(f"DEBUG: User does not have admin privileges. User role: {user.get('role')}")
        abort(403, "Admin privileges required.")
    return user

