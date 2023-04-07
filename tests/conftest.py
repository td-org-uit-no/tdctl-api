import pytest
import os
from app import config
from pymongo import MongoClient
from fastapi.testclient import TestClient
from utils.seeding import seed_events, seed_members

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# for pytest to create an FastAPI instance, used in client as argument


@pytest.fixture
def app():
    from app import create_app
    app.config = config['test']
    os.environ["API_ENV"] = 'test'
    return create_app()

# create a test client using a test database for testing
# The db resets after every test


@pytest.fixture
def client(app):
    mongo_client = MongoClient(
        app.config.MONGO_URI, uuidRepresentation="standard")
    # change the fastapi db to the test database
    app.db = mongo_client[app.config.MONGO_DBNAME]
    # safty check asserting we only clear our test database
    if app.db.name != 'test':
        pytest.exit("Error: test using wrong database")
    mongo_client.drop_database('test')
    test_seed_path = "db/seeds/test_seeds"

    with TestClient(app) as client:
        # important that test_members.json always has a penalized member
        seed_members(app.db, f"{test_seed_path}/test_members.json")
        seed_events(app.db, f"{test_seed_path}/test_events.json")
        yield client


def client_login(client: TestClient, email, pwd):
    response = client.post(
        '/api/auth/login', json={'email': email, 'password': pwd})
    if response.status_code != 200:
        pytest.fail(f'Login error: {response.reason}')
