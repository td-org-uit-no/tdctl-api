from flask import Flask
from config import config
from .api import api


def create_app(config_name):

    app = Flask(__name__)
    # Fetch config object
    app.config.from_object(config[config_name])

    from .db import mongo
    mongo.init_app(app)

    # Init with information from API.py
    api.init_app(app)

    return app
