from ..models import loginModel, tokenModel
from flask_restplus import Namespace, Resource

from ..db import mongo
from ..token import (create_token, decode_token,
                     login_required, invalidate_token)

api = Namespace('auth', description="authentication management")
api.models['loginModel'] = loginModel
api.models['tokenModel'] = tokenModel


@api.route('/login/')
class Auth(Resource):
    @api.expect(loginModel, validate=True)
    @api.marshal_with(tokenModel)
    def post(self):
        '''Takes login information and returns a token if correct'''
        user = mongo.db.members.find_one({'email': api.payload.get('email')})
        print(user)
        token = create_token(user)
        print(decode_token(token))

        return {"token": token.decode(), "refreshToken": token.decode()}


@api.route('/logout/')  # noqa: F811 # Redef error
class Auth(Resource):
    @api.doc(security="Bearer Token")
    @login_required(api)
    def post(self, token):
        '''invalidates token'''
        invalidate_token(token)
        return 200


@api.route('/renew/')  # noqa: F811 # Redef error
class Auth(Resource):
    @api.doc()
    @api.marshal_with(tokenModel)
    def get(self):
        '''renews bearer token'''
        return 200
