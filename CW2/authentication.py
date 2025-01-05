import requests
from models import User
from config import db, app
from sqlalchemy.orm import sessionmaker
from trails import get_user_role

# Authentication URL
auth_url = 'https://web.socem.plymouth.ac.uk/COMP2001/auth/api/users'

# List of users to authenticate
users = [
    {'email': 'grace@plymouth.ac.uk', 'password': 'ISAD123!'},
    {'email': 'tim@plymouth.ac.uk', 'password': 'COMP2001!'},
    {'email': 'ada@plymouth.ac.uk', 'password': 'insecurePassword'}
]

with app.app_context():
    # Set up a database session
    Session = sessionmaker(bind=db.engine)
    session = Session()

    # Authenticate users and fetch roles
    for user in users:
        credentials = {'email': user['email'], 'password': user['password']}
        response = requests.post(auth_url, json=credentials)

        if response.status_code == 200:
            print(f"Authenticated successfully: {user['email']}")

            # Fetch user from the local database
            local_user = session.query(User).filter(User.Email_address == user['email']).one_or_none()
            if local_user:
                # Fetch and print the user's global role
                role = get_user_role(local_user.UserID)
                print(f"Global Role for {user['email']}: {role}")
            else:
                print(f"User {user['email']} does not exist in the local database.")
        else:
            print(f"Failed to authenticate user {user['email']} with status code {response.status_code}")
