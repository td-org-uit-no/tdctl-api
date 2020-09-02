from flask_restx import Api
from flask import url_for
from .members import api as members
# from .servers import api as servers
# from .events import api as events
from .auth import api as auth


authorizations = {
    'Bearer Token': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': 'Bearer token in format: [Bearer TOKEN]'
    }
}

# Fix for mixed content when deployed on https. Will be removed when resolved.
# https://github.com/python-restx/flask-restx/issues/188
class PatchedApi(Api):
    @property
    def specs_url(self):
        return url_for(self.endpoint('specs'))

# General about API
api = PatchedApi(
    title='TDCTL-API',
    version='0.0',
    description='''TDCTL-database API.
    Everything related to Tromsøstudentenes Dataforening''',
    contact='td@list.uit.no', authorizations=authorizations
)


# Register namespaces
api.add_namespace(members)
# api.add_namespace(servers)
# api.add_namespace(events)
api.add_namespace(auth)
