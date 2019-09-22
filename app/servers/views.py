from . import servers

@servers.route('/')
def index():
    return {}
