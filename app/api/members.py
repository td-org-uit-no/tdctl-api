from flask_restplus import Namespace, Resource
from werkzeug.exceptions import NotFound

from ..db import mongo
from ..token import login_required
from ..models import PartialMember, Member as _member

api = Namespace('member', description="interfaces to interact with members")

# Register model
api.models['PartialMember'] = PartialMember
api.models['Member'] = _member


@api.route('/<int:id>')
class Member(Resource):

    # TODO: Should this take id?
    @api.marshal_with(_member)
    @api.expect(id, validate=True)
    @login_required(api, additionalErrors={404: 'Not found - User not found'})
    def get(self, id):
        '''Returns a user object associated with id passed in'''
        member = mongo.db.members.find_one({'id': id})
        if not member:
            raise NotFound('User not found')
        return member

    # def put(self, id):
    #    '''Update member'''
    #    return id

    # def delete(self, id):
    #    '''Removes a member. Returns ?????'''
    #    return id


@api.route('/')  # noqa: F811  # Redef error
class Member(Resource):

    @api.expect(PartialMember, validate=True)
    @api.marshal_with(_member)
    def post(self):
        '''Creates a new member. Returns the complete object.'''
        # Check if e-mail already exists ?
        # Assign id ?
        api.payload['id'] = 1  # TODO: We need to set ID properly.
        res = mongo.db.members.insert_one(api.payload)
        return mongo.db.members.find_one(res.inserted_id)

    @api.marshal_with(_member)
    @login_required(api)
    def get(self, token):
        '''Returns a user object associated with token in header'''
        return mongo.db.members.find_one_or_404({'id': token['user_id']})


@api.route('s/')  # noqa: F811  # Redef error
class Member(Resource):
    @api.marshal_list_with(_member)
    @login_required(api)
    def get(self):
        '''List all members objects'''
        return [m for m in mongo.db.members.find()]
