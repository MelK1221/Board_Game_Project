import pytest
from Board_Game_App import create_games_by_player, PlayerNotFoundError

em_games = {
         "Boggle": 7,
         "Hanabi": 6,
         "Mysterium": 9,
         "Rivals of Catan": 8
      }

mel_games = {
         "Codenames": 8,
         "Hanabi": 8,
         "Mysterium": 7,
         "Settlers of Catan": 6
      }

games_data = [
    {
        "Name": "Em",
        "Games": em_games
    },
    {
        "Name": "Mel",
        "Games": mel_games
    }
]

def test_create_games_by_player():
    res = create_games_by_player(players_games_list=games_data)
    assert res == {
        "Em": {
            "Boggle": 7,
            "Hanabi": 6,
            "Mysterium": 9,
            "Rivals of Catan": 8
            },
        "Mel":{
            "Codenames": 8,
            "Hanabi": 8,
            "Mysterium": 7,
            "Settlers of Catan": 6
            }
        }
