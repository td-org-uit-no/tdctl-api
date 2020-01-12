from flask import Flask
from config import config
from .api import api


def create_app(config_name):

    app = Flask(__name__)
    # Fetch config object
    app.config.from_object(config[config_name])

    # TODO:
    # Hook up the database

    # Init with information from API.pY
    api.init_app(app)
    return app
