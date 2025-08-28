#!/usr/bin/env python3
"""
Entry point python file to start Puzzles Project.

Authors: Emily Vaughn-Kukura and Melanie Kukura
"""
import argparse
import datetime
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import create_engine, Engine, Column, Integer, String, UniqueConstraint, ForeignKey
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.orm import declarative_base, Session, relationship
from sqlalchemy.exc import IntegrityError
from jsonschema import validate, ValidationError

DB_USER = "app"
DB_HOST = "127.0.0.1"
DB_NAME = "puzzles"
DB_PASSWORD_FILE = "password.txt"
SCHEMA_FILE = "ratings_schema.json"

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
class Puzzle(Base):
    __tablename__ = "puzzles"

    id = Column(Integer, primary_key=True)
    puzzle = Column(String, nullable=False)

    ratings = relationship("Rating", back_populates="puzzle")

class Solver(Base):
    __tablename__ = "solvers"

    id = Column(Integer, primary_key=True)
    solver = Column(String, nullable=False)

    ratings = relationship("Rating", back_populates="solver")

class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True)
    solver_id = Column(Integer, ForeignKey("solvers.id"), nullable=False)
    puzzle_id = Column(Integer, ForeignKey("puzzles.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    solver = relationship("Solver", back_populates="ratings")
    puzzle = relationship("Puzzle", back_populates="ratings")

    __table_args__ = (
        UniqueConstraint("solver_id", "puzzle_id", name="solver-and-puzzle"),
    )

### Fast API Application ###
app = FastAPI(
    title="Puzzles  API",
    summary="Kukura Family & Friends Puzzle Ratings",
    version="1",
    servers=[{"url": "/"}],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.globals["now"] = datetime.datetime.now


### UI routes ### 
@app.get("/", response_class=HTMLResponse)
def index():
    return RedirectResponse(url="/puzzles")


@app.get("/puzzles", response_class=HTMLResponse)
def puzzles(request: Request):
    return templates.TemplateResponse("puzzles.html", {"request": request})

@app.get("/puzzles/{puzzle}", response_class=HTMLResponse)
def puzzle_ratings(puzzle: str, request: Request):
    puzzle = puzzle.title()
    return templates.TemplateResponse("puzzle_data.html", {"puzzle": puzzle, "request": request})


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
            puzzles[rating.solver.solver].update({rating.puzzle.puzzle: rating.rating})

    return puzzles


@app.get("/api/solvers/{solver_name}")
def get_solver(solver_name: str):
    solver_to_ratings = {}
    solver_name = solver_name.title()
    with Session(app.engine) as session:
        solver = session.query(Solver).filter_by(solver=solver_name).first()
        if not solver:
            raise HTTPException(status_code=404, detail=f"Solver {solver_name} not found.")
        
        solver_ratings = session.query(Rating).filter_by(solver_id=solver.id).all()
        if not solver_ratings:
            raise HTTPException(status_code=404, detail=f"Solver {solver_name} has not rated any puzzles.")
        
        for rating in solver_ratings:
            solver_to_ratings[rating.puzzle.puzzle] = rating.rating

    return solver_to_ratings


@app.get("/api/puzzles/")
def get_puzzles():
    puzzle_info = defaultdict(list)
    with Session(app.engine) as session:
        ratings = session.query(Rating).all()
        for rating in ratings:
            puzzle_info[rating.puzzle.puzzle].append(rating.rating)

    return puzzle_info


@app.get("/api/puzzles/{puzzle_name}")
def get_puzzle_ratings(puzzle_name: str):
    solver_ratings = {}
    puzzle_name = puzzle_name.title()

    with Session(app.engine) as session:
        puzzle = session.query(Puzzle).filter_by(puzzle=puzzle_name).first()
        if not puzzle:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle_name} not found.")


        puzzle_ratings = session.query(Rating).filter_by(puzzle_id=puzzle.id).all()
        if not puzzle_ratings:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle} has not been rated.")

        for rating in puzzle_ratings:
            solver_ratings[rating.solver.solver] = rating.rating

    return solver_ratings


@app.get("/api/puzzles/{puzzle_name}/{solver_name}")
def get_solver_rating(puzzle_name: str, solver_name: str):
    rating = None
    puzzle_name = puzzle_name.title()
    solver_name = solver_name.title()
    with Session(app.engine) as session:  
        solver = session.query(Solver).filter_by(solver=solver_name).first()
        if not solver:
            raise HTTPException(status_code=404, detail=f"Solver {solver_name} not found.")
        
        puzzle = session.query(Puzzle).filter_by(puzzle=puzzle_name).first()
        if not puzzle:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle_name} not found.")
        
        ratings = session.query(Rating).filter_by(puzzle_id=puzzle.id, solver_id=solver.id).all()
        if not ratings:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle_name} not rated by {solver_name}.")

    rating = ratings[0].rating

    return rating


@app.patch("/api/puzzles/{puzzle_name}/{solver_name}", response_model = SolverEntry)
def update_solver_rating(
    puzzle_name: str,
    solver_name: str,
    rating: int
):
    """
    Update rating of existing puzzle in database.
    Returns dict of solver whose puzzle rating was updated.
    """
    updated_rating_entry = {}
    puzzle_name = puzzle_name.title()
    solver_name = solver_name.title()

    with Session(app.engine) as session:
        puzzle = session.query(Puzzle).filter_by(puzzle=puzzle_name).first()
        if not puzzle:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle_name} not found.")
        
        solver = session.query(Solver).filter_by(solver=solver_name).first()
        if not solver:
            raise HTTPException(status_code=404, detail=f"Solver {solver_name} not found.")

        ratings = session.query(Rating).filter_by(puzzle_id=puzzle.id, solver_id=solver.id).all()
        if not ratings:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle_name} not rated by {solver_name}.")
        
        ratings[0].rating = rating
        session.commit()
        updated_rating_entry[puzzle.puzzle] = ratings[0].rating

    return SolverEntry(name=solver_name, puzzles=updated_rating_entry)


@app.post("/api/puzzles/{puzzle_name}/{solver_name}", response_model = SolverEntry, status_code=201)
def add_puzzle_rating(
    puzzle_name: str,
    solver_name: str,
    rating: int
):
    """"
    Create new rated puzzle entry.
    Returns dict of solver new entry added to.
    """
    updated_rating_entry = {}
    puzzle_name = puzzle_name.title()
    solver_name = solver_name.title()

    with Session(app.engine) as session:      
        try:
            puzzle = session.query(Puzzle).filter_by(puzzle=puzzle_name).first()
            solver = session.query(Solver).filter_by(solver=solver_name).first()

            if not puzzle:
                new_puzzle = Puzzle(puzzle=puzzle_name)
                session.add(new_puzzle)
                session.commit()
                puzzle = new_puzzle

            if not solver:
                new_solver = Solver(solver=solver_name)
                session.add(new_solver)
                session.commit()
                solver = new_solver

            new_rating = Rating(solver_id=solver.id, puzzle_id=puzzle.id, rating=rating)
            session.add(new_rating)
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail=f"Puzzle {puzzle_name} has already been rated by {solver_name}.")

        updated_rating_entry[puzzle.puzzle] = rating


    return SolverEntry(name=solver_name, puzzles=updated_rating_entry)


@app.delete("/api/puzzles/{puzzle_name}/{solver_name}", status_code=204)
def delete_puzzle_rating(
    puzzle_name: str,
    solver_name: str
):
    """
    Delete rated puzzle from solver entry.
    Returns dict of solver puzzle rating deleted from.
    """
    solver_to_ratings = {}
    puzzle_name = puzzle_name.title()
    solver_name = solver_name.title()

    with Session(app.engine) as session:
        puzzle = session.query(Puzzle).filter_by(puzzle=puzzle_name).first()
        if not puzzle:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle_name} not found.")
        
        solver = session.query(Solver).filter_by(solver=solver_name).first()
        if not solver:
            raise HTTPException(status_code=404, detail=f"Solver {solver_name} not found.")

        ratings = session.query(Rating).filter_by(puzzle_id=puzzle.id, solver_id=solver.id).all()
        if not ratings:
            raise HTTPException(status_code=404, detail=f"Puzzle {puzzle_name} not rated by {solver_name}.")
            
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
    for solver_name, puzzle_ratings in puzzles_by_solver.items():
        solver = session.query(Solver).filter_by(solver=solver_name).first()
        if not solver:
            solver = Solver(solver=solver_name)
            session.add(solver)
            session.flush()

        for puzzle_name, value in puzzle_ratings.items():
            puzzle = session.query(Puzzle).filter_by(puzzle=puzzle_name).first()
            if not puzzle:
                puzzle = Puzzle(puzzle=puzzle_name)
                session.add(puzzle)
                session.flush()

            rating = session.query(Rating).filter_by(solver_id=solver.id, puzzle_id=puzzle.id).first()
            if not rating:
                rating = Rating(solver=solver, puzzle=puzzle, rating=value)
                session.add(rating)
            else:
                rating.rating = value


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

# def update_json_data(engine: Engine):
#     updated_solver_data = []
#     with Session(engine) as session:
#         solvers = session.query(Rating.solver).distinct()
#         for solver_name in solvers:
#             solver_entry = {}
#             solver_ratings = session.query(Rating).filter_by(solver=solver_name[0]).all()
#             solver_entry["name"] = solver_name[0]
#             solver_entry["puzzles"] = {}
#             for puzzle_rating in solver_ratings:
#                 solver_entry["puzzles"][puzzle_rating.puzzle] = puzzle_rating.rating

#             updated_solver_data.append(solver_entry)
    
#         with open("example_files/fam_fav_puzzles.json", "w") as puzzle_file:
#             json.dump(updated_solver_data, puzzle_file, indent=2)

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
    # Save database updates back to json file
    # update_json_data(engine)
    
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
