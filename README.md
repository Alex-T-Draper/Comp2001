# Trail Management Microservice

## Overview
This project is a microservice designed for managing trails, features, and location points. It is part of a larger Trail Application aimed at providing users with a platform to explore and enhance their outdoor experiences.

## Features
- **CRUD Operations** for trails, features, and location points.
- Integration with an **authentication API**.
- Ensures data privacy, security, and integrity.
- Implements RESTful principles and outputs data in JSON format.
- Includes a Swagger-based API documentation for easy interface representation.

## Prerequisites
1. **Docker** and **Docker Compose**
2. Access to the **Trail Authenticator API**

## Installation

### Using Docker

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd <repository_folder>
   ```

2. Build and run the Docker containers:
   ```bash
   docker-compose up --build
   ```

3. Access the application:
   - API: `http://localhost:5000`
   - Swagger UI: `http://localhost:5000/api/ui`

4. To stop the application:
   ```bash
   docker-compose down
   ```

### Without Docker

1. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up the database:
   - Use the provided `build_database.py` script to initialise the database schema and populate sample data.
   ```bash
   python build_database.py
   ```

3. Configure the server:
   - Update the database credentials and server information in `config.py` if necessary.

4. Run the server:
   ```bash
   python app.py
   ```

## API Documentation
The API documentation is available via Swagger:
- Navigate to `/api/ui` in your browser after starting the server.

### Endpoints
The following key endpoints are provided:

1. **Trails**
   - `GET /trails`: Fetch all trails.
   - `POST /trails`: Create a new trail (Admin only).
   - `GET /trails/{trail_id}`: Retrieve details of a specific trail.
   - `PUT /trails/{trail_id}`: Update a trail (Admin only).
   - `DELETE /trails/{trail_id}`: Delete a trail (Admin only).
   - `GET /trails/{trail_id}/features`: Retrieve features for a specific trail.
   - `POST /trails/{trail_id}/features/{feature_id}`: Add an existing feature to a trail (Admin only).
   - `DELETE /trails/{trail_id}/features/{feature_id}`: Remove a feature from a trail (Admin only).
   - `GET /trails/{trail_id}/location_points`: Retrieve location points for a specific trail.
   - `POST /trails/{trail_id}/location_points/{location_point_id}`: Add an existing location point to a trail (Admin only).
   - `DELETE /trails/{trail_id}/location_points/{location_point_id}`: Remove a location point from a trail (Admin only).

2. **Features**
   - `GET /features`: Fetch all features.
   - `POST /features`: Add a new feature (Admin only).
   - `GET /features/{feature_id}`: Retrieve details of a specific feature.
   - `PUT /features/{feature_id}`: Update a feature's name (Admin only).
   - `DELETE /features/{feature_id}`: Delete a feature (Admin only).

3. **Location Points**
   - `GET /location_points`: Fetch all location points.
   - `POST /location_points`: Add a new location point (Admin only).
   - `GET /location_points/{location_point_id}`: Retrieve details of a specific location point.
   - `PUT /location_points/{location_point_id}`: Update an existing location point (Admin only).
   - `DELETE /location_points/{location_point_id}`: Delete a location point (Admin only).

Refer to the `swagger.yml` file for more detailed endpoint descriptions and data formats.

## Security Features
- Authentication is enforced using the Authenticator API.
- Roles (`admin`, `user`) are validated for restricted actions.
- Data validation includes constraints like maximum distance between location points.

## Development
- **Programming Language:** Python
- **Frameworks:** Flask, Connexion
- **Database:** Microsoft SQL Server
- **ORM:** SQLAlchemy

### Directory Structure
```
├── CW2/
│   ├── app.py
│   ├── authentication.py
│   ├── build_database.py
│   ├── config.py
│   ├── models.py
│   ├── trails.py
│   ├── swagger.yml
│   ├── Dockerfile
│   ├── templates/
│   │   └── home.html
│   ├── requirements.txt
├── README.md
```

## Testing
Run the Flask server and use tools like Postman or cURL to test endpoints. Ensure the server is running on `http://localhost:5000`.

## Deployment
- The server-side code must be deployed on `web.socem.plymouth.ac.uk`.
- Ensure the database is hosted on `dist-6-505.uopnet.plymouth.ac.uk`.

## License
This project is for educational purposes under the COMP2001 coursework.
