import os


class DevelopmentConfig:
    SECRET_KEY = "crashtest"
    ENV = 'development'
    DEBUG = True  # Sets 'hot-reloading'
    MONGO_HOST = "127.0.0.1"
    MONGO_PORT = 27018
    MONGO_DBNAME = "tdctl"
    MONGO_URI = "mongodb://%s:%s/%s" % (MONGO_HOST, MONGO_PORT, MONGO_DBNAME)


class ProductionConfig:
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
