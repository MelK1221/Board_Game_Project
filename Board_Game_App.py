#!/usr/bin/env python3
"""
Entry point python file to start Board Game Project.

Authors: Emily Vaughn-Kukura and Melanie Kukura
"""
import argparse
import csv
import json
import os

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ALL="all"


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


@app.get("/api/players/")
def get_players():
    return app.players_games_list


@app.get("/api/players/{player_name}")
def get_player(player_name: str):
    player_name = player_name.capitalize()
    players = [player["Name"] for player in app.players_games_list]
    if player_name not in players:
        raise HTTPException(status_code=404, detail=f"Player {player_name} not found.")

    return app.games_by_player[player_name]


@app.get("/api/games/")
def get_games():
    return app.all_player_games


@app.get("/api/games/{game}")
def get_game_ratings(game: str):
    player_ratings = {}
    if game.capitalize() not in app.all_player_games:
        raise HTTPException(status_code=404, detail=f"Game {game} not found.")

    for name, game_list in app.games_by_player.items():
        for player_game in game_list:
            if player_game["Game"] == game.capitalize():
                player_ratings[name] = player_game["Rating"]

    return player_ratings


@app.get("/api/games/{game}/{player_name}")
def get_player_rating(game: str, player_name: str):
    player_rating = {}
    player_name = player_name.capitalize()
    game = game.capitalize()
    if player_name not in app.games_by_player.keys():
        raise HTTPException(status_code=404, detail=f"Player {player_name} not found.")

    game_list = [player_game["Game"] for player_game in app.games_by_player[player_name]]
    if game not in game_list:
        raise HTTPException(status_code=404, detail=f"Game {game} not rated by this player.")

    player_rating = next(player_game for player_game in app.games_by_player[player_name] if player_game["Game"] == game)

    return player_rating["Rating"]


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
            for game in person_dict["Games"]:
                game["Game"] = game["Game"].capitalize()
            players_games_list.append(person_dict)
            

        return players_games_list


def create_games_by_player(players_games_list):
    """
    Create dict of players and rated
    games keyed by player.
    """
    
    
    games_by_player = {}
    for player in players_games_list:
        player_games = []
        for game in player["Games"]:
            player_games.append({"Game": game["Game"], "Rating": game["Rating"]})
        games_by_player[player["Name"]] = player_games
    
    return games_by_player


def all_games(games_by_player: dict[str, list]):
    """
    Create list of all games rated.
    """
    
    all_games = []
    for player in games_by_player.keys():
        player_game_list = [player_game["Game"] for player_game in games_by_player[player]]
        if not all_games:
            all_games = player_game_list
        else:
            for game in player_game_list:
                if game not in all_games:
                    all_games.append(game)
    
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
            msg = f"{req_player} is not in the loaded file."
            raise ValueError(msg)
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
        app.players_games_list = players_games_list
        app.games_by_player = games_by_player
        app.all_player_games = all_player_games
        uvicorn.run(app, host="localhost", port=args.port)

if __name__ == "__main__":
    args = parse_args()
    
    try:
        run(args)
    except FileNotFoundError as e:
        print(e)
    except ValueError as e:
        print(e)
