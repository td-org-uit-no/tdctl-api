# Local Database
We currently use **mongodb** as our database.

The local database is used for development. The database features some seed-values to able to test the functionality of the API, without bothering anyone else.

The database is set to run on **port 27018** (default for mongodb is *27018*) to avoid interference with other databases.
## Usage
1. First step is to install mongodb. Follow directions on their site [here](https://docs.mongodb.com/manual/administration/install-community/)
2. Start the mongodb server with the config with: `mongod -f db.yml`
3. Seed the database with `seeding.py` found in the root directory

## Cleaning up
You can delete the database files with the `cleanup.sh` script.
