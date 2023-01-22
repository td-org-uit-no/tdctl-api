import os

class Config:
    SECRET_KEY: str
    ENV: str
    MONGO_HOST: str
    MONGO_PORT: int
    MONGO_DBNAME: str
    MONGO_URI: str
    FRONTEND_URL: str


class DevelopmentConfig(Config):
    SECRET_KEY = "crashtest"
    ENV = 'development'
    MONGO_HOST = os.environ.get('DB_HOSTNAME') or "127.0.0.1"
    MONGO_PORT = int(os.environ.get('DB_PORT') or 27018)
    MONGO_DBNAME = "tdctl"
    MONGO_URI = "mongodb://%s:%s/%s" % (MONGO_HOST, MONGO_PORT, MONGO_DBNAME)
    FRONTEND_URL = os.environ.get('FRONTEND_URL') or "localhost:3000"


class ProductionConfig(Config):
    SECRET_KEY = os.environ.get('SECRET_KEY') or ''
    ENV = 'production'
    MONGO_HOST = os.environ.get('DB_HOSTNAME') or ''
    MONGO_PORT = int(os.environ.get('DB_PORT') or 27017)
    MONGO_DBNAME = os.environ.get('DB')
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    try :
        del os.environ['DB_USER']
        del os.environ['DB_PASSWORD']
    except KeyError:
        # for CI test when env variables are not set
        pass
    MONGO_URI = "mongodb://%s:%s@%s:%s" % (DB_USER, DB_PASSWORD, MONGO_HOST, MONGO_PORT)
    FRONTEND_URL = os.environ.get('FRONTEND_URL') or "localhost:3000"

class TestConfig(Config):
    SECRET_KEY = "test"
    ENV = 'test'
    MONGO_HOST = os.environ.get('TEST_DB_HOSTNAME') or '127.0.0.1'
    MONGO_PORT = int(os.environ.get('TEST_DB_PORT') or 27018)
    MONGO_DBNAME = "test"
    MONGO_URI = "mongodb://%s:%s/%s" % (MONGO_HOST, MONGO_PORT, MONGO_DBNAME)
    FRONTEND_URL = os.environ.get('FRONTEND_URL') or "localhost:3000"


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'test' : TestConfig,
    'default': DevelopmentConfig
}
