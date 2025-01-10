from flask import render_template
import config
from models import Trail
from config import db
from trails import get_all_trails_with_details  # Import the method

config.connex_app.add_api(config.basedir / "swagger.yml")

app = config.app

@app.route("/")
def home():
    trails = get_all_trails_with_details()

    return render_template("home.html", trails=trails)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
