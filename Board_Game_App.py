"""
Entry point python file to start Board Game Project.

Authors: Emily Vaughn-Kukura and Melanie Kukura
"""

import argparse
import csv
import json
import re

MEL="mel"
EM="em"
ALL="all"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)

    # Add arguments
    parser.add_argument("-p","--player", choices=[MEL, EM, ALL], default= ALL, help="Name of Player")
    parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity")

    # Parse arguments
    args = parser.parse_args()
    return args

def parse_players_file(filename) -> dict:
    #Returns empty dict if filename is improper

    filename_list = re.split(r"[. ]+", filename)
    player_games_dict = {}

    # Check for proper filename format
    if len(filename_list) != 2:
        print("Invalid filename entered, no new player info entered into database.")
        return player_games_dict

    file_type = filename_list[1]

    # Check for csv or json file type
    if (file_type != "csv") and (file_type != "json"):
        print("Sorry, this file type is not accepted. No new player info entered into database")
        return player_games_dict
    
    # Open file and create new players dict
    with open(filename) as upload_file:
        if file_type == "csv":
            csvreader = csv.DictReader(upload_file)
            players_list = [row for row in csvreader]               
        else:
            players_list = json.load(upload_file)

        players_keys = list(players_list[0].keys())

        for person_dict in players_list:
            player_name = person_dict[players_keys[0]]
            games_list = person_dict[players_keys[1]].split(',')
            games_list = [game.strip() for game in games_list]
            player_games_dict[player_name] = games_list

        return player_games_dict


def run(args: argparse.Namespace):

    mel_fav_board_games = ["Codenames", "Hanabi", "Mysterium", "Settlers of Catan"]
    em_fav_board_games = ["Boggle", "Hanabi", "Mysterium", "Rivals of Catan"]
    games_by_player = {
        MEL: mel_fav_board_games,
        EM: em_fav_board_games,
    }

    print("The following are a few of our favorite board games, in no particular order:")
    players: list = []
    if args.player == ALL:
        players = [player for player in games_by_player.keys()]
    else:
        players = [args.player]

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
        
        print(f"All players like: {', '.join(list(joint_likes))}")

    #Import new players list
    new_players_file = input("If you would like to upload a new players list, please type the file name here:")
    
    # Handle input if no user input provided
    if new_players_file == "":
        print("No filename entered, no new player info entered into database.")
        return
    else:
        new_players_fav_games = parse_players_file(new_players_file)

    #Merge default players dict with new players dict
    merged_games_by_player = games_by_player | new_players_fav_games

    #Update players list
    players = [player for player in merged_games_by_player]

    #Print updated players and games list
    print("See the current players list below:")
    for player in players:
        games = ", ".join(merged_games_by_player[player])
        print(f"{player.capitalize()} likes {games}.")


if __name__ == "__main__":
    args = parse_args()
    run(args)
