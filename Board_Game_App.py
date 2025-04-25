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
    return app.games_by_player


@app.get("/api/players/{player_name}")
def get_player(player_name: str):
    player_name = player_name.capitalize()
    players = [player["Name"] for player in app.games_by_player]
    if player_name not in players:
        raise HTTPException(status_code=404, detail=f"Player {player_name} not found.")

    player_idx = find_player_idx(app.games_by_player, player_name)

    return app.games_by_player[player_idx]


@app.get("/api/games/")
def get_games():
    all_games_list = all_games(app.games_by_player)
    return all_games_list


@app.get("/api/games/{game}")
def get_game_ratings(game: str):
    player_ratings = {}
    all_games_list = all_games(app.games_by_player)
    if game.capitalize() not in all_games_list:
        raise HTTPException(status_code=404, detail=f"Game {game} not found.")

    for player in app.games_by_player:
        for cur_game in player["Games"]:
            if cur_game["Game"].capitalize() == game.capitalize():
                 player_ratings[player["Name"]] = cur_game["Rating"]

    return player_ratings


@app.get("/api/games/{game}/{player_name}")
def get_player_rating(game: str, player_name: str):
    player_rating = {}
    player_idx = find_player_idx(app.games_by_player, player_name.capitalize())
    if player_idx == -1:
        raise HTTPException(status_code=404, detail=f"Player {player_name.capitalize()} not found.")

    game_list = find_games_list(app.games_by_player, player_idx)
    if game.capitalize() not in game_list:
        raise HTTPException(status_code=404, detail=f"Game {game.capitalize()} not rated by this player.")
    
    games_dict_list = app.games_by_player[player_idx]["Games"]
    for cur_game in games_dict_list:
        if cur_game["Game"].capitalize() == game.capitalize():
            player_rating["Rating"] = cur_game["Rating"]

    return player_rating


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

    player_games_ratings_list = []

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
            player_games_ratings_list.append(person_dict)
            

        return player_games_ratings_list


def find_player_idx(games_by_player: list[dict], value: str) -> int:
    """
    Finds the list index of the requested player.
    value is the player name.
    """
    
    # Find player index in list
    index = 0
    for dictionary in games_by_player:
        if dictionary["Name"] == value:
            return index
        index += 1
    return -1


def find_games_list(games_by_player: list[dict], player_idx: int) -> list:
    """
    Returns list of games associated with
    provided player index.
    """

    # Convert player games into list
    games_ratings_list = games_by_player[player_idx]["Games"]
    games_list = [game["Game"].capitalize() for game in games_ratings_list]

    return games_list


def all_games(dic_list: list[dict]):
    """
    Create list of all games rated.
    """
    
    all_games = []
    for idx in range(len(app.games_by_player)):
        player_game_list = find_games_list(app.games_by_player, idx)
        if not all_games:
            all_games = list(map(lambda g: g.capitalize(),player_game_list))
        else:
            for game in player_game_list:
                if game.capitalize() not in all_games:
                    all_games.append(game.capitalize())
    
    return all_games


def print_player_likes(args: argparse.Namespace, games_by_player: list):
    """
    Print the players and their favorite games.
    If verbose is set, print the games that all players like.
    """
    # Print requested player(s) and their favorite games    
    players = [player['Name'] for player in games_by_player]
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

    print("The following is a list of current players and their favorite games:")
    for player in players_to_disp:
        player_idx = find_player_idx(games_by_player, player)
        games_list = find_games_list(games_by_player, player_idx)
        games = ", ".join(games_list)
        print(f"{player} likes {games}.")

    if args.verbose and args.player == ALL:
        joint_likes: set = set()
        for player in players:
            player_idx = find_player_idx(games_by_player, "Name", player)
            new_games = set(find_games_list(games_by_player, player_idx))

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
            print("No games listed that all players like.")
        else:
            print(f"All players like: {', '.join(list(joint_likes))}")


def run(args: argparse.Namespace):
    games_by_player = []

    # Check for existence of path
    if os.path.exists(args.file):
        _, extension = os.path.splitext(args.file)
        games_by_player = parse_players_file(args.file, extension)
    else:
        raise FileNotFoundError(f"File not found: {args.file}")
    
    # Check if players exist in dict
    if not games_by_player:
        msg = "No players found in provided file."
        raise ValueError(msg)

    if args.player:
        print_player_likes(args, games_by_player)
    else:
        app.games_by_player = games_by_player
        uvicorn.run(app, host="localhost", port=args.port)

if __name__ == "__main__":
    args = parse_args()
    
    try:
        run(args)
    except FileNotFoundError as e:
        print(e)
    except ValueError as e:
        print(e)
