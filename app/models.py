from typing import Optional, List
from pydantic import BaseModel, EmailStr, UUID4
from datetime import datetime

from pydantic.fields import Field


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
    # penalty for late cancellation 0-no penalty 1-warning and 2-lower priority
    penalty: int


class Member(BaseModel):
    id: UUID4
    realName: str
    email: EmailStr
    classof: str
    graduated: bool
    phone: Optional[str]
    role: str
    status: str


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
    penalty: int


class EventInput(BaseModel):
    title: str
    date: datetime
    address: str
    price: int
    description: str  # short info about the event
    # duration in hours
    duration: Optional[int]
    # more detailed practical information
    public: bool
    bindingRegistration: bool
    transportation: bool
    food: bool
    extraInformation: Optional[str]
    maxParticipants: Optional[int]
    romNumber: Optional[str]
    building: Optional[str]
    picturePath: Optional[str]
    # time before event starting
    registrationOpeningDate: Optional[datetime]


class Event(EventInput):
    eid: UUID4
    # The TD member responsible for the event
    host: EmailStr
    # Collects all user penalties registered, ensuring only one penalty is given per event
    registeredPenalties: List[UUID4]


class EventUpdate(BaseModel):
    title: Optional[str]
    date: Optional[datetime]
    address: Optional[str]
    description: Optional[str]
    maxParticipants: Optional[int]
    public: Optional[bool]
    price: Optional[int]
    transportation: Optional[bool]
    food: Optional[bool]
    registrationOpeningDate: Optional[datetime]


class EventDB(Event):
    participants: List[Participant]


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


class ForgotPasswordPayload(BaseModel):
    token: str
    newPassword: str


class JoinEventPayload(BaseModel):
    food: Optional[bool]
    transportation: Optional[bool]
    dietaryRestrictions: Optional[str]


class PenaltyInput(BaseModel):
    penalty: int = Field(
        ge=0, description="Penalty must be larger or equal to 0")


class JobItemPayload(BaseModel):
    company: str
    title: str
    type: str
    img: str
    tags: List[str]
    description_preview: str
    description: str
    start_date: datetime
    published_date: datetime
    location: str
    link: str
    due_date: datetime


class JobItem(JobItemPayload):
    id: UUID4
