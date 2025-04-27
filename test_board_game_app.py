import pytest
from Board_Game_App import find_games_list, find_player_idx

em_games = [
    {"Game": "Boggle", "Rating": 7},
    {"Game": "Hanabi", "Rating": 6},
]

mel_games = [
    {"Game": "Codenames", "Rating": 8},
    {"Game": "Hanabi", "Rating": 8},
    {"Game": "Mysterium", "Rating": 7},
]

games_data = [
   {
      "Name": "Em",
      "Games": em_games,
   },
   {
      "Name": "Mel",
      "Games": mel_games
   },
]

def test_find_player_idx():
    res = find_player_idx(games_by_player=games_data, key="Name", value="Em")
    assert res == 0

def test_find_player_idx_player_not_present():
    res = find_player_idx(games_by_player=games_data, key="Name", value="Bad")
    assert res == -1

def test_find_games_list():
    res = find_games_list(games_by_player=games_data, player_idx=0)
    assert res == ["Boggle", "Hanabi"]

def test_find_games_list_invalid_index():
    with pytest.raises(IndexError):
        find_games_list(games_by_player=games_data, player_idx=2)
