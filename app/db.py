from pymongo.database import Database
from app import config
from pymongo import MongoClient
from fastapi import Request


def get_database(request: Request) -> Database:
    return request.app.db


def get_image_path(request: Request) -> str:
    return request.app.image_path


def get_export_path(request: Request) -> str:
    return request.app.export_path


def setup_db(app):
    app.db = MongoClient(app.config.MONGO_URI)[app.config.MONGO_DBNAME]
    app.export_path = 'db/eventExports/'
    if app.config.MONGO_DBNAME == 'test':
        app.image_path = 'db/testEventImages'
        return
    app.image_path = 'db/eventImages/'


def get_test_db():
    test_config = config['test']
    return MongoClient(test_config.MONGO_URI)[test_config.MONGO_DBNAME]
