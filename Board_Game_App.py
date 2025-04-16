"""
Entry point python file to start Board Game Project.

Authors: Emily Vaughn-Kukura and Melanie Kukura
"""

import argparse
import csv
import json
import os

ALL="all"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)

    # Add arguments
    parser.add_argument("-p","--player", default= ALL, help="Name of Player")
    parser.add_argument("-f","--file",  default= "fam_fav_games.json", help="Player favorite games file")
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
            player_name = person_dict["Name"]
            games_list = person_dict["Favorite Games"].split(',')
            games_list = [game.strip() for game in games_list]
            player_games_dict[player_name] = games_list

        return player_games_dict


def run(args: argparse.Namespace):
    games_by_player = {}

    # Check for existence of path
    if os.path.exists(args.file):
        name, extension = os.path.splitext(args.file)
        try:
            games_by_player = parse_players_file(args.file, extension)
        except ValueError as e:
            print(e)
            return
    else:
        raise FileNotFoundError(f"File not found: {args.file}")
    
    # Check if players exist in dict
    if not games_by_player:
        msg = "No players found in provided file."
        raise ValueError(msg)

    # Print requested player(s) and their favorite games    
    players: list = []
    if args.player == ALL:
        players = [player for player in games_by_player.keys()]
    else:
        # Check if requested player is in dict
        if args.player.capitalize() not in games_by_player.keys():
            msg = f"{args.player.capitalize()} is not in the loaded file."
            raise ValueError(msg)
        players = [args.player.capitalize()]


    print("The following is a list of current players and their favorite games:")
    for player in players:
        games = ", ".join(games_by_player[player])
        print(f"{player.capitalize()} likes {games}.")

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


if __name__ == "__main__":
    args = parse_args()
    
    try:
        run(args)
    except FileNotFoundError as e:
        print(e)
    except ValueError as e:
        print(e)
