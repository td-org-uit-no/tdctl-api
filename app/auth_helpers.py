from flask import request
from functools import wraps
from flask import current_app as app
from flask_restplus import Namespace
from datetime import datetime, timedelta
from werkzeug.exceptions import Unauthorized, Forbidden
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


def authorize(request):
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

    try:
        # Attempt to decode the token found in header
        return decode(tokens[1].encode('utf-8'), app.config.get('SECRET_KEY'))
    except DecodeError:
        # Missing segments
        raise Unauthorized('Token has incorrect format.')
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


'''
We need to determine if we are going to use roles as a hierarchy
or as separate roles before continuing the logic in this decorator
'''


def role_required(api, roles):
    '''
    Decorator to aid with authorization of a resource.

    Note:
        Using this implicitly replaces the functionality of login_required.

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
            if 'ROLES' not in payload:
                # Should this be forbidden or unauthorized?
                raise Forbidden('')

            if 'token' in func.__code__.co_varnames:
                return func(*args, **kwargs, token=payload)
            else:
                return func(*args, **kwargs)
        return inner
    return decorate


def login_required(api):
    '''
    Decorator to aid with validation and interpretation of tokens.

    :type api: flask_restplus.Namespace
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
