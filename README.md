# Puzzles_Project
Sisters project tracking puzzle ownership and ratings :)

Puzzles Collection Manager

A simple app to log, browse, and rate puzzles you own or have played.

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
./puzzles_app.py
```
Then open the UI at the desired endpoint:
http://localhost:8080/[endpoint]

The root endpoint http://localhost:8080/ will take you to the main web page for the application.


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
pytest test_puzzles_app.py -v
```
