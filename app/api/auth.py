from flask_restx import Namespace, Resource
from werkzeug.exceptions import Unauthorized, BadRequest, NotFound
from werkzeug.security import check_password_hash
from pymongo import ReturnDocument

from ..db import mongo
from ..models import Login, Tokens, RefreshToken, ConfirmationCode
from ..auth_helpers import (create_token, create_refresh_token,
                            login_required, blacklist_token, is_blacklisted,
                            decode_token)

api = Namespace('auth', description="authentication management")
api.models['Login'] = Login
api.models['Tokens'] = Tokens
api.models['RefreshToken'] = RefreshToken
api.models['ConfirmationCode'] = ConfirmationCode


@api.route('/login/')
class Auth(Resource):
    @api.expect(Login, validate=True)
    @api.marshal_with(Tokens)
    @api.response(400, "Bad request: Incorrect format")
    @api.response(401, "Incorrect e-mail or password")
    def post(self):
        '''Logs user in using credentials and issues tokens'''
        # Check if user exists
        user = mongo.db.members.find_one({'email': api.payload['email']})
        if not user:
            raise Unauthorized('Incorrect e-mail or password')
        # Check if password matches
        if not check_password_hash(user['password'], api.payload['password']):
            raise Unauthorized('Incorrect e-mail or password')
        # Create token
        token = create_token(user)
        # Create refresh token
        refreshToken = create_refresh_token(user)
        # Return tokens in decoded style
        return {"token": token.decode(), "refreshToken": refreshToken.decode()}


@api.route('/logout/')  # noqa: F811 # Redef error
class Auth(Resource):
    @api.doc(security="Bearer Token")
    @login_required(api)
    @api.expect(RefreshToken, validate=True)
    @api.response(400, "Bad request: Incorrect format")
    def post(self, token):
        '''Logs user out and invalidates tokens'''
        try:
            refreshToken = decode_token(
                api.payload["refreshToken"].encode('utf-8'))
        except:  # noqa: E722
            raise Unauthorized("Refresh token is invalid")

        blacklist_token(refreshToken)
        return 200


@api.route('/renew/')  # noqa: F811 # Redef error
class Auth(Resource):
    @api.marshal_with(Tokens)
    @api.expect(RefreshToken, validate=True)
    def post(self):
        '''Renews tokens by reissuing valid tokens.'''
        # Decode the old refresh token. Potentially raising errors
        oldRefreshToken = decode_token(
            api.payload["refreshToken"].encode('utf-8'))

        # Check if already used / blacklisted
        if is_blacklisted(oldRefreshToken):
            raise Unauthorized('Refresh token is blacklisted')
        # Find member associated with token.
        user = mongo.db.members.find_one({'_id': oldRefreshToken('user_id')})
        if not user:
            # Not sure if this can happen
            raise BadRequest(
                'The member associated with refresh token no longer exists')

        # Create new tokens
        token = create_token(user)
        refreshToken = create_refresh_token(user)

        # Blacklist the old token
        blacklist_token(oldRefreshToken)
        return {
            "token": token.decode(),
            "refreshToken": refreshToken.decode()
        }


@api.route('/confirm/')  # noqa: F811 # Redef error
class Auth(Resource):
    @api.expect(ConfirmationCode, validate=True)
    @api.response(200, "Success")
    @api.response(404, "Not found: Confirmation token could not be matched")
    def post(self):
        dbConf = mongo.db.confirmations.find_one_and_delete(
            {'confirmationCode': api.payload['confirmationCode']})

        if not dbConf:
            raise NotFound("Confirmation token could not be matched")

        user = mongo.db.members.find_one_and_update(
            {'_id': dbConf['user_id']},
            {"$set":
                {'role': 'member',
                 'status': 'active'}
             },
            return_document=ReturnDocument.AFTER)

        if not user:
            # User associated with confirmation token does not exist.
            raise NotFound('Confirmation token could not be matched')

        return 200
