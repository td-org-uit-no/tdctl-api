from typing import Optional
from pydantic import BaseModel, SecretStr, EmailStr, UUID4
from uuid import uuid4
from werkzeug.security import generate_password_hash


'''
# Used as a base model to create member
PartialMember = Model('PartialMember', {
    'realName': fields.String(required=True),
    'email': fields.String(required=True),
    'password': fields.String(required=True),
    'classof': fields.String(required=True),
    'graduated': fields.Boolean(required=True),
    'phone': fields.String
})

# Used to represent the member
Member = Model('Member', {
    '_id': fields.String(required=True),
    'realName': fields.String(required=True),
    'email': fields.String(required=True),
    'classof': fields.String(required=True),
    'graduated': fields.Boolean(required=True),
    'phone': fields.String,
    'role': fields.String,
    'status': fields.String,
})

Login = Model('Login', {
    'email': fields.String(required=True),
    'password': fields.String(required=True)})

RefreshToken = Model('RefreshToken', {'refreshToken': fields.String})

Tokens = RefreshToken.clone('Tokens', {'token': fields.String})

ConfirmationCode = Model('ConfirmationCode', {'confirmationCode': fields.String})
'''


class AccessTokenPayload(BaseModel):
    exp: int
    iat: int
    user_id: str
    role: str
    access_token: bool


class RefreshTokenPayload(BaseModel):
    exp: int
    iat: int
    jti: str
    user_id: str

class MemberInput(BaseModel):
    realName: str
    email: EmailStr
    password: str
    classof: str
    graduated: bool
    phone: Optional[str]


class MemberDB(BaseModel):
    id: UUID4
    realName: str
    email: EmailStr
    password: str
    classof: str
    graduated: bool
    phone: Optional[str]
    role: str
    status: str


class Member(BaseModel):
    id: UUID4
    realName: str
    email: EmailStr
    classof: str
    graduated: bool
    phone: Optional[str]
    role: str
    status: str


class Tokens(BaseModel):
    accessToken: str
    refreshToken: str

class RefreshToken(BaseModel):
    refreshToken: str

class Credentials(BaseModel):
    email: EmailStr
    password: str
