from flask_restplus import Namespace, Resource
from werkzeug.exceptions import Unauthorized

from ..db import mongo
from ..models import loginModel, tokenModel
from ..auth_helpers import create_token, login_required, invalidate_token

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
        if not user:
            raise Unauthorized('Incorrect e-mail or password')
        # TODO:
        # * Hash the password from payload
        # * Match versus password
        #   * If password is wrong: 401 Unauthorized
        # Invalidate existing tokens related to user?
        # Create token
        token = create_token(user)
        # Create refresh token
        refreshToken = token
        # Return tokens in decoded style
        return {"token": token.decode(), "refreshToken": refreshToken.decode()}


@api.route('/logout/')  # noqa: F811 # Redef error
class Auth(Resource):
    @api.doc(security="Bearer Token")
    @login_required(api)
    def post(self, token):
        '''invalidates token'''
        invalidate_token(token)
        # TODO:
        # * Invalidate refresh token as well
        # Potentially run a cleanup of the validation list?
        return 200


@api.route('/renew/')  # noqa: F811 # Redef error
class Auth(Resource):
    @api.doc()
    @api.marshal_with(tokenModel)
    def get(self):
        '''renews bearer token'''
        # TODO:
        # * Check that refresh token is present
        # * Check that refresh token is valid (and unused)
        # * Fetch user associated with refresh token
        # * Create new token and refreshtoken for user
        # Return tokens in decoded style
        # return {"token": token.decode(), "refreshToken": refreshToken.decode()}
        return 200
