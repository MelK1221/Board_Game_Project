from sqlalchemy import Engine
from sqlalchemy.orm import Session

from fastapi.testclient import TestClient
from pytest import mark
from unittest.mock import patch, MagicMock

from board_game_app import create_games_by_player, app


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
            "name": "Em",
            "games": em_games
        },
        {
            "name": "Mel",
            "games": mel_games
        }
    ]
    games_by_player = create_games_by_player(games_data)

    return games_data, games_by_player

def start_application():
    app.engine = MagicMock(spec=Engine)
    client = TestClient(app)
    return client


### Test Supporting Funtions ###
class TestSupportingFuncs:

    def setup_method(self, method):
        self.games_data, self.games_by_player = sample_data_setup()

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
        

### Test API Get Endpoints ###
class TestAPIPlayersPath:
    
    @classmethod
    def setup_class(cls):
        cls.mock_session = MagicMock(spec=Session)
        cls.client = start_application()
        # TODO: is 'games_data' needed?
        cls.games_data, cls.games_by_player = sample_data_setup()
        # TODO: pass 'games_by_player' to 'add_ratings' - add ratings should add to a fake DB of some kind
        # then have return value here get from the fake DB
        cls.mock_session.query.return_value.all.return_value = cls.games_by_player
    
    @classmethod
    def teardown_class(cls):
        cls.client.close()

    @patch("board_game_app.Session")
    def test_get_players(self, mock_session_class):
        mock_session_class.return_value.__enter__.return_value = self.mock_session

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


class TestAPIGamesPath:
    
    @classmethod
    def setup_class(cls):
        cls.client = start_application()
        cls.games_data, cls.games_by_player = sample_data_setup()
    
    @classmethod
    def teardown_class(cls):
        cls.client.close()
    
    def test_get_games(self):
        response = self.client.get("/api/games")
        assert response.status_code == 200
        # FIXME
        # assert response.json() == self.all_player_games

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
@mark.skip()
class TestAPIRatingMods:
    @classmethod
    def setup_class(cls):
        cls.client = start_application()

    @classmethod
    def teardown_class(cls):
        cls.client.close()

    def setup_method(self, method):
        self.games_data, self.games_by_player = sample_data_setup()

    # ============ Test Patch Methods =============
    def test_patch_valid_update(self):
        response = self.client.patch("/api/games/hanabi/mel?rating=4")
        assert response.status_code == 200
        assert response.json()["name"] == "Mel"
        assert response.json()["games"] == {
            "Codenames": 8,
            "Hanabi": 4,
            "Mysterium": 7,
            "Settlers of Catan": 6
        }

    def test_patch_invalid_name(self):
        response = self.client.patch("/api/games/hanabi/bad?rating=4")
        assert response.status_code == 404
        assert response.json() == {"detail": "Player Bad not found."}

    def test_patch_invalid_game(self):
        response = self.client.patch("/api/games/bad/mel?rating=4")
        assert response.status_code == 404
        assert response.json() == {"detail": "Game Bad not rated by Mel."}

    # ============ Test Post Methods =============
    def test_post_game_added(self):
        response = self.client.post("/api/games/new_game/em?rating=5")
        assert response.status_code == 201
        assert response.json()["name"] == "Em"
        assert response.json()["games"] == {
            "Boggle": 7,
            "Hanabi": 6,
            "Mysterium": 9,
            "Rivals of Catan": 8,
            "New_game": 5
        }
    
    def test_post_player_added(self):
        response = self.client.post("/api/games/hanabi/new_player?rating=5")
        assert response.status_code == 201
        assert response.json()["name"] == "New_player"
        assert response.json()["games"] == {
            "Hanabi": 5
        }

    def test_post_entry_exists(self):
        response = self.client.post("/api/games/hanabi/em?rating=5")
        assert response.status_code == 409
        assert response.json() == {"detail": "Game Hanabi has already been rated by Em."}

    # ============ Test Delete Methods =============
    def test_delete_valid_entry(self):
        response = self.client.delete("/api/games/hanabi/mel")
        assert response.status_code == 200
        assert response.json()["name"] == "Mel"
        assert response.json()["games"] == {
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