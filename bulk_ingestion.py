import json
from datetime import datetime
import json  # used for converting dictionaries to JSON strings when needed
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Location, Event, Fight, Competitor

# Replace with your actual database connection string.
DATABASE_URL = "postgresql://fridge:Matt!!5452@localhost:5432/pbc"

# Set up the SQLAlchemy engine and session.
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)  # Create tables if they don't exist.
Session = sessionmaker(bind=engine)
session = Session()

# Path to the JSON file containing fights.
json_file_path = "fights.json"

with open(json_file_path, "r") as f:
    fights_data = json.load(f)

for fight_data in fights_data:
    try:
        # Extract basic fight details.
        fight_title = fight_data.get("title")
        fight_description = fight_data.get("description")
        fight_date_str = fight_data.get("date")
        fight_date = datetime.fromisoformat(fight_date_str)
        fight_url = fight_data.get("url")
        fight_image = fight_data.get("image")
        
        # Process the location.
        loc_data = fight_data.get("location", {})
        loc_name = loc_data.get("name")
        loc_address = loc_data.get("address")
        
        # Look up an existing location by name and address.
        location = session.query(Location).filter_by(
            name=loc_name
        ).first()
        if not location:
            location = Location(
                name=loc_name,
                address=loc_address,
                url=loc_data.get("sameAs")
            )
            session.add(location)
            session.commit()  # Commit to get an ID for the location.
        
        # Look up an existing event for this date and location.
        event = session.query(Event).filter_by(
            date=fight_date,
            location_id=location.id
        ).first()
        if not event:
            event = Event(
                date=fight_date,
                location=location,
                description=fight_data.get("eventDescription")  # Optional event-level description.
            )
            session.add(event)
            session.commit()  # Commit to get an ID for the event.
        
        # Check if a fight with the same title already exists for this event.
        existing_fight = session.query(Fight).filter_by(
            title=fight_title,
            event_id=event.id
        ).first()
        if existing_fight:
            print(f"Fight '{fight_title}' already exists for the event on {fight_date}. Skipping.")
            continue  # Skip to the next fight.
        
        # Create the new Fight record.
        fight = Fight(
            title=fight_title,
            description=fight_description,
            event=event,
            url=fight_url,
            image=fight_image
        )
        session.add(fight)
        session.commit()  # Commit to get an ID for the fight.
        
        competitor_instances = []
        for comp_data in fight_data.get("competitors", []):
            # Convert competitor's birth date (assumed to be ISO format) into a datetime object.
            comp_birth_date = datetime.fromisoformat(comp_data.get("birthDate"))
            
            # Check if a competitor already exists (using name and birth date as unique identifiers).
            existing_competitor = session.query(Competitor).filter_by(
                name=comp_data.get("name"),
                birth_date=comp_birth_date
            ).first()
            if existing_competitor:
                competitor_instance = existing_competitor
            else:
                # If the competitor doesn't exist, create a new record.
                # Convert work_location to a JSON string if it is a dict.
                work_location = comp_data.get("workLocation")
                if isinstance(work_location, dict):
                    work_location = json.dumps(work_location)
                
                competitor_instance = Competitor(
                    name=comp_data.get("name"),
                    given_name=comp_data.get("givenName"),
                    family_name=comp_data.get("familyName"),
                    birth_date=comp_birth_date,
                    birth_place=comp_data.get("birthPlace"),
                    nationality=comp_data.get("nationality"),
                    weight_value=comp_data.get("weight").get("value"),
                    weight_unit=comp_data.get("weight").get("unitText "),
                    height_value=comp_data.get("height").get("value"),
                    height_unit=comp_data.get("height").get("unitText "),
                    fighting_out_of_city=comp_data.get("workLocation").get("addressLocality"),
                    fighting_out_of_state=comp_data.get("workLocation").get("addressRegion"),
                    nick_name=comp_data.get("additionalName"),
                    image=comp_data.get("image"),
                    url=comp_data.get("url"),
                    description=comp_data.get("description")
                )
                session.add(competitor_instance)
                session.commit()  # Commit to assign an ID.
            competitor_instances.append(competitor_instance)
        
        # Associate the competitors with the fight (many-to-many relationship).
        fight.competitors = competitor_instances
        session.commit()
        print(f"Ingested fight '{fight_title}' successfully.")
    
    except Exception as e:
        session.rollback()
        print(f"Error ingesting fight '{fight_data.get('title')}', error: {e}")

session.close()