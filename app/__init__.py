import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import config

from .api import members, auth
from .db import setup_db


def create_app():

    app = FastAPI(
        title='TDCTL-API',
        version='0.1',
        description='''TDCTL-database API.
        Everything related to Tromsøstudentenes Dataforening''',
        contact='td@list.uit.no',
        docs_url="/",
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(members.router, prefix="/api/member", tags=['members'])
    app.include_router(auth.router, prefix="/api/auth", tags=['auth'])
    
    # Fetch config object
    env = os.getenv('FLASK_APP_ENV', 'default')
    app.config = config[env]
    
    setup_db(app)
    # Set tokens to expire at at "exp"
    app.db.tokens.create_index("exp", expireAfterSeconds=0)

    return app
