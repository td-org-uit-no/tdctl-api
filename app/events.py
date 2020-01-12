from flask_restplus import Namespace, Resource

api = Namespace('event', description="interfaces to interact with events")


@api.route('/<int:eventid>')
class event(Resource):
    def get(self, eventid):

        # Should fetch event object from database
        event = {
            'id': eventid,
            'name': 'Some event name'
        }
        return event
