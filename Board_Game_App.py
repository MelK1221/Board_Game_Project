"""
Entry point python file to start Board Game Project.

Authors: Emily Vaughn-Kukura and Melanie Kukura
"""

import argparse

MEL="mel"
EM="em"
ALL="all"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)

    # Add arguments
    parser.add_argument("player", choices=[MEL, EM, ALL], help="Name of Player")
    parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity")

    # Parse arguments
    args = parser.parse_args()
    return args


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
        
        print(f"All players like: {','.join(list(joint_likes))}")


if __name__ == "__main__":
    args = parse_args()
    run(args)