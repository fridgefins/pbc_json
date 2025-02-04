import argparse
import os
import json
import calendar
import re
import requests
from datetime import datetime
from urllib.parse import urlparse
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, update
from models import Base, Event, Fight, Competitor, Location, fight_competitor_association

DATABASE_URL = "postgresql://fridge:Matt!!5452@100.121.170.87:5432/pbc"

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)  # Ensure tables exist
Session = sessionmaker(bind=engine)
session = Session()


def update_event_urls(session, base_url="https://www.premierboxingchampions.com/fight-night-"):
    """
    For every Event in the database, generate a URL based on the event date and update the event record.
    Assumes Event.date is a datetime and Event has a 'url' column.
    """
    events = session.query(Event).all()
    for event in events:
        # Format the date: month fully spelled out (lowercase), dash, day (2 digits), dash, year.
        event_date = event.date
        month_str = calendar.month_name[event_date.month].lower()
        formatted_date = f"{month_str}-{event_date.day:02d}-{event_date.year}"
        event_url = base_url + formatted_date

        event.event_url = event_url
        print(f"Setting event {event.id} URL to {event_url}")
    
    session.commit()

def update_event_image_urls(session):
    """
    For each event, choose an image URL based on its associated fights.
    - If one fight: use its image.
    - If multiple: if any image appears more than once, use that.
    - Else: use the first fight's image.
    """
    events = session.query(Event).all()
    for event in events:
        fight_images = [fight.image for fight in event.fights if fight.image]
        if not fight_images:
            print(f"Event {event.id} has no fight images; skipping.")
            continue

        chosen_image = None
        if len(fight_images) == 1:
            chosen_image = fight_images[0]
        else:
            # Count frequency of each image URL.
            counts = {}
            for img in fight_images:
                counts[img] = counts.get(img, 0) + 1
            # Check if any image occurs more than once.
            for img, count in counts.items():
                if count > 1:
                    chosen_image = img
                    break
            # Otherwise, fallback to the first image.
            if not chosen_image:
                chosen_image = fight_images[0]

        event.event_image = chosen_image
        print(f"Setting event {event.id} image to {chosen_image}")
    
    session.commit()

def update_competitor_image_variants(session):
    """
    For each competitor whose image URL contains "BioImage", generate additional image URL variants:
      - A "FullBody" version (substitute "FullBody" for "BioImage").
      - If the URL ends with a pattern like _1 (or -1) before the extension, also generate versions without the numeric suffix.
    The generated URLs are stored in additional columns on the Competitor.
    (You may need to add these columns to your model and database.)
    """
    competitors = session.query(Competitor).all()
    for comp in competitors:
        original_url = comp.image
        if original_url and "BioImage" in original_url:
            # Replace BioImage with FullBody.
            full_body_url = original_url.replace("BioImage", "FullBody")
            
            # Check if there is a numeric suffix in the filename.
            # Example pattern: BioImage_Davis_1.jpg or BioImage-Davis-1.jpg
            pattern = r"(BioImage[_-].+?)([_-](\d+))(\.\w+)$"
            match = re.search(pattern, original_url)
            if match:
                base_part = match.group(1)  # e.g. "BioImage_Davis"
                num_part = match.group(2)   # e.g. "_1"
                ext = match.group(4)        # e.g. ".jpg"
                # Generate additional variants.
                bio_image_no_index = base_part + ext  # e.g. "BioImage_Davis.jpg"
                full_body_no_index = base_part.replace("BioImage", "FullBody") + ext  # "FullBody_Davis.jpg"
                full_body_with_index = full_body_url  # Already computed above.
                
                # Update competitor with these values (assuming these columns exist).
                comp.bio_image_no_index = bio_image_no_index
                comp.full_body_image = full_body_with_index
                comp.full_body_no_index = full_body_no_index
                print(f"Competitor {comp.id}: generated variants: {bio_image_no_index}, {full_body_with_index}, {full_body_no_index}")
            else:
                # No numeric suffix – simply set the full_body variant.
                comp.full_body_image = full_body_url
                print(f"Competitor {comp.id}: set full_body_image to {full_body_url}")
    
    session.commit()

def fetch_images_by_type(session, record_type, output_dir="images"):
    """
    Fetches images for the specified record type (fighters, fights, locations, or events).
    The image URL field is assumed to be 'image'. Files are saved as {record_type}_{id}.{ext}.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Map type names to model classes and a query.
    model_map = {
        "fighters": Competitor,
        "fights": Fight,
        "locations": Location,
        "events": Event,
    }
    
    if record_type not in model_map:
        print(f"Unknown type: {record_type}")
        return
    
    Model = model_map[record_type]
    records = session.query(Model).all()
    
    for record in records:
        image_url = getattr(record, "image", None)
        if not image_url:
            continue
        
        # Parse the URL to determine file extension.
        parsed = urlparse(image_url)
        filename = os.path.basename(parsed.path)
        ext = os.path.splitext(filename)[1]
        
        local_filename = f"{record_type}_{record.id}{ext}"
        local_path = os.path.join(output_dir, local_filename)
        
        if os.path.exists(local_path):
            print(f"Image for {record_type} {record.id} already exists locally.")
            continue
        
        try:
            print(f"Fetching image for {record_type} {record.id} from {image_url}...")
            r = requests.get(image_url, stream=True, timeout=10)
            r.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            print(f"Saved to {local_path}")
            # Optionally, update the record with the local file path.
            setattr(record, "local_image_path", local_path)
            session.commit()
        except Exception as e:
            print(f"Error fetching image for {record_type} {record.id}: {e}")

def clean_column_data(session, Model, column_name, target, replacement=""):
    """
    Update all records of the given Model, replacing occurrences of 'target' with 'replacement'
    in the specified column.
    """
    col = getattr(Model, column_name)
    stmt = update(Model).values({column_name: col.replace(target, replacement)})
    session.execute(stmt)
    session.commit()
    print(f"Updated {Model.__tablename__}.{column_name}: replaced '{target}' with '{replacement}'.")

def standardize_fight_titles():
    """Updates fight titles to use full fighter names instead of just last names."""
    fights = session.query(Fight).all()
    for fight in fights:
        if len(fight.competitors) == 2:
            comp1, comp2 = fight.competitors
            new_title = f"{comp1.given_name} {comp1.family_name} vs. {comp2.given_name} {comp2.family_name}"
            if fight.title != new_title:
                print(f"Updating fight {fight.id} title: '{fight.title}' -> '{new_title}'")
                fight.title = new_title
    session.commit()

def main():
    parser = argparse.ArgumentParser(description="Manage fight event data.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("update_event_urls", help="Generate and update event URLs.")
    subparsers.add_parser("update_event_images", help="Update event images based on fights.")
    subparsers.add_parser("update_competitor_images", help="Generate additional fighter image URLs.")
    subparsers.add_parser("standardize_fight_titles", help="Ensure fight titles follow full-name format.")

    fetch_parser = subparsers.add_parser("fetch_images", help="Fetch images by type.")
    fetch_parser.add_argument("type", choices=["fighters", "fights", "locations", "events"], help="Type of images to fetch.")
    fetch_parser.add_argument("--output-dir", type=str, default="images", help="Directory to save images.")

    clean_parser = subparsers.add_parser("clean_data", help="Clean unwanted characters from a column.")
    clean_parser.add_argument("model", choices=["fighters", "fights", "events", "locations"], help="Model name.")
    clean_parser.add_argument("column", type=str, help="Column to clean.")
    clean_parser.add_argument("target", type=str, help="Substring to remove.")
    clean_parser.add_argument("--replacement", type=str, default="", help="Replacement string.")

    args = parser.parse_args()
    if args.command == "update_event_urls":
        update_event_urls(session)
    elif args.command == "update_event_images":
        update_event_image_urls(session)
    elif args.command == "update_competitor_images":
        update_competitor_image_variants(session)
    elif args.command == "fetch_images":
        fetch_images_by_type(session, args.type, args.output_dir)
    elif args.command == "clean_data":
        clean_column_data(session, args.model, args.column, args.target, args.replacement)
    elif args.command == "standardize_fight_titles":
        standardize_fight_titles()

if __name__ == "__main__":
    main()
