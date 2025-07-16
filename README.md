# Board_Game_Project
Sisters project tracking board games :)

Board Game Collection Manager

A simple app to log, browse, and rate board games you own or have played.

Stage 1:

* Learn Python basics and file I/O or JSON storage
* Build a simple CLI interface at first
* Add basic CRUD operations (Create, Read, Update, Delete)


Stage 2:

* FastAPI backend to serve and query game data
* PostgreSQL to store the game collection
* Simple frontend with HTML/JS
* Use SQLAlchemy as the ORM

Bonus idea: Integrate with the BoardGameGeek API to fetch game info automatically.

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
pip install -r requirements.txt
```

### Run the application
```
./Board_Game_App.py
```
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
postgres=# \c board_games
# Show tables in DB
postgres=# \dt
```

### Test the application
pytest is the testing framework: https://docs.pytest.org/en/stable/getting-started.html#get-started

To run all files of the form test_*.py or *_test.py in the current directory and its subdirectories:
```
pytest
```
To run just a particular file:
```
pytest test_board_game_app.py 
```

### Project outline

1. Introduce entrypoint file with argument parsing, hard-coded list of Emily and Melanies favorite games.
2. Add ability to load 'favorite games' for a list of players from a file (CSV and JSON should both be  supported).
3. Move hard-coded emily and melanie list to a JSON file that is included in version control and that the entrypoint file loads by default.
4. Introduce basic Web API using Fast API with endpoints to show list of users and their favorite games and show a single user, which support the GET methods
    - `/api/players/` -> List of all players
    - `/api/players/<player>` -> List of games the player has submitted
5. Add "rating" to player game info
6. Implement Fast API GET methods for:
    - `/api/games/` -> List of all games
    - `/api/games/<game>` -> List of all ratings by player for this game
    - `/api/games/<game>/<player>` -> Game rating for this player
7. Add basic unit tests around the existing API
8. Add API PATCH method to update a rating of a game `/api/games/<game>/<player>`
9. Add API POST and DELETE methods for `/api/games/<game>/<player>`
10. Create "games" DB in postgresql with a 1 table, "ratings" that has 3 fields:
    - player (string)
    - game (string)
    - rating (int)
11. Load data from default JSON into the table.
    - API to read from DB instead of file
    - POST/PATCH/DELETE should all result in DB updates
12. Add JSON schema file and validate the JSON against the schema before loading it into the DB.
13. On web server shutdown, save contents of db back to JSON file.
14. Add some "fixture integration/end-to-end" tests.
15. [Optional] Prettify the front-end with some basic HTML/Javascript.