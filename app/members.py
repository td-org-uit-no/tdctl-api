from flask_restplus import Namespace, Resource

api = Namespace('member', description="interfaces to interact with members")


@api.route('/<int:memberid>')
class Member(Resource):
    def get(self, memberid):
        '''List information about a single member'''
        # Should fetch member object from database and return it
        member = {
            'id': memberid,
            'name': 'Somename'
        }
        return member

    def post(self, memberid):
        '''Creates a new member'''
        return {id: memberid}

    def put(self, memberid):
        '''Updates a member with the fields supplied'''
        return memberid

    def delete(self, memberid):
        '''Deletes a member based on id'''
        return memberid


@api.route('/')
class Member(Resource):
    def get(self):
        '''List all members'''
        # Should fetch all members from database and return it
        members = [
            {
                'id': 0,
                'name': 'First guy'
            },
            {
                'id': 1,
                'name': 'Second guy'
            }
        ]
        return members
