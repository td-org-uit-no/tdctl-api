import os


class Config:
    SECRET_KEY: str
    ENV: str
    MONGO_HOST: str
    MONGO_PORT: int
    MONGO_DBNAME: str
    MONGO_URI: str


class DevelopmentConfig(Config):
    SECRET_KEY = "crashtest"
    ENV = 'development'
    MONGO_HOST = "127.0.0.1"
    MONGO_PORT = 27018
    MONGO_DBNAME = "tdctl"
    MONGO_URI = "mongodb://%s:%s/%s" % (MONGO_HOST, MONGO_PORT, MONGO_DBNAME)


class ProductionConfig(Config):
    SECRET_KEY = os.environ.get('SECRET_KEY')
    ENV = 'production'
    MONGO_HOST = os.environ.get('DB_HOSTNAME')
    MONGO_PORT = os.environ.get('DB_PORT')
    MONGO_DBNAME = "tdctl"
    MONGO_URI = "mongodb://%s:%s/%s" % (MONGO_HOST, MONGO_PORT, MONGO_DBNAME)


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
