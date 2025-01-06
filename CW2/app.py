# app.py

from flask import render_template, jsonify
import config
from models import Trail, LocationPoint

config.connex_app.add_api(config.basedir / "swagger.yml")

app = config.app

@app.route("/")
def home():
    trails = Trail.query.all()
    return render_template("home.html", trails=trails)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
