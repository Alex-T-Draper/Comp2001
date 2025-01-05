from flask import render_template, jsonify
import config
from models import Trail, User, LocationPoint

app = config.connex_app
app.add_api(config.basedir / "swagger.yml")

@app.route("/")
def home():
    trails = Trail.query.all()
    return render_template("home.html", trails=trails)

@app.route("/users")
def get_users():
    users = User.query.all()
    return jsonify([user.Email_address for user in users])

@app.route("/locations")
def get_locations():
    locations = LocationPoint.query.all()
    return jsonify([{"Latitude": loc.Latitude, "Longitude": loc.Longitude} for loc in locations])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
