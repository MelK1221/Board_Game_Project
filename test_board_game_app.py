import pytest
import json

from jsonschema import validate, ValidationError
from sqlalchemy import Engine
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.exc import IntegrityError

from fastapi.testclient import TestClient
from pytest import mark
from unittest.mock import patch, MagicMock

from board_game_app import add_ratings, parse_players_file, create_games_by_player, app


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

    return games_data

def start_application():
    app.engine = MagicMock(spec=Engine)
    client = TestClient(app)
    return client


# Mocks the result of a session query / filter operation
class MockQueryResult:

    def __init__(self, results: list):
        self.results = results
    
    def filter_by(self, **kwargs):
        filtered = []
        for item in self.results:
            matches = True
            for k, v in kwargs.items():
                if getattr(item, k) != v:
                    matches = False
                    break

            if matches:
                filtered.append(item)
        
        return MockQueryResult(filtered)
    
    def distinct(self):
        unique = set(self.results)
        return MockQueryResult(list(unique))

    def all(self):
        return self.results

class MockDB:
    def __init__(self):
        self.entries = []

class MockSession:
    
    def __init__(self, engine: MagicMock):
        self.engine = engine
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass
    
    def _get_db(self) -> MockDB:
        return self.engine.db

    def add(self, entry):
        db = self._get_db()
        for rating in db.entries:
            if rating.player == entry.player and rating.game == entry.game:
                raise IntegrityError(statement=None, params=None, orig=Exception("Duplicate Entry"))
        db.entries.append(entry)

    def query(self, T):
        # Note: The type T can be a table class or a particular column in that class
        db = self._get_db()
        results: list = []
        if isinstance(T, InstrumentedAttribute):
            table_results = list(filter(lambda x: isinstance(x, T.class_), db.entries))
            results = [(getattr(entry, T.key),) for entry in table_results]
        else:
            results = list(filter(lambda x: isinstance(x, T), db.entries))
        return MockQueryResult(results)
    
    def commit(self):
        pass

    def rollback(self):
        pass

    def delete(self, entry):
        db = self._get_db()
        db.entries.remove(entry)

class TestAPIBase:
    @classmethod
    def setup_class(cls):
        cls.games_data = sample_data_setup()
        cls.games_by_player = create_games_by_player(cls.games_data)
        cls.client = start_application()

    @classmethod
    def teardown_class(cls):
        cls.client.close()

### Test Supporting Funtions ###
class TestSupportingFuncs:

    @classmethod
    def setup_class(cls):
        with open("ratings_schema.json") as schema_file:
            cls.schema = json.load(schema_file)

    def setup_method(self, method):
        self.games_data = sample_data_setup()

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
        
    def test_valid_schema(self):
        validate(instance=self.games_data, schema=self.schema)

    def test_schema_invalid_name_type(self):
        test_data = [
            {
                "name": 123,
                "games": {
                    "Boggle": 7,
                    }
            }
        ]
        with pytest.raises(ValidationError):
            validate(instance=test_data, schema=self.schema)

    def test_schema_invalid_game_type(self):
        test_data = [
            {
                "name": "Em",
                "games": {
                    123: 7,
                    }
            }
        ]
        with pytest.raises(ValidationError):
            validate(instance=test_data, schema=self.schema)

    def test_schema_invalid_rating(self):
        test_data = [
            {
                "name": "Em",
                "games": {
                    "Boggle": 11,
                    }
            }
        ]
        with pytest.raises(ValidationError):
            validate(instance=test_data, schema=self.schema)  


    def test_schema_missing_field(self):
        test_data = [
            {
                "name": "Em",
            }
        ]
        with pytest.raises(ValidationError):
            validate(instance=test_data, schema=self.schema)

    def test_schema_no_games(self):
        test_data = [
            {
                "name": "Em",
                "games": {}
            }
        ]
        with pytest.raises(ValidationError):
            validate(instance=test_data, schema=self.schema)
        
        

### Test API Get Endpoints ###
class TestAPIPlayersPath(TestAPIBase):
    
    @classmethod
    def setup_class(cls):
        super().setup_class()
        app.engine.db = MockDB()
        with MockSession(app.engine) as session:
            add_ratings(cls.games_by_player, session)

    @patch("board_game_app.Session", new=MockSession)
    def test_get_players(self):
        response = self.client.get("/api/players")
        assert response.status_code == 200
        assert response.json() == self.games_by_player

    @patch("board_game_app.Session", new=MockSession)
    def test_get_player(self):
        response = self.client.get("/api/players/em")
        assert response.status_code == 200
        assert response.json() == {
            "Boggle": 7,
            "Hanabi": 6,
            "Mysterium": 9,
            "Rivals of Catan": 8
            }
    
    @patch("board_game_app.Session", new=MockSession)
    def test_get_player_invalid_name(self):
        response = self.client.get("/api/players/bad")
        assert response.status_code == 404
        assert response.json() == {"detail": "Player Bad not found."}


class TestAPIGamesPath(TestAPIBase):
    
    @classmethod
    def setup_class(cls):
        super().setup_class()
        app.engine.db = MockDB()
        with MockSession(app.engine) as session:
            add_ratings(cls.games_by_player, session)
    
    @patch("board_game_app.Session", new=MockSession)
    def test_get_games(self):
        response = self.client.get("/api/games")
        assert response.status_code == 200
        assert sorted(response.json()) == sorted([
            "Boggle",
            "Rivals of Catan",
            "Codenames",
            "Hanabi",
            "Mysterium",
            "Settlers of Catan",
        ])

    @patch("board_game_app.Session", new=MockSession)
    def test_get_game_ratings(self):
        response = self.client.get("/api/games/hanabi")
        assert response.status_code == 200
        assert response.json() == {
            "Em": 6,
            "Mel": 8
        }

    @patch("board_game_app.Session", new=MockSession)
    def test_get_game_ratings_invalid_game(self):
        response = self.client.get("/api/games/zelda")
        assert response.status_code == 404
        assert response.json() == {"detail": "Game Zelda not found."}

    @patch("board_game_app.Session", new=MockSession)
    def test_get_player_rating(self):
        response = self.client.get("/api/games/hanabi/mel")
        assert response.status_code == 200
        assert response.json() == 8

    @patch("board_game_app.Session", new=MockSession)
    def test_get_player_rating_invalid_name(self):
        response = self.client.get("/api/games/hanabi/bad")
        assert response.status_code == 404
        assert response.json() == {"detail": "Game Hanabi not rated by Bad."}

    @patch("board_game_app.Session", new=MockSession)
    def test_get_player_rating_invalid_game(self):
        response = self.client.get("/api/games/zelda/em")
        assert response.status_code == 404
        assert response.json() == {"detail": "Game Zelda not rated by Em."}
  

# Test patch/post/delete methods
class TestAPIRatingMods(TestAPIBase):

    def setup_method(self, method):
        app.engine.db = MockDB()
        with MockSession(app.engine) as session:
            add_ratings(self.games_by_player, session)


    # ============ Test Patch Methods =============
    @patch("board_game_app.Session", new=MockSession)
    def test_patch_valid_update(self):
        response = self.client.patch("/api/games/hanabi/mel?rating=4")
        assert response.status_code == 200
        assert response.json()["name"] == "Mel"
        assert response.json()["games"] == {
            "Hanabi": 4,
        }

    @patch("board_game_app.Session", new=MockSession)
    def test_patch_invalid_name(self):
        response = self.client.patch("/api/games/hanabi/bad?rating=4")
        assert response.status_code == 404
        assert response.json() == {"detail": "Game Hanabi not rated by Bad."}

    @patch("board_game_app.Session", new=MockSession)
    def test_patch_invalid_game(self):
        response = self.client.patch("/api/games/bad/mel?rating=4")
        assert response.status_code == 404
        assert response.json() == {"detail": "Game Bad not rated by Mel."}

    # ============ Test Post Methods =============
    @patch("board_game_app.Session", new=MockSession)
    def test_post_game_added(self):
        response = self.client.post("/api/games/new_game/em?rating=5")
        assert response.status_code == 201
        assert response.json()["name"] == "Em"
        assert response.json()["games"] == {
            "New_game": 5
        }
    
    @patch("board_game_app.Session", new=MockSession)
    def test_post_player_added(self):
        response = self.client.post("/api/games/hanabi/new_player?rating=5")
        assert response.status_code == 201
        assert response.json()["name"] == "New_player"
        assert response.json()["games"] == {
            "Hanabi": 5
        }

    @patch("board_game_app.Session", new=MockSession)
    def test_post_entry_exists(self):
        response = self.client.post("/api/games/hanabi/em?rating=5")
        assert response.status_code == 409
        assert response.json() == {"detail": "Game Hanabi has already been rated by Em."}

    # ============ Test Delete Methods =============
    @patch("board_game_app.Session", new=MockSession)
    def test_delete_valid_entry(self):
        response = self.client.delete("/api/games/hanabi/mel")
        assert response.status_code == 204
        assert response.text == ''

    @patch("board_game_app.Session", new=MockSession)
    def test_delete_invalid_game(self):
        response = self.client.delete("/api/games/bad/mel")
        assert response.status_code == 404
        assert response.json() == {"detail": "Game Bad not rated by Mel."}

    @patch("board_game_app.Session", new=MockSession)
    def test_delete_invalid_name(self):
        response = self.client.delete("/api/games/hanabi/bad")
        assert response.status_code == 404
        assert response.json() == {"detail": "Game Hanabi not rated by Bad."}