from flask import request
from functools import wraps
from flask import current_app as app
from flask_restplus import Namespace
from datetime import datetime, timedelta
from werkzeug.exceptions import Unauthorized, BadRequest
from jwt import encode, decode, ExpiredSignatureError, DecodeError


def create_token(user):
    payload = {
        # Token lifetime
        'exp': datetime.utcnow() + timedelta(days=0, minutes=60),
        'iat': datetime.utcnow(),
        'user_id': user['id'],
        'roles': user['roles']
    }
    return encode(
        payload,
        app.config.get('SECRET_KEY'),
        algorithm='HS256'
    )


def decode_token(token):
    '''
    Decodes a token and returns content, effectively verifying the token

    :type token: bytes
    :param token: Token to be decoded and verified.

    Errors:
    400:
        - Token has incorrect format.
    401:
        - Token has expired.
        - Unknown error

    '''
    # TODO: Cover all the other types of error you can get from decode
    try:
        return decode(token, app.config.get('SECRET_KEY'))
    except DecodeError:
        # Missing segments
        raise BadRequest('Token has incorrect format.')
    except ExpiredSignatureError:
        raise Unauthorized('Token has expired.')
    except:  # noqa: E722
        raise Unauthorized('Unknown error')


def invalidate_token(token):
    # We need to invalidate the token somehow
    # And potentially clean the list of invalid tokens
    pass


def is_blacklisted(token):
    # Checks the validity of a token
    return False


def login_required(api, additionalErrors={}):
    '''
    Decorator to aid with validation and interpretation of tokens.

    :type api: flask_restplus.Namespace
    :param api: Namespace used with decorator - sets response documentation.

    If decorated method has argument 'token', the body of the JWT
    will be passed along into the method
    '''
    errors = {
        400: '''Bad request - With one of the following messages:
        - Token is missing from the header.
        - Token prefix is incorrect.
        - Token has incorrect format.
        ''',
        401: '''Unauthorized - With one of the following messages:
        - Token has expired.
        - Unknown error
        '''
    }

    # Merge error keys
    for key in additionalErrors:
        if (key in errors):
            errors[key] = "%s - %s" % (errors[key], additionalErrors[key])
        else:
            errors[key] = additionalErrors[key]

    def _login_required(func):

        @Namespace.doc(api, responses=errors, security="Bearer Token")
        @wraps(func)
        def decorated(*args, **kwargs):
            # Check if token exists in header
            if 'Authorization' not in request.headers:
                raise BadRequest('Token is missing from the header.')

            # Check bearer prefix
            tokens = request.headers['Authorization'].split(' ')
            if (tokens[0] != 'Bearer'):
                raise BadRequest('Token prefix is incorrect.')

            # Attempt decoding token - Comes with another set of errors
            tokenBody = decode_token(tokens[1].encode('utf-8'))

            # Logic to pass token information into methods (or not)
            if 'token' in func.__code__.co_varnames:
                return func(*args, **kwargs, token=tokenBody)
            else:
                return func(*args, **kwargs)

        return decorated

    return _login_required
