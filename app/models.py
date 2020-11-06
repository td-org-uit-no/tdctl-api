from typing import Optional
from pydantic import BaseModel, SecretStr, EmailStr, UUID4
from uuid import uuid4
from werkzeug.security import generate_password_hash


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


class ChangePasswordPayload(BaseModel):
    password: str
    newPassword: str
