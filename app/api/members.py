from fastapi import APIRouter, Response, Request, HTTPException, Depends
from werkzeug.security import generate_password_hash
from pymongo import ReturnDocument
from typing import List
from uuid import uuid4, UUID

from app.utils.validation import validate_uuid

from ..models import Member, MemberInput, MemberUpdate, AccessTokenPayload
from ..auth_helpers import authorize, role_required
from ..db import get_database
from ..utils import validate_password, passwordError

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
    pwd = generate_password_hash(newMember.password)
    uid = uuid4().hex
    additionalFields = {
        'id': uid,
        'email': newMember.email.lower(),  # Lowercase e-mail
        'password': pwd,
        'role': 'unconfirmed',
        'status': 'inactive',
    }

    member = newMember.dict()
    member.update(additionalFields)
    # Create user object
    db.members.insert_one(member)

    # Create confirmation code
    confirmationCode = uuid4().hex
    db.confirmations.insert_one(
        {"confirmationCode": confirmationCode, 'user_id': member['id']}
    )
    return confirmationCode


@router.get('/')
def get_member_associated_with_token(request: Request, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    currentMember = db.members.find_one({'id': token.user_id})
    if not currentMember:
        raise HTTPException(404, "User could not be found")
    return Member.parse_obj(currentMember)


@router.get('/{id}', response_model=Member, responses={404: {"model": None}}, dependencies=[Depends(validate_uuid)])
def get_member_by_id(request: Request, id: str, token: dict = Depends(authorize)):
    '''Returns a user object associated with id passed in'''
    db = get_database(request)
    # removes dashes
    member = db.members.find_one({'id': UUID(id).hex})
    if not member:
        raise HTTPException(404, 'Member not found')
    return Member.parse_obj(member)


@router.get("s/", response_model=List[Member])
def get_all_members(request: Request, token: AccessTokenPayload = Depends(authorize)):
    '''List all members objects'''
    role_required(token, 'admin')
    db = get_database(request)
    return [Member.parse_obj(m) for m in db.members.find()]


@router.post('/activate')
def change_status(request: Request, token: AccessTokenPayload = Depends(authorize)):
    '''Sets the member status to active'''
    db = get_database(request)
    member = db.members.find_one({'id': token.user_id})
    if not member:
        raise HTTPException(404, 'Member not found')
    result = db.members.find_one_and_update(
        {'id': token.user_id},
        {"$set": {'status': 'active'}}
    )
    if not result:
        raise HTTPException(500)
    return Response(status_code=200)


@router.post('/confirm/{code}')
def confirm_email(request: Request, code: str):
    '''Used to confirm the members e-mail address through activation code'''
    NotMatchedError = HTTPException(
        404, "Confirmation token could not be matched")
    db = get_database(request)
    validated = db.confirmations.find_one_and_delete(
        {'confirmationCode': code})
    if not validated:
        raise NotMatchedError

    user = db.members.find_one_and_update(
        {'id': validated['user_id']},
        {"$set":
         {'role': 'member',
          'status': 'active'}
         },
        return_document=ReturnDocument.AFTER)
    if not user:
        # User associated with confirmation token does not exist.
        raise NotMatchedError

    return Response(status_code=200)

@router.post('/confirm/code/{email}')
def generate_new_confirmation_code(request: Request, email: str): 
    '''Used to generate a new confirmation code for a member'''
    NonExistentMemberError = HTTPException(
        404, "A member with the given e-mail address does not exist"
    )
    MemberAlreadyConfirmedError = HTTPException(
        400, 'Member is already confirmed'
    )

    db = get_database(request)
    member = db.members.find_one({'email': email})

    if not member:
        # Member assoiciated with the email was not found
        raise NonExistentMemberError

    if member['role'] != 'unconfirmed':
        # Member associated with the email is already activated
        raise MemberAlreadyConfirmedError


    # delete existing activation code associated with member
    db.confirmations.find_one_and_delete({'id': member['id']})
    
    newConfirmationCode = uuid4().hex
    result = db.confirmations.insert_one(
        {"confirmationCode": newConfirmationCode, 'user_id': member['id']}
    )

    if not result:
        # An error occured when updating the user with the confirmation code
        raise HTTPException(500)
    
    return newConfirmationCode


@router.put('/')
def update_member(request: Request, memberData: MemberUpdate, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    user = db.members.find_one({'id': token.user_id})
    if not user:
        raise HTTPException(404, "User not found")

    values = memberData.dict()
    updateInfo = {}
    for key in values:
        if values[key]:
            updateInfo[key] = values[key]

    if not updateInfo:
        return HTTPException(400)

    result = db.members.find_one_and_update(
        {'id': token.user_id},
        {"$set": updateInfo})

    if not result:
        raise HTTPException(500)

    return Response(status_code=201)
