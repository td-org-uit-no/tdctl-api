from flask_restplus import Namespace, Resource
from ..db import mongo
from ..models import PartialMember, Member as _Member
api = Namespace('member', description="interfaces to interact with members")

# Register model
api.models['PartialMember'] = PartialMember
api.models['Member'] = _Member


@api.route('/<int:memberid>')
class Member(Resource):
    @api.marshal_with(_Member)
    def get(self, memberid):
        '''Returns a member object.'''
        # Should fetch member object from database and return it
        member = mongo.db.members.find_one({'id': memberid})
        return member

    # TODO
    def put(self, memberid):
        '''Updates a member with the fields submitted, and returns new member object.'''
        return memberid

    # TODO
    def delete(self, memberid):
        '''Removes a member. Returns ?????'''
        return memberid


@api.route('/')  # noqa: F811  # Disables flake8 error with redefinition
class Member(Resource):
    @api.marshal_list_with(_Member)
    def get(self):
        '''List all members objects'''
        members = mongo.db.members.find()
        # Should fetch all members from database and return it
        return [m for m in members]

    @api.doc(body=PartialMember)
    @api.expect(PartialMember, validate=True)
    @api.marshal_with(_Member)
    def post(self):
        '''Creates a new member. Returns the complete object.'''
        res = mongo.db.members.insert_one(api.payload)
        return mongo.db.members.find_one(res.inserted_id)
