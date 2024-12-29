from sqlalchemy import create_engine, Column, Integer, String, Float, Sequence, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

# Trail Table
class Trail(Base):
    __tablename__ = 'trail'

    TrailID = Column(Integer, Sequence('trail_id_seq'), primary_key=True)
    Trail_name = Column(String)
    Trail_Summary = Column(String)
    Trail_Description = Column(String)
    Difficulty = Column(String)
    Location = Column(String)
    Length = Column(Float)
    Elevation_gain = Column(Float)
    Route_type = Column(String)
    OwnerID = Column(Integer, ForeignKey('user.UserID'))

    owner = relationship("User", back_populates="trails")
    features = relationship("TrailFeature", back_populates="trail")

# Location-Point Table
class LocationPoint(Base):
    __tablename__ = 'location_point'

    Location_Point = Column(Integer, primary_key=True)
    Latitude = Column(Float)
    Longitude = Column(Float)
    Description = Column(String)

# Trail-LocationPt Table
class TrailLocationPt(Base):
    __tablename__ = 'trail_location_pt'

    TrailID = Column(Integer, ForeignKey('trail.TrailID'), primary_key=True)
    Location_Point = Column(Integer, ForeignKey('location_point.Location_Point'), primary_key=True)
    Order_no = Column(Integer)

# Feature Table
class Feature(Base):
    __tablename__ = 'feature'

    Trail_FeatureID = Column(Integer, Sequence('trail_feature_id_seq'), primary_key=True)
    Trail_Feature = Column(String)

# Trail-Feature Table
class TrailFeature(Base):
    __tablename__ = 'trail_feature'

    TrailID = Column(Integer, ForeignKey('trail.TrailID'), primary_key=True)
    Trail_FeatureID = Column(Integer, ForeignKey('feature.Trail_FeatureID'), primary_key=True)

    trail = relationship("Trail", back_populates="features")
    feature = relationship("Feature")

# User Table
class User(Base):
    __tablename__ = 'user'

    UserID = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    Email_address = Column(String)
    Role = Column(String)

    trails = relationship("Trail", back_populates="owner")

# Database Initialization
def init_db():
    engine = create_engine('sqlite:///trail_database.db')  # Replace with your database URL
    Base.metadata.create_all(engine)
    return engine

if __name__ == '__main__':
    engine = init_db()
    Session = sessionmaker(bind=engine)
    session = Session()

    # Example: Adding a user
    new_user = User(Email_address="user@example.com", Role="admin")
    session.add(new_user)
    session.commit()

    print("Database initialized and example data added.")
