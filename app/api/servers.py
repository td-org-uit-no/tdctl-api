from flask_restx import Namespace, Resource

api = Namespace('server',  description="interfaces to interact with servers")


@api.route('/<int:serverid>')
class Server(Resource):
    def get(self, serverid):

        # Should fetch server object from database and return it
        server = {
            'id': serverid,
            'name': 'Somename'
        }
        return server
