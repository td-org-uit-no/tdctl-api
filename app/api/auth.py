from uuid import UUID
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import get_database
from ..auth_helpers import create_token, create_refresh_token, decode_token, blacklist_token, is_blacklisted, authorize
from ..models import Credentials, Tokens, MemberDB, RefreshToken, RefreshTokenPayload, AccessTokenPayload, ChangePasswordPayload
from ..utils import validate_password, passwordError

router = APIRouter()


@router.post("/login", response_model=Tokens, responses={401: {"model": None}})
def login(request: Request, credentials: Credentials):
    credential_exception = HTTPException(401, "Invalid e-mail or password")

    db = get_database(request)
    member = db.members.find_one({'email': credentials.email.lower()})
    if not member:
        raise HTTPException(401, 'Invalid e-mail')
        #raise credential_exception
    member = MemberDB.parse_obj(member)
    if not check_password_hash(member.password, credentials.password):
        raise credential_exception

    token = create_token(member, request.app.config)
    refreshToken = create_refresh_token(member, request.app.config)
    return {"accessToken": token, "refreshToken": refreshToken}


@router.post('/logout')
def logout(request: Request, refreshToken: RefreshToken):
    try:
        token = RefreshTokenPayload.parse_obj(decode_token(
            refreshToken.refreshToken, request.app.config))
    except:
        raise HTTPException(401, "Refresh token is invalid")
    blacklist_token(token, request.app.db)
    return Response(status_code=200)


@router.post('/renew', response_model=Tokens)
def renew(request: Request, refreshToken: RefreshToken):
    tokenPayload = RefreshTokenPayload.parse_obj(
        decode_token(refreshToken.refreshToken, request.app.config))

    if is_blacklisted(tokenPayload, request.app.db):
        raise HTTPException(401, 'Refresh token is blacklisted')
    user = request.app.db.members.find_one({'id': UUID(tokenPayload.user_id)})
    if not user:
        # Edge case
        raise HTTPException(
            400, 'The member associated with refresh token no longer exists')
    user = MemberDB.parse_obj(user)
    token = create_token(user, request.app.config)
    refreshToken = create_refresh_token(user, request.app.config)
    blacklist_token(tokenPayload, request.app.db)
    return {"accessToken": token, "refreshToken": refreshToken}


@router.post('/password')
def change_password(passwords: ChangePasswordPayload, request: Request, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    user = MemberDB.parse_obj(db.members.find_one({'id': UUID(token.user_id)}))
    if not user:
        raise HTTPException(401, 'User not found')

    if not check_password_hash(user.password, passwords.password):
        raise HTTPException(403, 'Wrong password')

    if not validate_password(passwords.newPassword):
        raise HTTPException(400, passwordError)

    new_password = generate_password_hash(passwords.newPassword)
    result = db.members.find_one_and_update(
        {'id': user.id},
        {"$set": {'password': new_password}})

    if not result:
        raise HTTPException(500)

    return Response(status_code=200)
