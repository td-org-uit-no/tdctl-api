from fastapi import APIRouter, Request, HTTPException, Depends, Response
from uuid import UUID, uuid4
from pydantic import Field
from pydantic.main import BaseModel
from pydantic.types import PositiveInt
from werkzeug.security import generate_password_hash
from app.utils.validation import validate_password, validate_uuid
from ..db import get_database
from ..models import AccessTokenPayload, AdminMemberUpdate, MemberInput, PenaltyInput, Role, Status
from ..auth_helpers import authorize_admin
from ..utils import passwordError

router = APIRouter()

@router.post('/give-admin-privileges/{id}', dependencies=[Depends(validate_uuid)])
def give_existing_user_admin_privileges(request: Request, id: str, token: AccessTokenPayload = Depends(authorize_admin)):
    db = get_database(request)
    uuid = UUID(id)

    member = db.members.find_one({'id': uuid})
    if not member:
        raise HTTPException(404, "User not found")

    if member["role"] == Role.admin:
        raise HTTPException(400, "User already admin")
    
    results = db.members.find_one_and_update({'id': member["id"]}, {'$set': {'role': f'{Role.admin}'}})

    if not results:
        raise HTTPException(500)
    return Response(status_code=201)
    
@router.post('/')
def create_admin_user(request: Request, newAdmin: MemberInput, token: AccessTokenPayload = Depends(authorize_admin)):
    db = get_database(request)
    exists = db.members.find_one({'email': newAdmin.email.lower()})
    if exists:
        raise HTTPException(409, 'E-mail is already in use.')
    if not validate_password(newAdmin.password):
        raise HTTPException(400, passwordError)
    pwd = generate_password_hash(newAdmin.password)

    uid = uuid4()
    additionalFields = {
        'id': uid,
        'email': newAdmin.email.lower(),  # Lowercase e-mail
        'password': pwd,
        'role': f'{Role.admin}',
        'status': f'{Status.inactive}',
    }

    admin = newAdmin.dict()
    admin.update(additionalFields)
    # Create user object
    db.members.insert_one(admin)

    # Create confirmation code
    confirmationCode = uuid4().hex
    db.confirmations.insert_one(
        {"confirmationCode": confirmationCode, 'user_id': admin['id']}
    )
    return Response(status_code=201)

@router.put('/member/{id}', dependencies=[Depends(validate_uuid)])
def update_member(request: Request, id: str, memberData: AdminMemberUpdate, token: AccessTokenPayload = Depends(authorize_admin)):
    db = get_database(request)

    values = memberData.dict()
    updateInfo = {}
    for key in values:
        if values[key]:
            updateInfo[key] = values[key]

    if not updateInfo:
        return HTTPException(400)

    member = db.members.find_one({'id': UUID(id)})

    if not member:
        raise HTTPException(404, "User not found")

    if member["role"] == Role.admin:
        raise HTTPException(403, "Admin cannot update another admin")

    result = db.members.find_one_and_update(
        {'id': member["id"]}, 
        {"$set": updateInfo})

    if not result:
        raise HTTPException(500, "Unexpected error while updating member")

    return Response(status_code=201)

# minimum delete i.e only from the members collection
# TODO add full deletion for a user
@router.delete('/member/{id}', dependencies=[Depends(validate_uuid)])
def delete_member(request: Request, id: str, token: AccessTokenPayload = Depends(authorize_admin)):
    db = get_database(request)
    member = db.members.find_one({'id': UUID(id)})

    if not member:
        raise HTTPException(404, "User not found")

    if member["role"] == Role.admin:
        raise HTTPException(403, "Admin cannot delete another admin")

    result = db.members.find_one_and_delete({'id': member["id"]})

    if not result:
        raise HTTPException(500)

    return Response(status_code=200)

@router.post('/assign-penalty-to-member/{id}', dependencies=[Depends(validate_uuid)])
def set_member_penalty(request: Request, id:str, penalty_input: PenaltyInput, token: AccessTokenPayload = Depends(authorize_admin)):
    db = get_database(request)
    member = db.members.find_one({'id': UUID(id)})

    if not member:
        raise HTTPException(404, "Could not find member associated with id")

    result = db.members.find_one_and_update(
        {'id': member["id"]},
        {"$set": {'penalty': penalty_input.penalty}}
    )

    if not result:
        raise HTTPException(500, "Unexpected error while updating penalty")

    return Response(status_code=200)
