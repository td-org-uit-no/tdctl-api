from flask_restplus import Namespace, Resource
from werkzeug.exceptions import NotFound, Conflict
from werkzeug.security import generate_password_hash
from uuid import uuid4

from ..db import mongo
from ..models import PartialMember, Member as _Member
from ..auth_helpers import login_required, role_required

api = Namespace('member', description="interfaces to interact with members")

# Register model
api.models['PartialMember'] = PartialMember
api.models['Member'] = _Member


@api.route('/<int:id>')
class Member(Resource):
    @api.marshal_with(_Member)
    @api.expect(id, validate=True)
    @role_required(api, 'Member')
    @api.response(404, "Not found: User not found")
    def get(self, id):
        '''Returns a user object associated with id passed in'''
        member = mongo.db.members.find_one({'id': id})
        if not member:
            raise NotFound('User not found')
        return member


@api.route('/')  # noqa: F811  # Redef error
class Member(Resource):

    @api.expect(PartialMember, validate=True)
    @api.marshal_with(_Member)
    @api.response(409, "Conflict: E-mail is already in use.")
    def post(self):
        '''Creates a new member. Returns the complete object.'''
        existingUser = mongo.db.members.find_one(
            {'email': api.payload['email'].lower()})
        if existingUser:
            raise Conflict('E-mail is already in use.')

        # Build the new member
        newMember = api.payload
        newMember['email'] = newMember['email'].lower()  # Lowercase e-mail
        newMember['_id'] = uuid4()  # Generate ID
        newMember['password'] = generate_password_hash(api.payload['password'])
        newMember['STATUS'] = 'INACTIVE'  # Set default status for new members

        res = mongo.db.members.insert_one(newMember)  # Create the user!

        # TODO:
        #   * E-mail confirmation
        #   * Password requirements
        #   * Some tiny e-mail validation (Mostly handled by confirmation)

        return mongo.db.members.find_one(res.inserted_id)

    @api.marshal_with(_Member)
    @login_required(api)
    def get(self, token):
        '''Returns a user object associated with token in header'''
        return mongo.db.members.find_one_or_404({'id': token['user_id']})


@api.route('s/')  # noqa: F811  # Redef error
class Member(Resource):
    @api.marshal_list_with(_Member)
    @login_required(api)
    def get(self):
        '''List all members objects'''
        return [m for m in mongo.db.members.find()]
