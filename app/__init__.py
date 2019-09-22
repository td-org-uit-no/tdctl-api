from flask_api import FlaskAPI
from config import config


def create_app(config_name):

    app = FlaskAPI(__name__)

    app.config.from_object(config[config_name])

    from .root import root as root_blueprint
    app.register_blueprint(root_blueprint)
    
    from .events import events as events_blueprint
    app.register_blueprint(events_blueprint, url_prefix="/events")
    
    from .members import members as members_blueprint
    app.register_blueprint(members_blueprint, url_prefix="/members")
    
    from .servers import servers as servers_blueprint
    app.register_blueprint(servers_blueprint, url_prefix="/servers")

    return app
