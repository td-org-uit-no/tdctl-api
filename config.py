import os
''' Example configurations'''


class DevelopmentConfig:
    SECRET_KEY = "crashtest"
    ENV = 'development'
    DEBUG = True  # Sets 'hot-reloading'


class ProductionConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY')


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
