#!/usr/bin/env python3
"""
Entry point python file to start Board Game Project.

Authors: Emily Vaughn-Kukura and Melanie Kukura
"""
import argparse
import csv
import json
import os
from typing import Dict

import uvicorn
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


ALL="all"

class PlayerEntry(BaseModel):
    """Pydantic response model for API patch/post/delete methods"""
    Name: str
    Games: Dict[str, int]

class RatingUpdateRequest(BaseModel):
    rating_update: int
class PlayerNotFoundError(Exception):
    """Custom exception for player not found."""
    def __init__(self, player_name):
        self.player_name = player_name
        self.message = f"Player {self.player_name} not found."
        super().__init__(self.message)

app = FastAPI(
    title="Board Games API",
    summary="Kukura Family & Friends Board Game Ratings",
    version="1",
    servers=[{"url": "/"}],
)


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/favicon.ico")
def favicon():
    return FileResponse("static/favicon.ico")


### API endpoints ###
@app.get("/api/players/")
def get_players():
    return app.games_by_player


@app.get("/api/players/{player_name}")
def get_player(player_name: str):
    player_name = player_name.capitalize()
    if player_name not in app.games_by_player.keys():
        raise HTTPException(status_code=404, detail=f"Player {player_name} not found.")

    return app.games_by_player[player_name]


@app.get("/api/games/")
def get_games():
    return app.all_player_games


@app.get("/api/games/{game}")
def get_game_ratings(game: str):
    game = game.capitalize()
    player_ratings = {}
    if game not in app.all_player_games:
        raise HTTPException(status_code=404, detail=f"Game {game} not found.")

    for name, game_ratings in app.games_by_player.items():
        if game in game_ratings.keys():
            player_ratings[name] = game_ratings[game]

    return player_ratings


@app.get("/api/games/{game}/{player_name}")
def get_player_rating(game: str, player_name: str):
    player_rating = {}
    player_name = player_name.capitalize()
    game = game.capitalize()
    if player_name not in app.games_by_player.keys():
        raise HTTPException(status_code=404, detail=f"Player {player_name} not found.")

    if game not in app.games_by_player[player_name].keys():
        raise HTTPException(status_code=404, detail=f"Game {game} not rated by {player_name}.")

    return app.games_by_player[player_name][game]

@app.patch("/api/games/{game}/{player_name}", response_model = PlayerEntry)
def update_player_rating(
    game: str,
    player_name: str,
    rating: RatingUpdateRequest = Body(...)
):
    """
    Update rating of existing game in database.
    Returns dict of player whose game rating was updated.
    """
    game = game.capitalize()
    player_name = player_name.capitalize()

    if player_name not in app.games_by_player.keys():
        raise HTTPException(status_code=404, detail=f"Player {player_name} not found.")
    
    if game not in app.games_by_player[player_name].keys():
        raise HTTPException(status_code=404, detail=f"Game {game} not rated by {player_name}.")
    
    app.games_by_player[player_name][game] = rating.rating_update

    return PlayerEntry(Name=player_name, Games=app.games_by_player[player_name])

@app.post("/api/games/{game}/{player_name}", response_model = PlayerEntry, status_code=201)
def add_game_rating(
    game: str,
    player_name: str,
    rating: RatingUpdateRequest = Body(...)
):
    """"
    Create new rated game entry.
    Returns dict of player new entry added to.
    """
    game = game.capitalize()
    player_name = player_name.capitalize()

    if player_name in app.games_by_player.keys():
        if game in app.games_by_player[player_name]:
            raise HTTPException(status_code=409, detail=f"Game {game} has already been rated by {player_name}.")
        else:
            app.games_by_player[player_name][game] = rating.rating_update
    else:
        app.games_by_player[player_name] = {game: rating.rating_update}


    return PlayerEntry(Name=player_name, Games=app.games_by_player[player_name])

@app.delete("/api/games/{game}/{player_name}", response_model = PlayerEntry)
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

    if player_name not in app.games_by_player.keys():
        raise HTTPException(status_code=404, detail=f"Player {player_name} not found.")
    
    if game not in app.games_by_player[player_name].keys():
        raise HTTPException(status_code=404, detail=f"Game {game} not rated by {player_name}.")
    
    deleted_rating = app.games_by_player[player_name].pop(game)


    return PlayerEntry(Name=player_name, Games=app.games_by_player[player_name])

### Supporting functions ###
def parse_players_file(filename, ext) -> list:
    """
    Returns dict created from loaded file.
    Key -> Player, Value -> Fav games list.
    Returns empty dict if filename is improper.
    """

    players_games_list = []

    # Check for csv or json file type
    if (ext != ".csv") and (ext != ".json"):
        msg = "Sorry, this file type is not accepted. No new player info entered into database."
        raise ValueError(msg)
    
    # Open file and create new players dict
    with open(filename) as upload_file:
        if ext == ".csv":
            csvreader = csv.DictReader(upload_file)
            players_list = [row for row in csvreader]               
        else:
            players_list = json.load(upload_file)

        for person_dict in players_list:
            person_dict["Name"] = person_dict["Name"].capitalize()
            person_dict["Games"] = {game.capitalize(): rating for game, rating in person_dict["Games"].items()}
            players_games_list.append(person_dict)
            
        return players_games_list


def create_games_by_player(players_games_list):
    """
    Create dict of players and rated
    games keyed by player.
    """
    
    games_by_player = {}
    for player in players_games_list:
        games_by_player[player["Name"]] = player["Games"]
    
    return games_by_player


def all_games(games_by_player: dict[str, list]):
    """
    Create list of all games rated.
    """
    
    all_games = []
    for player in games_by_player.keys():
        player_game_list = list(games_by_player[player].keys())
        all_games = list(set(all_games + player_game_list))
    
    return all_games


def print_player_likes(args: argparse.Namespace, games_by_player):
    """
    Print the players and their favorite games.
    If verbose is set, print the games that all players like.
    """
    # Print requested player(s) and their favorite games    
    players = [player for player in games_by_player.keys()]
    players_to_disp: list = []
    if args.player == ALL:
        players_to_disp = players
    else:
        # Check if requested player is in dict
        req_player = args.player.capitalize()
        if req_player not in players:
            raise PlayerNotFoundError(req_player)
        players_to_disp = [req_player]

    print("The following is a list of current players and the games they have rated:")
    for player in players_to_disp:
        games_list = [player_game["Game"] for player_game in games_by_player[player]]
        games = ", ".join(games_list)
        print(f"{player} has rated {games}.")

    if args.verbose and args.player == ALL:
        joint_likes: set = set()
        for player in players:
            new_games = set([player_game["Game"] for player_game in games_by_player[player]])

            if not joint_likes:
                # Initialize intersection for new player
                joint_likes = new_games
            else:
                # Only keep likes if shared by all previous players
                joint_likes = joint_likes.intersection(new_games)
                if not joint_likes:
                    # No common likes, end loop with empty set
                    break
        
        if not joint_likes:
            print("No games listed that all players have rated.")
        else:
            print(f"All players have rated: {', '.join(list(joint_likes))}")


### Main application loop ###
def run(args: argparse.Namespace):
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
    all_player_games = all_games(games_by_player)

    if args.player:
        print_player_likes(args, games_by_player)
    else:
        # Maps a player to a dict of the games they have rated
        app.games_by_player = games_by_player
        # List of all unique games that have been rated by players
        app.all_player_games = all_player_games

        # Start server
        uvicorn.run(app, host="localhost", port=args.port)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)

    # Add arguments
    parser.add_argument("--port", type=int, default=8080, help="Port number to run the server on")
    parser.add_argument("-p","--player", help="Player name to get favorite games for")
    parser.add_argument("-f","--file",  default="example_files/fam_fav_games.json", help="Player favorite games file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity")

    # Parse arguments
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    
    try:
        run(args)
    except (FileNotFoundError, PlayerNotFoundError, ValueError) as e:
        print(e)
