import pytest
from fastapi.testclient import TestClient
from Board_Game_App import create_games_by_player, all_games, app

### Setup Test Data ###

def sample_data_setup():
    """
    Setup sample data to use in tests
    """
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
    games_by_player = create_games_by_player(games_data)
    all_player_games = all_games(games_by_player)

    return games_data, games_by_player, all_player_games

def start_application():
    games_data, games_by_player, all_player_games = sample_data_setup()
    client = TestClient(app)
    app.games_by_player = games_by_player
    app.all_player_games = all_player_games

    return client


### Test Supporting Funtions ###
class Test_Supporting_Funcs:

    def setup_method(self, method):
        self.games_data, self.games_by_player, self.all_player_games = sample_data_setup()

    def test_create_games_by_player(self):
        res = create_games_by_player(players_games_list=self.games_data)
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
        games = create_games_by_player(self.games_data)
        res = all_games(games_by_player = games)
        expected_list = ["Boggle", "Hanabi", "Mysterium", "Rivals of Catan", "Codenames", "Settlers of Catan"]
        assert sorted(res) == sorted(expected_list)


### Test API Get Endpoints ###
class Test_API_Players_Path:
    
    @classmethod
    def setup_class(cls):
        cls.client = start_application()
        cls.games_data, cls.games_by_player, cls.all_player_games = sample_data_setup()
    
    @classmethod
    def teardown_class(cls):
        cls.client.close()

    def test_get_players(self):
        response = self.client.get("/api/players")
        assert response.status_code == 200
        assert response.json() == self.games_by_player

    def test_get_player(self):
        response = self.client.get("/api/players/em")
        assert response.status_code == 200
        assert response.json() == {
            "Boggle": 7,
            "Hanabi": 6,
            "Mysterium": 9,
            "Rivals of Catan": 8
            }
        
    def test_get_player_invalid_name(self):
        response = self.client.get("/api/players/bad")
        assert response.status_code == 404
        assert response.json() == {"detail": "Player Bad not found."}

class Test_API_Games_Path:
    
    @classmethod
    def setup_class(cls):
        cls.client = start_application()
        cls.games_data, cls.games_by_player, cls.all_player_games = sample_data_setup()
    
    @classmethod
    def teardown_class(cls):
        cls.client.close()
    
    def test_get_games(self):
        response = self.client.get("/api/games")
        assert response.status_code == 200
        assert response.json() == self.all_player_games

    def test_get_game_ratings(self):
        response = self.client.get("/api/games/hanabi")
        assert response.status_code == 200
        assert response.json() == {
            "Em": 6,
            "Mel": 8
        }

    def test_get_game_ratings_invalid_game(self):
        response = self.client.get("/api/games/zelda")
        assert response.status_code == 404
        assert response.json() == {"detail": "Game Zelda not found."}

    def test_get_player_rating(self):
        response = self.client.get("/api/games/hanabi/mel")
        assert response.status_code == 200
        assert response.json() == 8

    def test_get_player_rating_invalid_name(self):
        response = self.client.get("/api/games/hanabi/bad")
        assert response.status_code == 404
        assert response.json() == {"detail": "Player Bad not found."}

    def test_get_player_rating_invalid_game(self):
        response = self.client.get("/api/games/zelda/em")
        assert response.status_code == 404
        assert response.json() == {"detail": "Game Zelda not rated by Em."}
  

  # Test patch/post/delete methods
class Test_API_Rating_Mods:
    @classmethod
    def setup_class(cls):
        cls.client = start_application()

    @classmethod
    def teardown_class(cls):
        cls.client.close()

    def setup_method(self, method):
        self.games_data, self.games_by_player, self.all_player_games = sample_data_setup()

    # ============ Test Patch Methods =============
    def test_patch_valid_update(self):
        response = self.client.patch("/api/games/hanabi/mel", json={"rating_update": 4})
        assert response.status_code == 200
        assert response.json()["Name"] == "Mel"
        assert response.json()["Games"] == {
            "Codenames": 8,
            "Hanabi": 4,
            "Mysterium": 7,
            "Settlers of Catan": 6
        }

    def test_patch_invalid_name(self):
        response = self.client.patch("/api/games/hanabi/bad", json={"rating_update": 4})
        assert response.status_code == 404
        assert response.json() == {"detail": "Player Bad not found."}

    def test_patch_invalid_game(self):
        response = self.client.patch("/api/games/bad/mel", json={"rating_update": 4})
        assert response.status_code == 404
        assert response.json() == {"detail": "Game Bad not rated by Mel."}

    # ============ Test Post Methods =============
    def test_post_game_added(self):
        response = self.client.post("/api/games/new_game/em", json={"rating_update": 5})
        assert response.status_code == 201
        assert response.json()["Name"] == "Em"
        assert response.json()["Games"] == {
            "Boggle": 7,
            "Hanabi": 6,
            "Mysterium": 9,
            "Rivals of Catan": 8,
            "New_game": 5
        }
    
    def test_post_player_added(self):
        response = self.client.post("/api/games/hanabi/new_player", json={"rating_update": 5})
        assert response.status_code == 201
        assert response.json()["Name"] == "New_player"
        assert response.json()["Games"] == {
            "Hanabi": 5
        }

    def test_post_entry_exists(self):
        response = self.client.post("/api/games/hanabi/em", json={"rating_update": 5})
        assert response.status_code == 409
        assert response.json() == {"detail": "Game Hanabi has already been rated by Em."}

    # ============ Test Delete Methods =============
    def test_delete_valid_entry(self):
        response = self.client.delete("/api/games/hanabi/mel")
        assert response.status_code == 200
        assert response.json()["Name"] == "Mel"
        assert response.json()["Games"] == {
            "Codenames": 8,
            "Mysterium": 7,
            "Settlers of Catan": 6
        }

    def test_delete_invalid_game(self):
        response = self.client.delete("/api/games/bad/mel")
        assert response.status_code == 404
        assert response.json() == {"detail": "Game Bad not rated by Mel."}

    def test_delete_invalid_name(self):
        response = self.client.delete("/api/games/hanabi/bad")
        assert response.status_code == 404
        assert response.json() == {"detail": "Player Bad not found."}