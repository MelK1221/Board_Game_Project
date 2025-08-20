# Puzzles_Project
Sisters project tracking puzzle ownership and ratings :)

Puzzles Collection Manager

A simple app to log, browse, and rate puzzles you own or have played.

Stage 1:

* Learn Python basics and file I/O or JSON storage
* Build a simple CLI interface at first
* Add basic CRUD operations (Create, Read, Update, Delete)


Stage 2:

* FastAPI backend to serve and query puzzle data
* PostgreSQL to store the puzzle collection
* Simple frontend with HTML/JS
* Use SQLAlchemy as the ORM

Bonus idea: Integrate Neural Network to help recommend puzzles based on past ratings.

### Installation
```
# Install PostgreSQL (mac OS)
brew install postgresql
brew services start postgresql

# Setup Postgres with application user
psql postgres
postgres=# CREATE USER app WITH PASSWORD '[REDACTED]';
postgres=# ALTER USER app WITH SUPERUSER;
# Verify user is present and has expected permissions
postgres=# \du

# Store password [REDACTED] in `password.txt` file
echo "[REDACTED]" > password.txt

# Install python application
```
pip install -r requirements.txt
```

### Run the application
```
./puzzles_app.py
Then open the UI at the desired endpoint:
http://localhost:8080/[endpoint]


### Stop PostgreSQL Server
```
brew services stop postgresql
# Check Status
brew services info postgresql
```

### Interacting with PostgreSQL
```
# Show databases
postgres=# \list
# Connect to Database
postgres=# \c puzzles
# Show tables in DB
postgres=# \dt
# Describe the 'ratings' table
puzzles=# \d ratings
# See all current entries
puzzles=# SELECT * FROM ratings;
# Drop table manually
puzzles=# DROP TABLE ratings;
```

### Test the application
pytest is the testing framework: https://docs.pytest.org/en/stable/getting-started.html#get-started

To run all files of the form test_*.py or *_test.py in the current directory and its subdirectories:
```
pytest
```
To run just a particular file:
```
pytest test_puzzles_app.py 
```

### Project outline

1. Introduce entrypoint file with argument parsing, hard-coded list of Emily and Melanies favorite puzzles.
2. Add ability to load 'favorite puzzles' for a list of solvers from a file (CSV and JSON should both be  supported).
3. Move hard-coded emily and melanie list to a JSON file that is included in version control and that the entrypoint file loads by default.
4. Introduce basic Web API using Fast API with endpoints to show list of users and their favorite puzzles and show a single user, which support the GET methods
    - `/api/solvers/` -> List of all solvers
    - `/api/solvers/<solver>` -> List of puzzles the solver has submitted
5. Add "rating" to solver puzzle info
6. Implement Fast API GET methods for:
    - `/api/puzzles/` -> List of all puzzles
    - `/api/puzzles/<puzzle>` -> List of all ratings by solver for this puzzle
    - `/api/puzzles/<puzzle>/<solver>` -> Puzzle rating for this solver
7. Add basic unit tests around the existing API
8. Add API PATCH method to update a rating of a puzzle `/api/puzzles/<puzzle>/<solver>`
9. Add API POST and DELETE methods for `/api/puzzles/<puzzle>/<solver>`
10. Create "puzzles" DB in postgresql with a 1 table, "ratings" that has 3 fields:
    - solver (string)
    - puzzle (string)
    - rating (int)
11. Load data from default JSON into the table.
    - API to read from DB instead of file
    - POST/PATCH/DELETE should all result in DB updates
12. Add JSON schema file and validate the JSON against the schema before loading it into the DB.
13. On web server shutdown, save contents of db back to JSON file.
14. Add some "fixture integration/end-to-end" tests.
15. [Optional] Prettify the front-end with some basic HTML/Javascript.
