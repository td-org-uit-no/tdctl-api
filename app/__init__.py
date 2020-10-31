from fastapi import FastAPI
from .config import config

from .api import members, auth
from .db import setup_db


def create_app(config_name):
    app = FastAPI(
        title='TDCTL-API',
        version='0.1',
        description='''TDCTL-database API.
        Everything related to Tromsøstudentenes Dataforening''',
        contact='td@list.uit.no',
        docs_url="/"
    )
    app.include_router(members.router, prefix="/member")
    app.include_router(auth.router, prefix="/auth")
    # Fetch config object
    app.config = config[config_name]
    setup_db(app)

    # Set tokens to expire at at "exp"
    app.db.tokens.create_index("exp", expireAfterSeconds=0)
    # Init with information from API.py

    return app
