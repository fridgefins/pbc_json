# models.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    ForeignKey,
    Table,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Association table for many-to-many between fights and competitors.
fight_competitor_association = Table(
    'fight_competitor',
    Base.metadata,
    Column('fight_id', Integer, ForeignKey('fights.id'), primary_key=True),
    Column('competitor_id', Integer, ForeignKey('competitors.id'), primary_key=True)
)

class Location(Base):
    __tablename__ = 'locations'
    id = Column(Integer, primary_key=True)
    type = Column(String)  # e.g. "Place"
    name = Column(String, nullable=False)
    address = Column(String)
    url = Column(String)
    # One location may host many events.
    events = relationship("Event", back_populates="location")

class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    location_id = Column(Integer, ForeignKey('locations.id'))
    description = Column(String)
    event_url = Column(String)
    event_image = Column(String)
    
    # Ensure that there is only one event for a given date at a specific location.
    __table_args__ = (UniqueConstraint('date', 'location_id', name='_date_location_uc'),)
    
    location = relationship("Location", back_populates="events")
    # An event groups many fights.
    fights = relationship("Fight", back_populates="event", cascade="all, delete-orphan")

class Fight(Base):
    __tablename__ = 'fights'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    url = Column(String)
    image = Column(String)
    event_id = Column(Integer, ForeignKey('events.id'))
    
    event = relationship("Event", back_populates="fights")
    # A fight can involve multiple competitors.
    competitors = relationship("Competitor",
                               secondary=fight_competitor_association,
                               back_populates="fights")

class Competitor(Base):
    __tablename__ = 'competitors'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    given_name = Column(String)
    family_name = Column(String)
    birth_date = Column(DateTime)
    birth_place = Column(String)
    nationality = Column(String)
    weight_value = Column(Float)
    weight_unit = Column(String)
    height_value = Column(Float)
    height_unit = Column(String)
    fighting_out_of_city = Column(String)
    fighting_out_of_state = Column(String)
    nick_name = Column(String)
    image = Column(String)
    bio_image_no_index = Column(String)
    full_body_no_index = Column(String)
    full_body_image = Column(String)
    url = Column(String)
    description = Column(String)
    
    # A competitor may participate in many fights.
    fights = relationship("Fight",
                          secondary=fight_competitor_association,
                          back_populates="competitors")
