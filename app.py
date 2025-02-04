# app.py
from flask import Flask
from flask_graphql import GraphQLView
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os
from models import Base
from schema import schema

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://fridge:Matt!!5452@localhost:5432/pbc")

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

app = Flask(__name__)

app.add_url_rule(
    '/graphql',
    view_func=GraphQLView.as_view(
        'graphql',
        schema=schema,
        graphiql=True,
        get_context=lambda: {"session": Session()}
    )
)

@app.teardown_appcontext
def shutdown_session(exception=None):
    Session.remove()

if __name__ == '__main__':
    app.run(debug=True)
