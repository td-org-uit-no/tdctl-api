from flask_restx import Namespace, Resource
from werkzeug.exceptions import NotFound, Conflict
from werkzeug.security import generate_password_hash
from uuid import uuid4

from ..db import mongo
from ..models import PartialMember, Member as _Member, ConfirmationCode
from ..auth_helpers import login_required, role_required

api = Namespace('member', description="interfaces to interact with members")

# Register model
api.models['PartialMember'] = PartialMember
api.models['ConfirmationCode'] = ConfirmationCode
api.models['Member'] = _Member


@api.route('/<int:id>')
class Member(Resource):
    @api.marshal_with(_Member)
    @api.expect(id, validate=True)
    @role_required(api, 'admin')
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
    @api.marshal_with(ConfirmationCode)
    @api.response(409, "Conflict: E-mail is already in use.")
    @api.response(400, "Bad request: Incorrect format")
    def post(self):
        '''Creates a new member. Returns the complete object.'''
        '''
        TODO:
            * E-mail confirmation
            * Currently returns a ConfirmationCode for development purposes
            * Password requirements
            * Some e-mail validation (Mostly handled by confirmation)
        '''

        exists = mongo.db.members.find_one(
            {'email': api.payload['email'].lower()})
        if exists:
            raise Conflict('E-mail is already in use.')

        # Build the new member
        new = api.payload
        new['email'] = new['email'].lower()  # Lowercase e-mail
        new['_id'] = uuid4().hex  # Generate ID
        new['password'] = generate_password_hash(api.payload['password'])
        new['role'] = 'unconfirmed'
        new['status'] = 'inactive'  # Set default status for new members
        # Create the user!
        mongo.db.members.insert_one(new)

        confirmationCode = uuid4().hex
        mongo.db.confirmations.insert_one(
            {
                "confirmationCode": confirmationCode,
                'user_id': new['_id']
            })
        return confirmationCode

    @api.marshal_with(_Member)
    @login_required(api)
    def get(self, token):
        '''Returns a user object associated with token in header'''
        return mongo.db.members.find_one_or_404({'id': token['user_id']})


@api.route('s/')  # noqa: F811  # Redef error
class Member(Resource):
    @api.marshal_list_with(_Member)
    @role_required(api, 'admin')
    def get(self):
        '''List all members objects'''
        return [m for m in mongo.db.members.find()]
