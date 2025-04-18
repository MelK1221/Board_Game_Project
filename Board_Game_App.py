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

app = FastAPI(
    title="Board Games API",
    summary="Kukura Family & Friends Board Game Ratings",
    version="1",
    servers=[{"url": "/"}],
)


@app.get("/api/players/")
def get_players():
    return app.games_by_player


@app.get("/api/players/{player_name}")
def get_player(player_name: str):
    player_name = player_name.capitalize()
    if player_name not in app.games_by_player:
        raise HTTPException(status_code=404, detail=f"Player {player_name} not found.")

    return app.games_by_player[player_name]


ALL="all"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)

    # Add arguments
    parser.add_argument("--port", default=8080, help="Port number to run the server on")
    parser.add_argument("-p","--player", help="Player name to get favorite games for")
    parser.add_argument("-f","--file",  default="example_files/fam_fav_games.json", help="Player favorite games file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity")

    # Parse arguments
    args = parser.parse_args()
    return args


def parse_players_file(filename, ext) -> dict[str, list]:
    """
    Returns dict created from loaded file.
    Key -> Player, Value -> Fav games list.
    Returns empty dict if filename is improper.
    """

    player_games_dict = {}

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
            player_name = person_dict["Name"].capitalize()
            games_list = person_dict["Favorite Games"].split(',')
            games_list = [game.strip() for game in games_list]
            player_games_dict[player_name] = games_list

        return player_games_dict


def print_player_likes(args: argparse.Namespace, games_by_player: dict[str, list]):
    """
    Print the players and their favorite games.
    If verbose is set, print the games that all players like.
    """
    # Print requested player(s) and their favorite games    
    players: list = []
    if args.player == ALL:
        players = [player for player in games_by_player.keys()]
    else:
        # Check if requested player is in dict
        req_player = args.player.capitalize()
        if req_player not in games_by_player.keys():
            msg = f"{req_player} is not in the loaded file."
            raise ValueError(msg)
        players = [req_player]

    print("The following is a list of current players and their favorite games:")
    for player in players:
        games = ", ".join(games_by_player[player])
        print(f"{player} likes {games}.")

    if args.verbose and args.player == ALL:
        joint_likes: set = set()
        for player in players:
            new_games = set(games_by_player[player])

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
    games_by_player = {}

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
