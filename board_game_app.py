#!/usr/bin/env python3
"""
Entry point python file to start Board Game Project.

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
from sqlalchemy import create_engine, Engine, Column, Integer, String, UniqueConstraint
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.exc import IntegrityError
from jsonschema import validate, ValidationError
from pydantic import BaseModel

DB_USER = "app"
DB_HOST = "127.0.0.1"
DB_NAME = "board_games"
DB_PASSWORD_FILE = "password.txt"
SCHEMA_FILE = "ratings_schema.json"


ALL="all"

class PlayerEntry(BaseModel):
    """Pydantic response model for API patch/post/delete methods"""
    name: str
    games: Dict[str, int]

class PlayerNotFoundError(Exception):
    """Custom exception for player not found."""
    def __init__(self, player_name):
        self.player_name = player_name
        self.message = f"Player {self.player_name} not found."
        super().__init__(self.message)

### DB ###
Base = declarative_base()

# Define table schema
class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True)
    player = Column(String, nullable=False)
    game = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("player", "game", name="player-and-game"),
    )

### Fast API Application ###
app = FastAPI(
    title="Board Games API",
    summary="Kukura Family & Friends Board Game Ratings",
    version="1",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
templates.env.globals["now"] = datetime.datetime.now

### UI routes ### 
@app.get("/", response_class=HTMLResponse)
def index():
    return RedirectResponse(url="/games")

@app.get("/games", response_class=HTMLResponse)
def games(request: Request):
    return templates.TemplateResponse("games.html", {"request": request})


@app.get("/favicon.ico")
def favicon():
    return FileResponse("static/favicon.ico")


### API endpoints ###
@app.get("/api/players/")
def get_players():
    games_by_player = defaultdict(dict)
    with Session(app.engine) as session:
        ratings = session.query(Rating).all()
        for rating in ratings:
            games_by_player[rating.player].update({rating.game: rating.rating})

    return games_by_player


@app.get("/api/players/{player_name}")
def get_player(player_name: str):
    player_to_ratings = {}
    player_name = player_name.capitalize()
    with Session(app.engine) as session:  
        player_ratings = session.query(Rating).filter_by(player=player_name).all()
        if not player_ratings:
            raise HTTPException(status_code=404, detail=f"Player {player_name} not found.")
        
        for rating in player_ratings:
            player_to_ratings[rating.game] = rating.rating

    return player_to_ratings


@app.get("/api/games/")
def get_games():
    games = []
    with Session(app.engine) as session:
        ratings = session.query(Rating).all()
        game_info = defaultdict(list)
        for rating in ratings:
            game_info[rating.game].append(rating.rating)

    return game_info


@app.get("/api/games/{game}")
def get_game_ratings(game: str):
    game = game.capitalize()
    player_ratings = {}

    with Session(app.engine) as session:  
        game_ratings = session.query(Rating).filter_by(game=game).all()
        if not game_ratings:
            raise HTTPException(status_code=404, detail=f"Game {game} not found.")

        for rating in game_ratings:
            player_ratings[rating.player] = rating.rating

    return player_ratings


@app.get("/api/games/{game}/{player_name}")
def get_player_rating(game: str, player_name: str):
    player_name = player_name.capitalize()
    game = game.capitalize()
    rating = None
    with Session(app.engine) as session:  
        ratings = session.query(Rating).filter_by(game=game, player=player_name).all()
        if not ratings:
            raise HTTPException(status_code=404, detail=f"Game {game} not rated by {player_name}.")

    rating = ratings[0].rating

    return rating


@app.patch("/api/games/{game}/{player_name}", response_model = PlayerEntry)
def update_player_rating(
    game: str,
    player_name: str,
    rating: int
):
    """
    Update rating of existing game in database.
    Returns dict of player whose game rating was updated.
    """
    game = game.capitalize()
    player_name = player_name.capitalize()
    updated_rating_entry = {}

    with Session(app.engine) as session:
        ratings = session.query(Rating).filter_by(game=game, player=player_name).all()

        if not ratings:
            raise HTTPException(status_code=404, detail=f"Game {game} not rated by {player_name}.")
        
        ratings[0].rating = rating
        session.commit()
        updated_rating_entry[game] = ratings[0].rating

    return PlayerEntry(name=player_name, games=updated_rating_entry)

@app.post("/api/games/{game}/{player_name}", response_model = PlayerEntry, status_code=201)
def add_game_rating(
    game: str,
    player_name: str,
    rating: int
):
    """"
    Create new rated game entry.
    Returns dict of player new entry added to.
    """
    game = game.capitalize()
    player_name = player_name.capitalize()
    updated_rating_entry = {}

    with Session(app.engine) as session:      
        try:
            new_rating = Rating(player=player_name, game=game, rating=rating)
            session.add(new_rating)
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail=f"Game {game} has already been rated by {player_name}.")

        updated_rating_entry[game] = rating


    return PlayerEntry(name=player_name, games=updated_rating_entry)

@app.delete("/api/games/{game}/{player_name}", status_code=204)
def delete_game_rating(
    game: str,
    player_name: str
):
    """
    Delete rated game from player entry.
    Returns dict of player game rating deleted from.
    """
    game = game.capitalize()
    player_name = player_name.capitalize()
    player_to_ratings = {}

    with Session(app.engine) as session:
        ratings = session.query(Rating).filter_by(game=game, player=player_name).all()
        if not ratings:
            raise HTTPException(status_code=404, detail=f"Game {game} not rated by {player_name}.")
            
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


def ensure_game_database(engine: Engine):
    if not database_exists(engine.url):
        create_database(engine.url)
        print(f"Initialized database {DB_NAME}")


def add_ratings(games_by_player: Dict, session: Session):
    for player, game_ratings in games_by_player.items():
        for game, value in game_ratings.items():
            rating = Rating(player=player, game=game, rating=value)
            session.add(rating)


def initialize_ratings_table(engine, games_by_player: dict):
    """
    Initialize table in db from the `games_by_player` mapping
    games_by_player maps player_name -> {game -> rating}
    """
    # Ensure table exists
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        add_ratings(games_by_player, session)

        try:
            session.commit()
        except IntegrityError as e:
            print(f"Commit failed: {e}")


### Supporting functions ###
def parse_players_file(filename, ext) -> list:
    """
    Returns dict created from loaded file.
    Key -> Player, Value -> Fav games list.
    Returns empty dict if filename is improper.
    """

    players_games_list = []

    # Check for csv or json file type
    if (ext != ".json"):
        msg = "Sorry, this file type is not accepted. No new player info entered into database."
        raise ValueError(msg)
    
    # Open and save ratings schema for validation
    with open(SCHEMA_FILE) as schema_file:
        schema = json.load(schema_file)

    # Open file and create new players dict
    with open(filename) as upload_file:
        players_list = json.load(upload_file)

        # Check for valid file schema
        validate(instance=players_list, schema=schema)

        for person_dict in players_list:
            person_dict["name"] = person_dict["name"].capitalize()
            person_dict["games"] = {game.capitalize(): rating for game, rating in person_dict["games"].items()}
            players_games_list.append(person_dict)
            
        return players_games_list


def create_games_by_player(players_games_list):
    """
    Create dict of players and rated
    games keyed by player.
    """
    
    games_by_player = {}
    for player in players_games_list:
        games_by_player[player["name"]] = player["games"]
    
    return games_by_player


### Main application loop ###
def run(engine: Engine, args: argparse.Namespace):

    ensure_game_database(engine)

    players_games_list = []

    # Check for existence of path
    if os.path.exists(args.file):
        _, extension = os.path.splitext(args.file)
        players_games_list = parse_players_file(args.file, extension)
    else:
        raise FileNotFoundError(f"File not found: {args.file}")
    
    # Check if players exist in dict
    if not players_games_list:
        msg = "No players found in provided file."
        raise ValueError(msg)
    
    # Create different maps for endpoint access
    games_by_player = create_games_by_player(players_games_list)

    # Database connection
    app.engine = engine

    initialize_ratings_table(engine, games_by_player)

    # Start server
    print("Routes at startup:", [r.name for r in app.routes])
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
    parser.add_argument("-f","--file",  default="example_files/fam_fav_games.json", help="Player favorite games file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity")

    # Parse arguments
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    engine = connect_to_database()
    try:
        run(engine, args)
    except (FileNotFoundError, PlayerNotFoundError, ValueError, ValidationError) as e:
        print(e)
    finally:
        shutdown(engine)
