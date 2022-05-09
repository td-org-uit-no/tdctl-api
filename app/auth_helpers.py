from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pymongo import database
from datetime import datetime, timedelta
from jwt import encode, decode, ExpiredSignatureError, DecodeError
from uuid import uuid4

from .config import Config
from .models import MemberDB, RefreshTokenPayload, AccessTokenPayload

security_scheme = HTTPBearer()


def authorize(request: Request, token: HTTPAuthorizationCredentials = Depends(security_scheme)):
    '''
    Takes a request and goes through all the steps of authenticating it.
    On valid request, function will return the payload.
    If token used in the request is invalid, a number of errors can be raised
    and returned.
    '''
    payload = AccessTokenPayload.parse_obj(decode_token(
        token.credentials, request.app.config))
    if not payload.access_token:
        raise HTTPException(
            401, 'The token is not an access token. Is this a refresh token?')
    return payload


def role_required(accessToken: AccessTokenPayload, role: str):
    if accessToken.role != role:
        raise HTTPException(403, 'No privileges to access this resource')


def create_token(user: MemberDB, config: Config):
    payload = {
        # Token lifetime
        'exp': datetime.utcnow() + timedelta(days=0, minutes=10),
        'iat': datetime.utcnow(),
        'user_id': user.id.hex,
        'role': user.role,
        'access_token': True        # Separates it from refresh token
    }
    return encode(payload, config.SECRET_KEY, algorithm='HS256')


def create_refresh_token(user: MemberDB, config: Config):
    return encode({
        # Token lifetime
        "exp": datetime.utcnow() + timedelta(days=0, minutes=60),  # Expiry
        "iat": datetime.utcnow(),                                  # Issued at
        "jti": uuid4().hex,                                        # Token id
        "user_id": user.id.hex
    }, config.SECRET_KEY, algorithm='HS256')


def decode_token(token: bytes, config: Config) -> dict:
    try:
        # Attempt to decode the token found in header
        return decode(token.encode('utf-8'), config.SECRET_KEY)
    except DecodeError:
        # Missing segments
        raise HTTPException(401, 'Token has incorrect format.')
    except ExpiredSignatureError:
        raise HTTPException(401, 'Token has expired.')
    #  except:
    #    raise HTTPException(401, 'Unknown error')


def blacklist_token(refreshToken: RefreshTokenPayload, db: database):
    '''
    Blacklists the provided (decoded) refresh token.
    '''
    # Insert token into database
    db.tokens.insert_one(refreshToken.dict())


def is_blacklisted(refreshToken: RefreshTokenPayload, db: database):
    '''
    Check if the provided (decoded) refresh token is blacklisted.
    '''
    if (db.tokens.find_one({"jti": refreshToken.jti})):
        return True
    return False
