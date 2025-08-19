#!/usr/bin/env python3
"""
Entry point python file to start Puzzles Project.

Authors: Emily Vaughn-Kukura and Melanie Kukura
"""
import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Engine, Column, Integer, String, UniqueConstraint
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.exc import IntegrityError
from jsonschema import validate, ValidationError

DB_USER = "app"
DB_HOST = "127.0.0.1"
DB_NAME = "puzzles"
DB_PASSWORD_FILE = "password.txt"
SCHEMA_FILE = "ratings_schema.json"
from pydantic import BaseModel


ALL="all"

class PersonEntry(BaseModel):
    """Pydantic response model for API patch/post/delete methods"""
    name: str
    puzzles: Dict[str, int]

class PersonNotFoundError(Exception):
    """Custom exception for person not found."""
    def __init__(self, person_name):
        self.person_name = person_name
        self.message = f"Person {self.person_name} not found."
        super().__init__(self.message)

### DB ###
Base = declarative_base()

# Define table schema
class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True)
    person = Column(String, nullable=False)
    puzzle = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("person", "puzzle", name="person-and-puzzle"),
    )

### Fast API Application ###
app = FastAPI(
    title="Puzzles  API",
    summary="Kukura Family & Friends Puzzle Ratings",
    version="1",
    servers=[{"url": "/"}],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/favicon.ico")
def favicon():
    return FileResponse("static/favicon.ico")


### API endpoints ###
@app.get("/api/people/")
def get_people():
    puzzles = defaultdict(dict)
    with Session(app.engine) as session:
        ratings = session.query(Rating).all()
        for rating in ratings:
            puzzles[rating.person].update({rating.puzzle: rating.rating})

    return puzzles


@app.get("/api/people/{person_name}")
def get_person(person_name: str):
    person_to_ratings = {}
    person_name = person_name.title()
    with Session(app.engine) as session:  
        person_ratings = session.query(Rating).filter_by(person=person_name).all()
        if not person_ratings:
            raise HTTPException(status_code=404, detail=f"Person {person_name} not found.")
        
        for rating in person_ratings:
            person_to_ratings[rating.puzzle] = rating.rating

    return person_to_ratings


@app.get("/api/puzzles/")
def get_puzzles():
    puzzles = []
    with Session(app.engine) as session:
        puzzle_results = session.query(Rating.puzzle).distinct().all()
        # When you query a single attribute you still get back a tuple (1-tuple)
        # For example: puzzle_results =[('Ticket to ride',), ('Risk',), ...]
        puzzles = [puzzle[0] for puzzle in puzzle_results]

    return puzzles


@app.get("/api/puzzles/{puzzle}")
def get_puzzle_ratings(puzzle: str):
    puzzle = puzzle.title()
    person_ratings = {}

    with Session(app.engine) as session:  
        puzzle_ratings = session.query(Rating).filter_by(puzzle=puzzle).all()
        if not puzzle_ratings:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle} not found.")

        for rating in puzzle_ratings:
            person_ratings[rating.person] = rating.rating

    return person_ratings


@app.get("/api/puzzles/{puzzle}/{person_name}")
def get_person_rating(puzzle: str, person_name: str):
    person_name = person_name.title()
    puzzle = puzzle.title()
    rating = None
    with Session(app.engine) as session:  
        ratings = session.query(Rating).filter_by(puzzle=puzzle, person=person_name).all()
        if not ratings:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle} not rated by {person_name}.")

    rating = ratings[0].rating

    return rating

@app.patch("/api/puzzles/{puzzle}/{person_name}", response_model = PersonEntry)
def update_person_rating(
    puzzle: str,
    person_name: str,
    rating: int
):
    """
    Update rating of existing puzzle in database.
    Returns dict of person whose puzzle rating was updated.
    """
    puzzle = puzzle.title()
    person_name = person_name.title()
    updated_rating_entry = {}

    with Session(app.engine) as session:
        ratings = session.query(Rating).filter_by(puzzle=puzzle, person=person_name).all()

        if not ratings:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle} not rated by {person_name}.")
        
        ratings[0].rating = rating
        session.commit()
        updated_rating_entry[puzzle] = ratings[0].rating

    return PersonEntry(name=person_name, puzzles=updated_rating_entry)

@app.post("/api/puzzles/{puzzle}/{person_name}", response_model = PersonEntry, status_code=201)
def add_puzzle_rating(
    puzzle: str,
    person_name: str,
    rating: int
):
    """"
    Create new rated puzzle entry.
    Returns dict of person new entry added to.
    """
    puzzle = puzzle.title()
    person_name = person_name.title()
    updated_rating_entry = {}

    with Session(app.engine) as session:      
        try:
            new_rating = Rating(person=person_name, puzzle=puzzle, rating=rating)
            session.add(new_rating)
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail=f"Puzzle {puzzle} has already been rated by {person_name}.")

        updated_rating_entry[puzzle] = rating


    return PersonEntry(name=person_name, puzzles=updated_rating_entry)

@app.delete("/api/puzzles/{puzzle}/{person_name}", status_code=204)
def delete_puzzle_rating(
    puzzle: str,
    person_name: str
):
    """
    Delete rated puzzle from person entry.
    Returns dict of person puzzle rating deleted from.
    """
    puzzle = puzzle.title()
    person_name = person_name.title()
    person_to_ratings = {}

    with Session(app.engine) as session:
        ratings = session.query(Rating).filter_by(puzzle=puzzle, person=person_name).all()
        if not ratings:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle} not rated by {person_name}.")
            
        session.delete(ratings[0])
        session.commit()

    return


### Database Methods ###
def connect_to_database() -> Engine:
    current_dir = Path(__file__).parent
    password_path = current_dir / "password.txt"
    db_password: str = ""
    with password_path.open() as f:
        db_password = f.read()  

    url = f"postgresql://{DB_USER}:{db_password}@{DB_HOST}/{DB_NAME}"
    engine = create_engine(url)
    return engine


def ensure_puzzle_database(engine: Engine):
    if not database_exists(engine.url):
        create_database(engine.url)
        print(f"Initialized database {DB_NAME}")


def add_ratings(puzzles_by_person: Dict, session: Session):
    for person, puzzle_ratings in puzzles_by_person.items():
        for puzzle, value in puzzle_ratings.items():
            rating = Rating(person=person, puzzle=puzzle, rating=value)
            session.add(rating)


def initialize_ratings_table(engine, puzzles_by_person: dict):
    """
    Initialize table in db from the `puzzles_by_person` mapping
    puzzles_by_person maps person_name -> {puzzle -> rating}
    """
    # Ensure table exists
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        add_ratings(puzzles_by_person, session)

        try:
            session.commit()
        except IntegrityError as e:
            print(f"Commit failed: {e}")


### Supporting functions ###
def parse_people_file(filename, ext) -> list:
    """
    Returns dict created from loaded file.
    Key -> Person, Value -> Fav puzzles list.
    Returns empty dict if filename is improper.
    """

    people_puzzles_list = []

    # Check for csv or json file type
    if (ext != ".json"):
        msg = "Sorry, this file type is not accepted. No new person info entered into database."
        raise ValueError(msg)
    
    # Open and save ratings schema for validation
    with open(SCHEMA_FILE) as schema_file:
        schema = json.load(schema_file)

    # Open file and create new people dict
    with open(filename) as upload_file:
        people_list = json.load(upload_file)

        # Check for valid file schema
        validate(instance=people_list, schema=schema)

        for person_dict in people_list:
            person_dict["name"] = person_dict["name"].title()
            person_dict["puzzles"] = {puzzle.title(): rating for puzzle, rating in person_dict["puzzles"].items()}
            people_puzzles_list.append(person_dict)
            
        return people_puzzles_list


def create_puzzles_by_person(people_puzzles_list):
    """
    Create dict of people and rated
    puzzles keyed by person.
    """
    
    puzzles_by_person = {}
    for person in people_puzzles_list:
        puzzles_by_person[person["name"]] = person["puzzles"]
    
    return puzzles_by_person


### Main application loop ###
def run(engine: Engine, args: argparse.Namespace):

    ensure_puzzle_database(engine)

    people_puzzles_list = []

    # Check for existence of path
    if os.path.exists(args.file):
        _, extension = os.path.splitext(args.file)
        people_puzzles_list = parse_people_file(args.file, extension)
    else:
        raise FileNotFoundError(f"File not found: {args.file}")
    
    # Check if people exist in dict
    if not people_puzzles_list:
        msg = "No people found in provided file."
        raise ValueError(msg)
    
    # Create different maps for endpoint access
    puzzles_by_person = create_puzzles_by_person(people_puzzles_list)

    # Database connection
    app.engine = engine

    initialize_ratings_table(engine, puzzles_by_person)

    # Start server
    uvicorn.run(app, host="localhost", port=args.port)


def shutdown(engine: Engine):
    with Session(engine) as session:
        # Clear out table entries on shutdown.
        session.query(Rating).delete()
        session.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)

    # Add arguments
    parser.add_argument("--port", type=int, default=8080, help="Port number to run the server on")
    parser.add_argument("-f","--file",  default="example_files/fam_fav_puzzles.json", help="Person favorite puzzles file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity")

    # Parse arguments
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    engine = connect_to_database()
    try:
        run(engine, args)
    except (FileNotFoundError, PersonNotFoundError, ValueError, ValidationError) as e:
        print(e)
    finally:
        shutdown(engine)
