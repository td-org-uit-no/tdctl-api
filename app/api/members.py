from fastapi import APIRouter, Request, HTTPException, Depends
from werkzeug.security import generate_password_hash
from typing import List
from uuid import uuid4

from ..models import Member, MemberDB, MemberInput, AccessTokenPayload
from ..auth_helpers import authorize, role_required
from ..db import get_database

router = APIRouter()


@router.post('/', tags=["member"])
def create_new_member(request: Request, newMember: MemberInput):
    '''
        TODO:
            * E-mail confirmation
            * Currently returns a ConfirmationCode for development purposes
            * Password requirements
    '''
    db = get_database(request)
    exists = db.members.find_one({'email': newMember.email.lower()})
    if exists:
        raise HTTPException(409, 'E-mail is already in use.')
    member = MemberDB.parse_obj(newMember.dict())
    member.id = uuid4().hex  # Generate ID
    member.email = newMember.email.lower(),  # Lowercase e-mail
    member.password = generate_password_hash(newMember.password),
    member.role = 'unconfirmed',
    member.status = 'inactive',

    # Create user object
    db.members.insert_one(member.dict())

    # Create confirmation code
    confirmationCode = uuid4().hex
    db.confirmations.insert_one(
        {"confirmationCode": confirmationCode, 'user_id': newMember.id}
    )
    return confirmationCode


@router.get('/', tags=["member"])
def get_member_associated_with_token(request: Request, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    currentMember = db.members.find_one({'id': token.user_id})
    if not currentMember:
        raise HTTPException(404, "User could not be found")
    return Member.parse_obj(currentMember)


@router.get('/{id}', tags=["member"], response_model=Member, responses={404: {"model": None}})
def get_member_by_id(request: Request, id: str, token: dict = Depends(authorize)):
    '''Returns a user object associated with id passed in'''
    db = get_database(request)
    member = db.members.find_one({'id': id})
    if not member:
        raise HTTPException(404, 'Member not found')
    return Member.parse_obj(member)


@router.get("s/", tags=["member"], response_model=List[Member])
def get_all_members(request: Request, token: AccessTokenPayload = Depends(authorize)):
    '''List all members objects'''
    role_required(token, 'admin')
    db = get_database(request)
    return [Member.parse_obj(m) for m in db.members.find()]
