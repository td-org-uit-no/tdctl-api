from flask import Flask
from config import config

from .api import api
from .db import mongo


def create_app(config_name):

    app = Flask(__name__)
    # Fetch config object
    app.config.from_object(config[config_name])

    mongo.init_app(app)

    # Set tokens to expire at at "exp"
    mongo.db.tokens.create_index("exp", expireAfterSeconds=0)
    # Init with information from API.py
    api.init_app(app)

    return app
