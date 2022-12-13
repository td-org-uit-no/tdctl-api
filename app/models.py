from typing import Optional, List
from pydantic import BaseModel, EmailStr, UUID4
from datetime import datetime


class MailPayload(BaseModel):
    """
    Mail model used to define emails sent from server
    subject: str
        - Subject of email.
    content: str
        - Content of email.
    to: List[EmailStr]
        - List of emails to send email to.
    sent_by: str
        - Email that is to be marked as sender.
    """
    subject: str
    content: str
    to: List[EmailStr]
    sent_by: str = "no-reply@td-uit.no"


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


class AdminMemberUpdate(BaseModel):
    realName: Optional[str]
    role: Optional[str]
    status: Optional[str]
    email: Optional[EmailStr]
    classof: Optional[str]
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


class EventInput(BaseModel):
    title: str
    date: datetime
    address: str
    price: int
    description: str  # short info about the event
    duration: Optional[int]  # in hours
    extraInformation: Optional[str]  # more detailed practical information
    maxParticipants: Optional[int]
    romNumber: Optional[str]
    building: Optional[str]
    picturePath: Optional[str]
    transportation: bool
    food: bool
    active: bool


class Event(EventInput):
    eid: UUID4


class EventUpdate(BaseModel):
    title: Optional[str]
    date: Optional[datetime]
    address: Optional[str]
    description: Optional[str]
    maxParticipants: Optional[int]
    active: Optional[bool]
    price: Optional[int]


class Participant(BaseModel):
    id: UUID4
    realName: str
    email: EmailStr
    classof: str
    phone: Optional[str]
    role: str
    food: bool
    transportation: bool
    dietaryRestrictions: str
    submitDate: datetime


class EventDB(Event):
    participants: List[Participant]
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


class JoinEventPayload(BaseModel):
    food: Optional[bool]
    transportation: Optional[bool]
    dietaryRestrictions: Optional[str]
