from pymongo.database import Database
from app import config
from pymongo import MongoClient
from fastapi import Request


def get_database(request: Request) -> Database:
    return request.app.db


def get_image_path(request: Request) -> str:
    return request.app.image_path


def get_JobImage_path(request: Request) -> str:
    return request.app.jobImage_path


def get_export_path(request: Request) -> str:
    return request.app.export_path


def setup_db(app):
    app.db = MongoClient(app.config.MONGO_URI, uuidRepresentation="standard")[
        app.config.MONGO_DBNAME]
    app.export_path = 'db/eventExports'

    # Expire reset password codes after 10 minutes
    app.db.passwordResets.create_index("createdAt", expireAfterSeconds=60 * 10)
    if app.config.MONGO_DBNAME == 'test':
        app.image_path = 'db/testEventImages'
        return
    app.image_path = 'db/eventImages'
    app.jobImage_path = 'db/jobImages'


def get_test_db():
    test_config = config['test']
    return MongoClient(test_config.MONGO_URI, uuidRepresentation="standard")[test_config.MONGO_DBNAME]
