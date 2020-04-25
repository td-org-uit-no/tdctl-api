from flask import request, current_app as app
from functools import wraps
from flask_restx import Namespace
from datetime import datetime, timedelta
from werkzeug.exceptions import Unauthorized, Forbidden

from jwt import encode, decode, ExpiredSignatureError, DecodeError
from uuid import uuid4
from .db import mongo


def create_token(user: dict):
    payload = {
        # Token lifetime
        'exp': datetime.utcnow() + timedelta(days=0, minutes=10),
        'iat': datetime.utcnow(),
        'user_id': user['_id'].hex,
        'role': user['role'],
        'access_token': True        # Separates it from refresh token
    }
    return encode(payload, app.config.get('SECRET_KEY'), algorithm='HS256')


def create_refresh_token(user: dict):
    return encode({
        # Token lifetime
        "exp": datetime.utcnow() + timedelta(days=0, minutes=60),  # Expiry
        "iat": datetime.utcnow(),                                  # Issued at
        "jti": uuid4().hex,                                        # Token id
        "user_id": user['_id'].hex
    }, app.config.get('SECRET_KEY'), algorithm='HS256')


def decode_token(token: bytes):
    try:
        # Attempt to decode the token found in header
        return decode(token.encode('utf-8'), app.config.get('SECRET_KEY'))
    except DecodeError:
        # Missing segments
        raise Unauthorized('Token has incorrect format.')
    except ExpiredSignatureError:
        raise Unauthorized('Token has expired.')
    except:  # noqa: E722
        raise Unauthorized('Unknown error')


def authorize(request: request):
    '''
    Takes a request and goes through all the steps of authenticating it.
    On valid request, function will return the payload.
    If token used in the request is invalid, a number of errors can be raised
    and returned.

    :type request: flask.request
    :param request: Request to be authenticated.

    '''
    # Check if token exists in header
    if 'Authorization' not in request.headers:
        raise Unauthorized('Token is missing from the header.')

    # Check bearer prefix
    tokens = request.headers['Authorization'].split(' ')
    if (tokens[0] != 'Bearer'):
        raise Unauthorized('Token prefix is incorrect.')

    token = decode_token(tokens[1])
    if not token['access_token']:
        raise Unauthorized(
            'The token is not an access token. Is this a refresh token?')
    return token


def blacklist_token(refreshToken: dict):
    '''
    Blacklists the provided (decoded) refresh token.
    '''
    # Insert token into database
    mongo.db.tokens.insert_one(
        {
            # We have to parse the timestamps into date object for mongodb
            "exp": datetime.utcfromtimestamp(refreshToken['exp']),
            "iat": datetime.utcfromtimestamp(refreshToken['iat']),
            "jti": refreshToken["jti"],
            "user_id": refreshToken["user_id"]
        })
    # Return something?


def is_blacklisted(refreshToken: dict):
    '''
    Check if the provided (decoded) refresh token is blacklisted.
    '''
    if (mongo.db.tokens.find_one({"jit": refreshToken["jit"]})):
        return True
    return False


def role_required(api: Namespace, role: str):
    '''
    Decorator to aid with authorization of a resource.

    Note:
        Using this implicitly replaces the functionality of login_required
        and only one of the decorators should be used at the same time.

    '''
    errors = {
        401: "Unauthorized: Token is invalid, expired or has incorrect format",
        403: "Forbidden: No privileges to access this resource"
    }

    def decorate(func):
        @Namespace.doc(api, responses=errors, security="Bearer Token")
        @wraps(func)
        def inner(*args, **kwargs):
            payload = authorize(request)

            # If token does not contain role, or the role isnt sufficient
            if "role" not in payload or payload['role'] is not role:
                raise Forbidden('No privileges to access this resource')

            if 'token' in func.__code__.co_varnames:
                return func(*args, **kwargs, token=payload)
            else:
                return func(*args, **kwargs)
        return inner
    return decorate


def login_required(api: Namespace):
    '''
    Decorator to aid with validation and interpretation of tokens.

    :type api: flask_restx.Namespace
    :param api: Namespace used with decorator - sets response documentation.

    If decorated method has argument 'token', the body of the JWT
    will be passed along into the method
    '''
    errors = {
        401: "Unauthorized: Token is invalid, expired or has incorrect format"
    }

    def decorate(func):
        @Namespace.doc(api, responses=errors, security="Bearer Token")
        @wraps(func)
        def inner(*args, **kwargs):
            payload = authorize(request)

            # Handle request which require the token payload
            if 'token' in func.__code__.co_varnames:
                return func(*args, **kwargs, token=payload)
            else:
                return func(*args, **kwargs)

        return inner

    return decorate
