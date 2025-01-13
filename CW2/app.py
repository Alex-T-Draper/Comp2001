from flask import render_template
import config
from trails import get_all_trails  

config.connex_app.add_api(config.basedir / "swagger.yml")

app = config.app

@app.route("/")
def home():
    trails = get_all_trails()

    return render_template("home.html", trails=trails)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
