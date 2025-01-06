# config.py

import pathlib
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import connexion

# Initialize Connexion
basedir = pathlib.Path(__file__).parent.resolve()
connex_app = connexion.App(__name__, specification_dir=basedir)

# Flask app and configurations
app = connex_app.app
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mssql+pyodbc:///?odbc_connect="
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=dist-6-505.uopnet.plymouth.ac.uk;"
    "DATABASE=COMP2001_ATrzcinskiDraper;"
    "UID=ATrzcinskiDraper;"
    "PWD=BlzN651*;"
    "TrustServerCertificate=yes;"
    "Encrypt=yes;"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
db = SQLAlchemy(app)
ma = Marshmallow(app)
