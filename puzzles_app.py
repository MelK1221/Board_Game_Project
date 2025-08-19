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

class SolverEntry(BaseModel):
    """Pydantic response model for API patch/post/delete methods"""
    name: str
    puzzles: Dict[str, int]

class SolverNotFoundError(Exception):
    """Custom exception for solver not found."""
    def __init__(self, solver_name):
        self.solver_name = solver_name
        self.message = f"Solver {self.solver_name} not found."
        super().__init__(self.message)

### DB ###
Base = declarative_base()

# Define table schema
class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True)
    solver = Column(String, nullable=False)
    puzzle = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("solver", "puzzle", name="solver-and-puzzle"),
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
@app.get("/api/solvers/")
def get_solvers():
    puzzles = defaultdict(dict)
    with Session(app.engine) as session:
        ratings = session.query(Rating).all()
        for rating in ratings:
            puzzles[rating.solver].update({rating.puzzle: rating.rating})

    return puzzles


@app.get("/api/solvers/{solver_name}")
def get_solver(solver_name: str):
    solver_to_ratings = {}
    solver_name = solver_name.title()
    with Session(app.engine) as session:  
        solver_ratings = session.query(Rating).filter_by(solver=solver_name).all()
        if not solver_ratings:
            raise HTTPException(status_code=404, detail=f"Solver {solver_name} not found.")
        
        for rating in solver_ratings:
            solver_to_ratings[rating.puzzle] = rating.rating

    return solver_to_ratings


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
    solver_ratings = {}

    with Session(app.engine) as session:  
        puzzle_ratings = session.query(Rating).filter_by(puzzle=puzzle).all()
        if not puzzle_ratings:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle} not found.")

        for rating in puzzle_ratings:
            solver_ratings[rating.solver] = rating.rating

    return solver_ratings


@app.get("/api/puzzles/{puzzle}/{solver_name}")
def get_solver_rating(puzzle: str, solver_name: str):
    solver_name = solver_name.title()
    puzzle = puzzle.title()
    rating = None
    with Session(app.engine) as session:  
        ratings = session.query(Rating).filter_by(puzzle=puzzle, solver=solver_name).all()
        if not ratings:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle} not rated by {solver_name}.")

    rating = ratings[0].rating

    return rating

@app.patch("/api/puzzles/{puzzle}/{solver_name}", response_model = SolverEntry)
def update_solver_rating(
    puzzle: str,
    solver_name: str,
    rating: int
):
    """
    Update rating of existing puzzle in database.
    Returns dict of solver whose puzzle rating was updated.
    """
    puzzle = puzzle.title()
    solver_name = solver_name.title()
    updated_rating_entry = {}

    with Session(app.engine) as session:
        ratings = session.query(Rating).filter_by(puzzle=puzzle, solver=solver_name).all()

        if not ratings:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle} not rated by {solver_name}.")
        
        ratings[0].rating = rating
        session.commit()
        updated_rating_entry[puzzle] = ratings[0].rating

    return SolverEntry(name=solver_name, puzzles=updated_rating_entry)

@app.post("/api/puzzles/{puzzle}/{solver_name}", response_model = SolverEntry, status_code=201)
def add_puzzle_rating(
    puzzle: str,
    solver_name: str,
    rating: int
):
    """"
    Create new rated puzzle entry.
    Returns dict of solver new entry added to.
    """
    puzzle = puzzle.title()
    solver_name = solver_name.title()
    updated_rating_entry = {}

    with Session(app.engine) as session:      
        try:
            new_rating = Rating(solver=solver_name, puzzle=puzzle, rating=rating)
            session.add(new_rating)
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail=f"Puzzle {puzzle} has already been rated by {solver_name}.")

        updated_rating_entry[puzzle] = rating


    return SolverEntry(name=solver_name, puzzles=updated_rating_entry)

@app.delete("/api/puzzles/{puzzle}/{solver_name}", status_code=204)
def delete_puzzle_rating(
    puzzle: str,
    solver_name: str
):
    """
    Delete rated puzzle from solver entry.
    Returns dict of solver puzzle rating deleted from.
    """
    puzzle = puzzle.title()
    solver_name = solver_name.title()
    solver_to_ratings = {}

    with Session(app.engine) as session:
        ratings = session.query(Rating).filter_by(puzzle=puzzle, solver=solver_name).all()
        if not ratings:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle} not rated by {solver_name}.")
            
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


def add_ratings(puzzles_by_solver: Dict, session: Session):
    for solver, puzzle_ratings in puzzles_by_solver.items():
        for puzzle, value in puzzle_ratings.items():
            rating = Rating(solver=solver, puzzle=puzzle, rating=value)
            session.add(rating)


def initialize_ratings_table(engine, puzzles_by_solver: dict):
    """
    Initialize table in db from the `puzzles_by_solver` mapping
    puzzles_by_solver maps solver_name -> {puzzle -> rating}
    """
    # Ensure table exists
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        add_ratings(puzzles_by_solver, session)

        try:
            session.commit()
        except IntegrityError as e:
            print(f"Commit failed: {e}")


### Supporting functions ###
def parse_solvers_file(filename, ext) -> list:
    """
    Returns dict created from loaded file.
    Key -> Solver, Value -> Fav puzzles list.
    Returns empty dict if filename is improper.
    """

    solvers_puzzles_list = []

    # Check for csv or json file type
    if (ext != ".json"):
        msg = "Sorry, this file type is not accepted. No new solver info entered into database."
        raise ValueError(msg)
    
    # Open and save ratings schema for validation
    with open(SCHEMA_FILE) as schema_file:
        schema = json.load(schema_file)

    # Open file and create new solvers dict
    with open(filename) as upload_file:
        solvers_list = json.load(upload_file)

        # Check for valid file schema
        validate(instance=solvers_list, schema=schema)

        for solver_dict in solvers_list:
            solver_dict["name"] = solver_dict["name"].title()
            solver_dict["puzzles"] = {puzzle.title(): rating for puzzle, rating in solver_dict["puzzles"].items()}
            solvers_puzzles_list.append(solver_dict)
            
        return solvers_puzzles_list


def create_puzzles_by_solver(solvers_puzzles_list):
    """
    Create dict of solvers and rated
    puzzles keyed by solver.
    """
    
    puzzles_by_solver = {}
    for solver in solvers_puzzles_list:
        puzzles_by_solver[solver["name"]] = solver["puzzles"]
    
    return puzzles_by_solver


### Main application loop ###
def run(engine: Engine, args: argparse.Namespace):

    ensure_puzzle_database(engine)

    solvers_puzzles_list = []

    # Check for existence of path
    if os.path.exists(args.file):
        _, extension = os.path.splitext(args.file)
        solvers_puzzles_list = parse_solvers_file(args.file, extension)
    else:
        raise FileNotFoundError(f"File not found: {args.file}")
    
    # Check if solvers exist in dict
    if not solvers_puzzles_list:
        msg = "No solvers found in provided file."
        raise ValueError(msg)
    
    # Create different maps for endpoint access
    puzzles_by_solver = create_puzzles_by_solver(solvers_puzzles_list)

    # Database connection
    app.engine = engine

    initialize_ratings_table(engine, puzzles_by_solver)

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
    parser.add_argument("-f","--file",  default="example_files/fam_fav_puzzles.json", help="Solver favorite puzzles file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity")

    # Parse arguments
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    engine = connect_to_database()
    try:
        run(engine, args)
    except (FileNotFoundError, SolverNotFoundError, ValueError, ValidationError) as e:
        print(e)
    finally:
        shutdown(engine)
