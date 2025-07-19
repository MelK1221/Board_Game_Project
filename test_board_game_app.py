import pytest
from fastapi.testclient import TestClient
from Board_Game_App import create_games_by_player, all_games, app

### Setup Test Data ###
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

client = TestClient(app)

games_by_player = create_games_by_player(games_data)
app.games_by_player = games_by_player

all_player_games = all_games(games_by_player)
app.all_player_games = all_player_games

### Test Supporting Funtions ###
class Test_Supporting_Funcs:
    def test_create_games_by_player(self):
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
        
    def test_all_games(self):
        games = create_games_by_player(games_data)
        res = all_games(games_by_player = games)
        expected_list = ["Boggle", "Hanabi", "Mysterium", "Rivals of Catan", "Codenames", "Settlers of Catan"]
        assert sorted(res) == sorted(expected_list)


### Test API Get Endpoints ###
class Test_API_Players_Path:
    def test_get_players(self):
        response = client.get("/api/players")
        assert response.status_code == 200
        assert response.json() == games_by_player

    def test_get_player(self):
        response = client.get("/api/players/em")
        assert response.status_code == 200
        assert response.json() == {
            "Boggle": 7,
            "Hanabi": 6,
            "Mysterium": 9,
            "Rivals of Catan": 8
            }
        
    def test_get_player_invalid_name(self):
        response = client.get("/api/players/bad")
        assert response.status_code == 404
        assert response.json() == {"detail": "Player Bad not found."}

class Test_API_Games_Path():
    def test_get_games(self):
        response = client.get("/api/games")
        assert response.status_code == 200
        assert response.json() == all_player_games

    def test_get_game_ratings(self):
        response = client.get("/api/games/hanabi")
        assert response.status_code == 200
        assert response.json() == {
            "Em": 6,
            "Mel": 8
        }

    def test_get_game_ratings_invalid_game(self):
        response = client.get("/api/games/zelda")
        assert response.status_code == 404
        assert response.json() == {"detail": "Game Zelda not found."}

    def test_get_player_rating(self):
        response = client.get("/api/games/hanabi/mel")
        assert response.status_code == 200
        assert response.json() == 8

    def test_get_player_rating_invalid_name(self):
        response = client.get("/api/games/hanabi/bad")
        assert response.status_code == 404
        assert response.json() == {"detail": "Player Bad not found."}

    def test_get_player_rating_invalid_game(self):
        response = client.get("/api/games/zelda/em")
        assert response.status_code == 404
        assert response.json() == {"detail": "Game Zelda not rated by Em."}
  