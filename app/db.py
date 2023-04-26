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

def get_qr_path(request: Request) -> str:
    return request.app.qr_path


def get_export_path(request: Request) -> str:
    return request.app.export_path


def setup_db(app):
    app.db = MongoClient(app.config.MONGO_URI, uuidRepresentation="standard")[
        app.config.MONGO_DBNAME]
    file_storage_path = "db/file_storage"
    app.export_path = f'{file_storage_path}/event_exports'

    # Expire reset password codes after 10 minutes
    app.db.passwordResets.create_index("createdAt", expireAfterSeconds=60 * 10)
    app.qr_path = f'{file_storage_path}/qr'
    if app.config.MONGO_DBNAME == 'test':
        app.image_path = 'db/test_event_images'
        return
    app.image_path = f'{file_storage_path}/event_images'
    app.jobImage_path = f'{file_storage_path}/job_images'


def get_test_db():
    test_config = config['test']
    return MongoClient(test_config.MONGO_URI, uuidRepresentation="standard")[test_config.MONGO_DBNAME]
