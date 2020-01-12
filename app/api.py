from flask_restplus import Api
from .members import api as members
from .servers import api as servers
from .events import api as events


# General about API
api = Api(
    title='TDCTL-API',
    version='0.0',
    description='''TDCTL-database API.
    Everything related to Tromsøstudentenes Dataforening''',
    contact='td@list.uit.no'
)

# Register namespaces
api.add_namespace(members)
api.add_namespace(servers)
api.add_namespace(events)
