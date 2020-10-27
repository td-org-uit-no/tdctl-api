from pymongo import MongoClient, database
from fastapi import Request


def get_database(request: Request) -> database:
    return request.app.db


def setup_db(app):
    app.db = MongoClient(app.config.MONGO_URI)[app.config.MONGO_DBNAME]
    db = app.db
