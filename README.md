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


Project outline:

1. Introduce entrypoint file with argument parsing, hard-coded list of Emily and Melanies favorite games.
2. Add ability to load 'favorite games' for a list of players from a file (CSV and JSON should both be supported).
3. Move hard-coded emily and melanie list to a JSON file that is included in version control and that the entrypoint file loads by default.
4. Introduce basic Web API using Fast API with endpoints to show list of users and their favorite games and show a single user, which support the GET method
    - `/api/games`
    - `/api/games/<player>`
5. Add "rating" to player game info
6. Add API PATCH method to update a rating of a game `/api/games/<player>`
7. Add API POST and DELETE methods for `/api/games/<player>`
8. Create "games" DB in postgresql with a 1 table, "ratings" that has 3 fields:
    - player (string)
    - game (string)
    - rating (int)
9. Load data from default JSON into the table.
    - API to read from DB instead of file
    - POST/PATCH/DELETE should all result in DB updates
10. On web server shutdown, save contents of db back to JSON file
11. [Optional] Prettify the front-end with some basic HTML/Javascript.