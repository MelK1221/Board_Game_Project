import pytest
import json

from jsonschema import validate, ValidationError
from sqlalchemy import Engine
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.exc import IntegrityError

from fastapi.testclient import TestClient
from pytest import mark
from unittest.mock import patch, MagicMock

from puzzles_app import add_ratings, create_puzzles_by_solver, app


### Setup Test Data ###

def sample_data_setup():
    """
    Setup sample data to use in tests
    """
    em_puzzles = {
            "The Mystic Maze": 7,
            "Decaying Diner": 9,
            "Hotel Vacancy": 5
        }

    mel_puzzles = {
            "Spirit Island in Canada": 9,
            "The Mystic Maze": 6,
            "The Gnomes Homes": 10
        }

    puzzles_data = [
        {
            "name": "Em",
            "puzzles": em_puzzles
        },
        {
            "name": "Mel",
            "puzzles": mel_puzzles
        }
    ]

    return puzzles_data

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
            if rating.solver == entry.solver and rating.puzzle == entry.puzzle:
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
        cls.puzzles_data = sample_data_setup()
        cls.puzzles_by_solver = create_puzzles_by_solver(cls.puzzles_data)
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
        self.puzzles_data = sample_data_setup()

    def test_create_puzzles_by_solver(self):
        res = create_puzzles_by_solver(solvers_puzzles_list=self.puzzles_data)
        assert res == {
            "Em": {
                "The Mystic Maze": 7,
                "Decaying Diner": 9,
                "Hotel Vacancy": 5
                },
            "Mel":{
                "Spirit Island in Canada": 9,
                "The Mystic Maze": 6,
                "The Gnomes Homes": 10
                }
            }
        
    def test_valid_schema(self):
        validate(instance=self.puzzles_data, schema=self.schema)

    def test_schema_invalid_name_type(self):
        test_data = [
            {
                "name": 123,
                "puzzles": {
                    "The Mystic Maze": 7,
                }
            }
        ]
        with pytest.raises(ValidationError):
            validate(instance=test_data, schema=self.schema)

    def test_schema_invalid_puzzles_type(self):
        test_data = [
            {
                "name": "Em",
                "puzzles": {
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
                "puzzles": {
                    "The Mystic Maze": 11,
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

    def test_schema_no_puzzles(self):
        test_data = [
            {
                "name": "Em",
                "puzzles": {}
            }
        ]
        with pytest.raises(ValidationError):
            validate(instance=test_data, schema=self.schema)
        
        

### Test API Get Endpoints ###
class TestAPISolversPath(TestAPIBase):
    
    @classmethod
    def setup_class(cls):
        super().setup_class()
        app.engine.db = MockDB()
        with MockSession(app.engine) as session:
            add_ratings(cls.puzzles_by_solver, session)

    @patch("puzzles_app.Session", new=MockSession)
    def test_get_solvers(self):
        response = self.client.get("/api/solvers")
        assert response.status_code == 200
        assert response.json() == self.puzzles_by_solver

    @patch("puzzles_app.Session", new=MockSession)
    def test_get_solver(self):
        response = self.client.get("/api/solvers/em")
        assert response.status_code == 200
        assert response.json() == {
            "The Mystic Maze": 7,
            "Decaying Diner": 9,
            "Hotel Vacancy": 5
            }
    
    @patch("puzzles_app.Session", new=MockSession)
    def test_get_solver_invalid_name(self):
        response = self.client.get("/api/solvers/bad")
        assert response.status_code == 404
        assert response.json() == {"detail": "Solver Bad not found."}


class TestAPIPuzzlesPath(TestAPIBase):
    
    @classmethod
    def setup_class(cls):
        super().setup_class()
        app.engine.db = MockDB()
        with MockSession(app.engine) as session:
            add_ratings(cls.puzzles_by_solver, session)
    
    @patch("puzzles_app.Session", new=MockSession)
    def test_get_puzzles(self):
        response = self.client.get("/api/puzzles")
        assert response.status_code == 200
        assert sorted(response.json().items()) == sorted([
            ("The Mystic Maze", [7,6]),
            ("Decaying Diner", [9]),
            ("Hotel Vacancy", [5]),
            ("Spirit Island in Canada", [9]),
            ("The Gnomes Homes", [10]),
        ])

    @patch("puzzles_app.Session", new=MockSession)
    def test_get_puzzle_ratings(self):
        response = self.client.get("/api/puzzles/the%20mystic%20maze")
        assert response.status_code == 200
        assert response.json() == {
            "Em": 7,
            "Mel": 6
        }

    @patch("puzzles_app.Session", new=MockSession)
    def test_get_puzzle_ratings_invalid_puzzle(self):
        response = self.client.get("/api/puzzles/zelda")
        assert response.status_code == 404
        assert response.json() == {"detail": "Puzzle Zelda not found."}

    @patch("puzzles_app.Session", new=MockSession)
    def test_get_solver_rating(self):
        response = self.client.get("/api/puzzles/the%20mystic%20maze/mel")
        assert response.status_code == 200
        assert response.json() == 6

    @patch("puzzles_app.Session", new=MockSession)
    def test_get_solver_rating_invalid_name(self):
        response = self.client.get("/api/puzzles/the%20mystic%20maze/bad")
        assert response.status_code == 404
        assert response.json() == {"detail": "Puzzle The Mystic Maze not rated by Bad."}

    @patch("puzzles_app.Session", new=MockSession)
    def test_get_solver_rating_invalid_puzzle(self):
        response = self.client.get("/api/puzzles/zelda/em")
        assert response.status_code == 404
        assert response.json() == {"detail": "Puzzle Zelda not rated by Em."}
  

# Test patch/post/delete methods
class TestAPIRatingMods(TestAPIBase):

    def setup_method(self, method):
        app.engine.db = MockDB()
        with MockSession(app.engine) as session:
            add_ratings(self.puzzles_by_solver, session)


    # ============ Test Patch Methods =============
    @patch("puzzles_app.Session", new=MockSession)
    def test_patch_valid_update(self):
        response = self.client.patch("/api/puzzles/the%20mystic%20maze/mel?rating=4")
        assert response.status_code == 200
        assert response.json()["name"] == "Mel"
        assert response.json()["puzzles"] == {
            "The Mystic Maze": 4,
        }

    @patch("puzzles_app.Session", new=MockSession)
    def test_patch_invalid_name(self):
        response = self.client.patch("/api/puzzles/the%20mystic%20maze/bad?rating=4")
        assert response.status_code == 404
        assert response.json() == {"detail": "Puzzle The Mystic Maze not rated by Bad."}

    @patch("puzzles_app.Session", new=MockSession)
    def test_patch_invalid_puzzle(self):
        response = self.client.patch("/api/puzzles/bad/mel?rating=4")
        assert response.status_code == 404
        assert response.json() == {"detail": "Puzzle Bad not rated by Mel."}

    # ============ Test Post Methods =============
    @patch("puzzles_app.Session", new=MockSession)
    def test_post_puzzle_added(self):
        response = self.client.post("/api/puzzles/new_puzzle/em?rating=5")
        assert response.status_code == 201
        assert response.json()["name"] == "Em"
        assert response.json()["puzzles"] == {
            "New_Puzzle": 5
        }
    
    @patch("puzzles_app.Session", new=MockSession)
    def test_post_solver_added(self):
        response = self.client.post("/api/puzzles/the%20mystic%20maze/new_solver?rating=5")
        assert response.status_code == 201
        assert response.json()["name"] == "New_Solver"
        assert response.json()["puzzles"] == {
            "The Mystic Maze": 5
        }

    @patch("puzzles_app.Session", new=MockSession)
    def test_post_entry_exists(self):
        response = self.client.post("/api/puzzles/the%20mystic%20maze/em?rating=5")
        assert response.status_code == 409
        assert response.json() == {"detail": "Puzzle The Mystic Maze has already been rated by Em."}

    # ============ Test Delete Methods =============
    @patch("puzzles_app.Session", new=MockSession)
    def test_delete_valid_entry(self):
        response = self.client.delete("/api/puzzles/the%20mystic%20maze/mel")
        assert response.status_code == 204
        assert response.text == ''

    @patch("puzzles_app.Session", new=MockSession)
    def test_delete_invalid_puzzle(self):
        response = self.client.delete("/api/puzzles/bad/mel")
        assert response.status_code == 404
        assert response.json() == {"detail": "Puzzle Bad not rated by Mel."}

    @patch("puzzles_app.Session", new=MockSession)
    def test_delete_invalid_name(self):
        response = self.client.delete("/api/puzzles/the%20mystic%20maze/bad")
        assert response.status_code == 404
        assert response.json() == {"detail": "Puzzle The Mystic Maze not rated by Bad."}