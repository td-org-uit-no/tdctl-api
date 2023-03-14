from uuid import UUID
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import get_database
from ..auth_helpers import create_token, create_refresh_token, decode_token, blacklist_token, delete_auth_cookies, is_blacklisted, authorize, set_auth_cookies
from ..models import Credentials, Status, MemberDB, RefreshTokenPayload, AccessTokenPayload, ChangePasswordPayload
from ..utils import validate_password, passwordError

router = APIRouter()


@router.post("/login", responses={401: {"model": None}})
def login(request: Request, credentials: Credentials, response: Response):
    credential_exception = HTTPException(401, "Invalid e-mail or password")
    db = get_database(request)
    member = db.members.find_one({'email': credentials.email.lower()})

    if not member:
        raise HTTPException(401, 'Invalid e-mail')
        #raise credential_exception
    member = MemberDB.parse_obj(member)

    if not check_password_hash(member.password, credentials.password):
        raise credential_exception

    if member.status != Status.active:
        # activate members on login
        db.members.find_one_and_update(
            {'id': member.id},
            {"$set": {'status': f'{Status.active}'}}
        )

    token = create_token(member, request.app.config)
    refresh_token = create_refresh_token(member, request.app.config)
    set_auth_cookies(response, token, refresh_token)
    response.status_code = 200

    return response


@router.post('/logout')
def logout(request: Request, response: Response):
    try:
        refresh_token = request.cookies.get("refresh_token") or ""
        token = RefreshTokenPayload.parse_obj(decode_token(
            refresh_token, request.app.config))
    except:
        raise HTTPException(401, "Refresh token is invalid")
    blacklist_token(token, request.app.db)
    
    delete_auth_cookies(response)
    response.status_code = 200
    return response


@router.post('/renew')
def renew(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(401, 'Refresh token is not present')

    tokenPayload = RefreshTokenPayload.parse_obj(
        decode_token(refresh_token, request.app.config))

    if is_blacklisted(tokenPayload, request.app.db):
        raise HTTPException(401, 'Refresh token is blacklisted')
    user = request.app.db.members.find_one({'id': UUID(tokenPayload.user_id)})
    if not user:
        # Edge case
        raise HTTPException(
            400, 'The member associated with refresh token no longer exists')
    user = MemberDB.parse_obj(user)
    token = create_token(user, request.app.config)
    refresh_token = create_refresh_token(user, request.app.config)
    set_auth_cookies(response, token, refresh_token)
    blacklist_token(tokenPayload, request.app.db)
    response.status_code = 200

    return response


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

@router.get("/token-info")
def token_info(token: AccessTokenPayload = Depends(authorize)):
    return { "user_id": token.user_id, "role": token.role, "exp": token.exp }
