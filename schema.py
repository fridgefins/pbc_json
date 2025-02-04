# schema.py
import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType
from models import Location, Event, Fight, Competitor
from datetime import datetime

class LocationType(SQLAlchemyObjectType):
    class Meta:
        model = Location

class EventType(SQLAlchemyObjectType):
    class Meta:
        model = Event

class FightType(SQLAlchemyObjectType):
    class Meta:
        model = Fight

class CompetitorType(SQLAlchemyObjectType):
    class Meta:
        model = Competitor

class LocationInput(graphene.InputObjectType):
    type = graphene.String(required=False)  # Optional; you might supply a default
    name = graphene.String(required=True)
    address = graphene.String(required=False)
    url = graphene.String(required=False)

class CompetitorInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    givenName = graphene.String(required=True)
    familyName = graphene.String(required=True)
    birthDate = graphene.String(required=False)  # ISO formatted date string
    birthPlace = graphene.String(required=False)
    nationality = graphene.String(required=False)
    weightValue = graphene.Float(required=False)
    weightUnit = graphene.String(required=False)
    heightValue = graphene.Float(required=False)
    heightUnit = graphene.String(required=False)
    workLocation = graphene.String(required=False)
    additionalName = graphene.String(required=False)
    image = graphene.String(required=False)
    url = graphene.String(required=False)
    description = graphene.String(required=False)

class FightInput(graphene.InputObjectType):
    title = graphene.String(required=True)
    description = graphene.String(required=False)
    date = graphene.String(required=True)  # The fight's date in ISO format
    location = LocationInput(required=True)
    competitors = graphene.List(CompetitorInput, required=True)

class CreateFight(graphene.Mutation):
    class Arguments:
        input = FightInput(required=True)
    
    fight = graphene.Field(lambda: FightType)
    
    def mutate(self, info, input):
        session = info.context.get("session")
        
        # Convert the fight's date from string to datetime.
        fight_date = datetime.fromisoformat(input.date)
        
        # Handle Location: try to find an existing location record by name & address.
        loc_input = input.location
        location = session.query(Location).filter_by(
            name=loc_input.name,
            address=loc_input.address
        ).first()
        if not location:
            location = Location(
                type=loc_input.type,
                name=loc_input.name,
                address=loc_input.address,
                same_as=loc_input.sameAs
            )
            session.add(location)
            session.commit()  # Commit to obtain the location.id
        
        # Look for an existing event with the same date and location.
        event = session.query(Event).filter_by(
            date=fight_date,
            location_id=location.id
        ).first()
        if not event:
            event = Event(
                date=fight_date,
                location=location,
                description=None  # You could optionally set an event description
            )
            session.add(event)
            session.commit()
        
        # Create the Fight instance.
        fight_instance = Fight(
            title=input.title,
            description=input.description,
            event=event
        )
        session.add(fight_instance)
        
        # Process competitors.
        competitor_instances = []
        for comp_input in input.competitors:
            comp_birth_date = datetime.fromisoformat(comp_input.birthDate)
            competitor = Competitor(
                name=comp_input.name,
                given_name=comp_input.givenName,
                family_name=comp_input.familyName,
                birth_date=comp_birth_date,
                birth_place=comp_input.birthPlace,
                nationality=comp_input.nationality,
                weight_value=comp_input.weightValue,
                weight_unit=comp_input.weightUnit,
                height_value=comp_input.heightValue,
                height_unit=comp_input.heightUnit,
                work_location=comp_input.workLocation,
                additional_name=comp_input.additionalName,
                image=comp_input.image,
                url=comp_input.url,
                description=comp_input.description
            )
            session.add(competitor)
            session.commit()  # Commit to get an ID
            competitor_instances.append(competitor)
        
        # Associate the competitors with the fight.
        fight_instance.competitors = competitor_instances
        session.commit()
        
        return CreateFight(fight=fight_instance)

class Mutation(graphene.ObjectType):
    create_fight = CreateFight.Field()

class Query(graphene.ObjectType):
    # Field to retrieve a list of events
    events = graphene.List(EventType)
    
    # Field to retrieve a single event by ID
    event = graphene.Field(EventType, id=graphene.ID(required=True))
    
    def resolve_events(self, info):
        session = info.context.get("session")
        return session.query(Event).all()

    def resolve_event(self, info, id):
        session = info.context.get("session")
        return session.query(Event).filter_by(id=id).first()

schema = graphene.Schema(query=Query, mutation=Mutation)
