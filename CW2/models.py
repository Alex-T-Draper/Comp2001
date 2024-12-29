from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Sequence, ForeignKey, DateTime
from sqlalchemy.orm import DeclarativeBase, relationship
import pytz

class Base(DeclarativeBase):
    pass

# Trail Table
class Trail(Base):
    __tablename__ = 'trail'

    TrailID = Column(Integer, Sequence('trail_id_seq'), primary_key=True)
    Trail_name = Column(String, nullable=False)
    Trail_Summary = Column(String)
    Trail_Description = Column(String)
    Difficulty = Column(String)
    Location = Column(String)
    Length = Column(Float)
    Elevation_gain = Column(Float)
    Route_type = Column(String)
    OwnerID = Column(Integer, ForeignKey('user.UserID'))
    timestamp = Column(
        DateTime, default=lambda: datetime.now(pytz.timezone('Europe/London')),
        onupdate=lambda: datetime.now(pytz.timezone('Europe/London'))
    )

    owner = relationship("User", back_populates="trails")
    features = relationship("TrailFeature", back_populates="trail")

class TrailSchema:
    class Meta:
        model = Trail
        load_instance = True
        include_relationships = True

# Location-Point Table
class LocationPoint(Base):
    __tablename__ = 'location_point'

    Location_Point = Column(Integer, primary_key=True)
    Latitude = Column(Float, nullable=False)
    Longitude = Column(Float, nullable=False)
    Description = Column(String)
    timestamp = Column(
        DateTime, default=lambda: datetime.now(pytz.timezone('Europe/London')),
        onupdate=lambda: datetime.now(pytz.timezone('Europe/London'))
    )

class LocationPointSchema:
    class Meta:
        model = LocationPoint
        load_instance = True

# Trail-LocationPt Table
class TrailLocationPt(Base):
    __tablename__ = 'trail_location_pt'

    TrailID = Column(Integer, ForeignKey('trail.TrailID'), primary_key=True)
    Location_Point = Column(Integer, ForeignKey('location_point.Location_Point'), primary_key=True)
    Order_no = Column(Integer)

class TrailLocationPtSchema:
    class Meta:
        model = TrailLocationPt
        load_instance = True

# Feature Table
class Feature(Base):
    __tablename__ = 'feature'

    Trail_FeatureID = Column(Integer, Sequence('trail_feature_id_seq'), primary_key=True)
    Trail_Feature = Column(String, nullable=False)

class FeatureSchema:
    class Meta:
        model = Feature
        load_instance = True

# Trail-Feature Table
class TrailFeature(Base):
    __tablename__ = 'trail_feature'

    TrailID = Column(Integer, ForeignKey('trail.TrailID'), primary_key=True)
    Trail_FeatureID = Column(Integer, ForeignKey('feature.Trail_FeatureID'), primary_key=True)

    trail = relationship("Trail", back_populates="features")
    feature = relationship("Feature")

class TrailFeatureSchema:
    class Meta:
        model = TrailFeature
        load_instance = True

# User Table
class User(Base):
    __tablename__ = 'user'

    UserID = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    Email_address = Column(String, nullable=False, unique=True)
    Role = Column(String)
    timestamp = Column(
        DateTime, default=lambda: datetime.now(pytz.timezone('Europe/London')),
        onupdate=lambda: datetime.now(pytz.timezone('Europe/London'))
    )

    trails = relationship("Trail", back_populates="owner")

class UserSchema:
    class Meta:
        model = User
        load_instance = True
        include_relationships = True

trail_schema = TrailSchema()
trails_schema = TrailSchema(many=True)
location_point_schema = LocationPointSchema()
location_points_schema = LocationPointSchema(many=True)
trail_location_pt_schema = TrailLocationPtSchema()
trail_location_pts_schema = TrailLocationPtSchema(many=True)
feature_schema = FeatureSchema()
features_schema = FeatureSchema(many=True)
trail_feature_schema = TrailFeatureSchema()
trail_features_schema = TrailFeatureSchema(many=True)
user_schema = UserSchema()
users_schema = UserSchema(many=True)
