from fastapi import APIRouter, Response, Request, HTTPException, Depends
from pydantic.networks import EmailStr
from werkzeug.security import generate_password_hash
from pymongo import ReturnDocument
from typing import List
from uuid import uuid4, UUID
from datetime import datetime
from .mail import send_mail

from app.utils.validation import validate_uuid

from ..models import Member, MemberDB, MemberInput, MemberUpdate, AccessTokenPayload, MailPayload, ForgotPasswordPayload, Role, Status
from ..auth_helpers import authorize, authorize_admin, role_required
from ..db import get_database
from ..utils import validate_password, passwordError

router = APIRouter()

@router.post('/')
def create_new_member(request: Request, newMember: MemberInput):
    db = get_database(request)
    exists = db.members.find_one({'email': newMember.email.lower()})
    if exists:
        raise HTTPException(409, 'E-mail is already in use.')
    if not validate_password(newMember.password):
        raise HTTPException(400, passwordError)
    pwd = generate_password_hash(newMember.password)
    uid = uuid4()
    additionalFields = {
        'id': uid,
        'email': newMember.email.lower(),  # Lowercase e-mail
        'password': pwd,
        'role': f'{Role.unconfirmed}',
        'status': f'{Status.inactive}',
        'penalty': 0
    }

    member = newMember.dict()
    member.update(additionalFields)
    # Create user object
    db.members.insert_one(member)

    # Create confirmation code
    confirmationCode = uuid4()
    db.confirmations.insert_one(
        {"confirmationCode": confirmationCode, 'user_id': member['id']}
    )
    
    if request.app.config.ENV == 'production':
        # Send email to new user for verification
        with open("./app/assets/mails/member_confirmation.txt", 'r') as mail_content:
            confirmation_email = MailPayload(
                to = [newMember.email],
                subject = "Confirmation email",
                content = mail_content.read().replace("$LINK$", f"{request.app.config.FRONTEND_URL}/confirmation/{confirmationCode.hex}")
            )
        send_mail(confirmation_email)

@router.get('/')
def get_member_associated_with_token(request: Request, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    currentMember = db.members.find_one({'id': UUID(token.user_id)})
    if not currentMember:
        raise HTTPException(404, "User could not be found")
    return Member.parse_obj(currentMember)


@router.get('/{id}', response_model=Member, responses={404: {"model": None}}, dependencies=[Depends(validate_uuid)])
def get_member_by_id(request: Request, id: str, token: dict = Depends(authorize)):
    '''Returns a user object associated with id passed in'''
    db = get_database(request)
    member = db.members.find_one({'id': UUID(id)})
    if not member:
        raise HTTPException(404, 'Member not found')
    return Member.parse_obj(member)

@router.get('/email/{email}')
def get_member_by_email(request: Request, email: EmailStr, token: AccessTokenPayload = Depends(authorize_admin)):
    db = get_database(request)
    member = db.members.find_one({'email': email.lower()})
    if not member:
        raise HTTPException(404, 'Member not found')
    return {'id': member['id'].hex}

@router.get("s/", response_model=List[Member])
def get_all_members(request: Request, token: AccessTokenPayload = Depends(authorize_admin)):
    '''List all members objects'''
    db = get_database(request)
    return [Member.parse_obj(m) for m in db.members.find()]

@router.post('/activate')
def change_status(request: Request, token: AccessTokenPayload = Depends(authorize)):
    '''Sets the member status to active'''
    db = get_database(request)
    member = db.members.find_one({'id': UUID(token.user_id)})
    if not member:
        raise HTTPException(404, 'Member not found')

    member = MemberDB.parse_obj(member)
    if member.status == Status.active:
        raise HTTPException(400, "member already activated")

    result = db.members.find_one_and_update(
        {'id': member.id},
        {"$set": {'status': f'{Status.active}'}}
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
        {'confirmationCode': UUID(code)})
    if not validated:
        raise NotMatchedError

    user = db.members.find_one_and_update(
        {'id': validated['user_id']},
        {"$set":
         {'role': f'{Role.member}',
          'status': f'{Status.active}'}
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

    if member['role'] != Role.unconfirmed:
        # Member associated with the email is already activated
        raise MemberAlreadyConfirmedError


    newConfirmationCode = uuid4()

    result = db.confirmations.find_one_and_update(
            {'user_id': member['id']}, 
            {"$set": 
                { "confirmationCode": newConfirmationCode }
            })

    if not result:
        # An error occured when updating the user with the confirmation code
        raise HTTPException(500)

    if request.app.config.ENV == 'production':
        # Send email to new user for verification
        with open("./app/assets/mails/member_confirmation.txt", 'r') as mail_content:
            confirmation_email = MailPayload(
                to = [email],
                subject = "Confirmation email",
                content = mail_content.read().replace("$LINK$", f"{request.app.config.FRONTEND_URL}/confirmation/{newConfirmationCode.hex}")
            )
        send_mail(confirmation_email)
    return Response(status_code=200)

@router.post('/reset-password/code/{email}')
def generate_new_reset_password_code(request: Request, email: str):
    """
    Generates a code that is mailed to the members registered email.
    This code can then be used to verify the member in stead of a password.
    """
    NonExistentMemberError = HTTPException(
        404, "A member with the given e-mail address does not exist"
    )

    db = get_database(request)
    member = db.members.find_one({'email': email})

    if not member:
        # Member assoiciated with the email was not found
        raise NonExistentMemberError
    db.passwordResets.find_one_and_delete({'user_id': member['id']})

    newCode = uuid4()
    result = db.passwordResets.insert_one(
        {"createdAt": datetime.utcnow(),"code": newCode, 'user_id': member['id']}
    )
    if not result:
        # An error occured when updating the user with the confirmation code
        raise HTTPException(500)

    if request.app.config.ENV == 'production':
        with open("./app/assets/mails/restore_password.txt", 'r') as mail_content:
            resetPasswordEmail = MailPayload(
                to = [email],
                subject = "TD Website reset password",
                content = mail_content.read().replace("$LINK$", f"{request.app.config.FRONTEND_URL}/reset-password/{newCode.hex}")
            )
        send_mail(resetPasswordEmail)

    return Response(status_code=200)


@router.post('/reset-password/')
def reset_password(request: Request, newPasswordPayload : ForgotPasswordPayload ):
    """
    Resets password of member based on token from email.
    """
    NotMatchedError = HTTPException(
        404, "Reset password token could not be matched")

    if not validate_password(newPasswordPayload.newPassword):
        raise HTTPException(400, passwordError)

    db = get_database(request)

    # Remove reset password token from database
    passwordResetToken = db.passwordResets.find_one_and_delete(
        {'code': UUID(newPasswordPayload.token)})
    if not passwordResetToken:
        raise NotMatchedError

    # Generate hash of new password
    pwd = generate_password_hash(newPasswordPayload.newPassword)

    # Update member with new hash
    user = db.members.find_one_and_update(
        {'id': passwordResetToken['user_id']},
        {"$set":
         {'password': pwd}
         },
        return_document=ReturnDocument.AFTER)
    if not user:
        # User associated with reset password token does not exist.
        raise NotMatchedError

    return Response(status_code=200)

@router.put('/')
def update_member(request: Request, memberData: MemberUpdate, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    member = db.members.find_one({'id': UUID(token.user_id)})
    if not member:
        raise HTTPException(404, "User not found")

    values = memberData.dict()
    updateInfo = {}
    for key in values:
        if values[key]:
            updateInfo[key] = values[key]

    if not updateInfo:
        return HTTPException(400)

    result = db.members.find_one_and_update(
        {'id': member["id"]},
        {"$set": updateInfo})

    if not result:
        raise HTTPException(500)

    return Response(status_code=201)

