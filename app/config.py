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
    FRONTEND_URL = os.environ.get('FRONTEND_URL')


class ProductionConfig(Config):
    SECRET_KEY = os.environ.get('SECRET_KEY') or ''
    ENV = 'production'
    MONGO_HOST = os.environ.get('DB_HOSTNAME') or ''
    MONGO_PORT = int(os.environ.get('DB_PORT') or 27017)
    MONGO_DBNAME = "tdctl"
    MONGO_URI = "mongodb://%s:%s/%s" % (MONGO_HOST, MONGO_PORT, MONGO_DBNAME)
    FRONTEND_URL = os.environ.get('FRONTEND_URL')


class TestConfig(Config):
    SECRET_KEY = "test"
    ENV = 'test'
    MONGO_HOST = os.environ.get('TEST_DB_HOSTNAME') or '127.0.0.1'
    MONGO_PORT = 27018
    MONGO_DBNAME = "test"
    MONGO_URI = "mongodb://%s:%s/%s" % (MONGO_HOST, MONGO_PORT, MONGO_DBNAME)
    FRONTEND_URL = os.environ.get('FRONTEND_URL')


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'test' : TestConfig,
    'default': DevelopmentConfig
}
