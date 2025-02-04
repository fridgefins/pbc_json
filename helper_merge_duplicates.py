import argparse
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, update
from models import Location, Event, Base

# Replace with your actual database connection string.
DATABASE_URL = "postgresql://fridge:Matt!!5452@localhost:5432/pbc"


# Set up SQLAlchemy engine and session.
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)  # Ensure tables exist
Session = sessionmaker(bind=engine)
session = Session()

def merge_locations(primary_location_id, duplicate_location_ids):
    """
    Merges multiple duplicate locations into a primary location.
    Updates events to reference the primary location and removes duplicate locations.

    :param primary_location_id: The ID of the location that will be kept.
    :param duplicate_location_ids: A list of IDs for locations that should be merged into the primary.
    """
    try:
        # Step 1: Update events that reference the duplicate locations
        session.execute(
            update(Event)
            .where(Event.location_id.in_(duplicate_location_ids))
            .values(location_id=primary_location_id)
        )
        session.commit()
        print(f"✅ Updated event references to location ID {primary_location_id}")

        # Step 2: Delete the duplicate locations after events have been reassigned
        session.query(Location).filter(Location.id.in_(duplicate_location_ids)).delete(synchronize_session=False)
        session.commit()
        print(f"✅ Deleted duplicate locations: {duplicate_location_ids}")

    except Exception as e:
        session.rollback()
        print(f"❌ Error merging locations: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge duplicate locations in the database.")
    parser.add_argument("primary_location_id", type=int, help="ID of the primary location to keep.")
    parser.add_argument("duplicate_location_ids", type=int, nargs="+", help="IDs of locations to merge into the primary.")
    
    args = parser.parse_args()
    
    print(f"📌 Merging locations: {args.duplicate_location_ids} into {args.primary_location_id}...")
    merge_locations(args.primary_location_id, args.duplicate_location_ids)

    session.close()