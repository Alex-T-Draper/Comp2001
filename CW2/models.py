from datetime import datetime
import pytz
from config import db, ma
from sqlalchemy import CheckConstraint
from marshmallow import fields

# USER
class User(db.Model):
    __tablename__ = 'cw2_user'
    
    UserID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Email_address = db.Column(db.String(255), nullable=False)

    Role = db.Column(db.String(5), nullable=False)

    timestamp = db.Column(
        db.DateTime,
        default=lambda: datetime.now(pytz.timezone('Europe/London')),
        onupdate=lambda: datetime.now(pytz.timezone('Europe/London'))
    )

    _table_args__ = (
        CheckConstraint(
            "Role IN ('admin', 'user')",
            name="ck_user_role_valid"
        ),
    )

# TRAIL
class Trail(db.Model):
    __tablename__ = 'cw2_trail'

    TrailID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Trail_name = db.Column(db.String(50), nullable=False)
    Trail_Summary = db.Column(db.String(255))
    Trail_Description = db.Column(db.String(255))
    Difficulty = db.Column(db.String(20), nullable=False)
    Location = db.Column(db.String(50), nullable=False)
    Length = db.Column((db.Float), nullable=False)
    Elevation_gain = db.Column((db.Float), nullable=False)
    Route_type = db.Column(db.String(20), nullable=False)
    
    # OwnerID* Numeric (FK to User)
    OwnerID = db.Column(
        db.Integer, 
        db.ForeignKey('cw2_user.UserID', ondelete='CASCADE'), 
        nullable=False
    )

    features = db.relationship(
        'TrailFeature',
        backref='trail',
        cascade="all, delete-orphan"
    )

    location_points = db.relationship(
        'TrailLocationPt',
        backref='trail',
        cascade="all, delete-orphan"
    )

    timestamp = db.Column(
        db.DateTime,
        default=lambda: datetime.now(pytz.timezone('Europe/London')),
        onupdate=lambda: datetime.now(pytz.timezone('Europe/London'))
    )

# FEATURE
class Feature(db.Model):
    __tablename__ = 'cw2_feature'

    # Trail FeatureID Sequence PK
    Trail_FeatureID = db.Column(
        db.Integer, 
        primary_key=True, 
        autoincrement=True
    )
    
    Trail_Feature = db.Column(db.String(100), nullable=False)

    trail_features = db.relationship(
        'TrailFeature',
        backref='feature',
        cascade="all, delete-orphan"
    )

# TRAIL-FEATURE 
class TrailFeature(db.Model):
    __tablename__ = 'cw2_trail_feature'

    TrailID = db.Column(
        db.Integer,
        db.ForeignKey('cw2_trail.TrailID', ondelete='CASCADE'),
        primary_key=True
    )
    Trail_FeatureID = db.Column(
        db.Integer,
        db.ForeignKey('cw2_feature.Trail_FeatureID', ondelete='CASCADE'),
        primary_key=True
    )

# LOCATION-POINT
class LocationPoint(db.Model):
    __tablename__ = 'cw2_location_point'

    Location_Point = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Latitude = db.Column(db.Float, nullable=False)
    Longitude = db.Column(db.Float, nullable=False)
    Description = db.Column(db.String(255))

    timestamp = db.Column(
        db.DateTime,
        default=lambda: datetime.now(pytz.timezone('Europe/London')),
        onupdate=lambda: datetime.now(pytz.timezone('Europe/London'))
    )

    trail_location_pts = db.relationship(
        'TrailLocationPt',
        backref='location_point',
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.UniqueConstraint('Latitude', 'Longitude', name='unique_lat_lon'),
    )

# TRAIL-LOCATIONPt 
class TrailLocationPt(db.Model):
    __tablename__ = 'cw2_trail_location_pt'

    # PK: TrailID Numeric + Location_Point Numeric
    TrailID = db.Column(
        db.Integer,
        db.ForeignKey('cw2_trail.TrailID', ondelete='CASCADE'),
        primary_key=True
    )
    
    Location_Point = db.Column(
        db.Integer,
        db.ForeignKey('cw2_location_point.Location_Point', ondelete='CASCADE'),
        primary_key=True
    )

    # Order_no Numeric
    Order_no = db.Column((db.Integer), nullable=False)

# Schemas
class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        sqla_session = db.session

class TrailSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Trail
        load_instance = True
        sqla_session = db.session
        
class FeatureSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Feature
        load_instance = True
        sqla_session = db.session

class TrailFeatureSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = TrailFeature
        load_instance = True
        sqla_session = db.session
        include_fk = True

class LocationPointSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = LocationPoint
        load_instance = True
        sqla_session = db.session

class TrailLocationPtSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = TrailLocationPt
        load_instance = True
        sqla_session = db.session
        include_fk = True

user_schema = UserSchema()
users_schema = UserSchema(many=True)
trail_schema = TrailSchema()
trails_schema = TrailSchema(many=True)
location_point_schema = LocationPointSchema()
location_points_schema = LocationPointSchema(many=True)
feature_schema = FeatureSchema()
features_schema = FeatureSchema(many=True)
trail_feature_schema = TrailFeatureSchema()
trail_features_schema = TrailFeatureSchema(many=True)
trail_location_pt_schema = TrailLocationPtSchema()
trail_location_pts_schema = TrailLocationPtSchema(many=True)