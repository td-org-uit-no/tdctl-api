from typing import Optional, List
from pydantic import BaseModel, SecretStr, EmailStr, UUID4, Field
from uuid import uuid4
from werkzeug.security import generate_password_hash
from datetime import datetime
from bson import ObjectId


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

class MemberUpdate(BaseModel):
    realName: Optional[str]
    email: Optional[EmailStr]
    classof: Optional[str]
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

class CommentData(BaseModel):
    comment: str

class Comment(CommentData):
    author: UUID4
    created_at: datetime

class PostData(BaseModel):
    message: str

class Post(PostData):
    id: UUID4
    author: UUID4
    created_at: datetime
    comments: List[Comment]

class Event(BaseModel):
    title: str
    description: Optional[str]
    date: datetime
    address: str

class EventDB(Event):
    participants: List[Member]
    posts: List[Post]

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
