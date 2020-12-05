from fastapi import APIRouter, Response, Request, HTTPException, Depends
from werkzeug.security import generate_password_hash
from typing import List
from uuid import uuid4

from ..models import Member, MemberDB, MemberInput, AccessTokenPayload
from ..auth_helpers import authorize, role_required
from ..db import get_database
from ..util import validate_password, passwordError

router = APIRouter()

@router.post('/')
def create_new_member(request: Request, newMember: MemberInput):
    '''
        TODO:\n
            - E-mail confirmation
            - Currently returns a ConfirmationCode for development purposes
    '''
    db = get_database(request)
    exists = db.members.find_one({'email': newMember.email.lower()})
    if exists:
        raise HTTPException(409, 'E-mail is already in use.')

    if not validate_password(newMember.password):
        raise HTTPException(400, passwordError)

    additionalFields = {
        'id': uuid4().hex,  # Generate ID
        'email': newMember.email.lower(),  # Lowercase e-mail
        'password': generate_password_hash(newMember.password),
        'role': 'unconfirmed',
        'status': 'inactive',
    }

    member = newMember.dict()
    member.update(additionalFields)
    # Create user object
    db.members.insert_one(member)

    # Create confirmation code
    confirmationCode=uuid4().hex
    db.confirmations.insert_one(
        {"confirmationCode": confirmationCode, 'user_id': member['id']}
    )
    return confirmationCode


@ router.get('/')
def get_member_associated_with_token(request: Request, token: AccessTokenPayload=Depends(authorize)):
    db=get_database(request)
    currentMember=db.members.find_one({'id': token.user_id})
    if not currentMember:
        raise HTTPException(404, "User could not be found")
    return Member.parse_obj(currentMember)


@ router.get('/{id}', response_model=Member, responses={404: {"model": None}})
def get_member_by_id(request: Request, id: str, token: dict=Depends(authorize)):
    '''Returns a user object associated with id passed in'''
    db=get_database(request)
    member=db.members.find_one({'id': id})
    if not member:
        raise HTTPException(404, 'Member not found')
    return Member.parse_obj(member)


@ router.get("s/", response_model=List[Member])
def get_all_members(request: Request, token: AccessTokenPayload=Depends(authorize)):
    '''List all members objects'''
    role_required(token, 'admin')
    db=get_database(request)
    return [Member.parse_obj(m) for m in db.members.find()]

@ router.post('/activate')
def change_status(request: Request, token: AccessTokenPayload=Depends(authorize)):
    db=get_database(request)
    member = db.members.find_one({'id': token.user_id})
    if not member:
        raise HTTPException(404, 'Member not found')
    result = db.members.find_one_and_update(
        {'id': token.user_id},
        { "$set": {'status': 'activ'}}
    )
    if not result:
        raise HTTPException(500)
    return Response(status_code=200)
