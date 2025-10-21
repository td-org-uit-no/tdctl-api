from enum import Enum
from typing import Dict, Literal, Optional, List
from pydantic import BaseModel, EmailStr, UUID4, create_model, field_validator
from datetime import datetime, date

from pydantic.fields import Field


class Status(str, Enum):
    active = "active"
    inactive = "inactive"

    def __str__(self):
        return self.value


class Role(str, Enum):
    admin = "admin"
    member = "member"
    unconfirmed = "unconfirmed"
    kiosk_admin = "kiosk_admin"

    def __str__(self):
        return self.value


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
    role: Role
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
    phone: Optional[str] = None


class AdminMemberUpdate(BaseModel):
    realName: Optional[str] = None
    role: Optional[Role] = None
    status: Optional[Status] = None
    email: Optional[EmailStr] = None
    classof: Optional[str] = None
    phone: Optional[str] = None
    penalty: Optional[int] = None


class MemberUpdate(BaseModel):
    realName: Optional[str] = None
    email: Optional[EmailStr] = None
    classof: Optional[str] = None
    phone: Optional[str] = None


class MemberDB(BaseModel, use_enum_values=True):
    id: UUID4
    realName: str
    email: EmailStr
    password: str
    classof: str
    graduated: bool
    phone: Optional[str] = None
    role: Role
    status: Status
    # penalty for late cancellation 0-no penalty 1-warning and 2-lower priority
    penalty: int

    # sets role to unconfirmed if role is something else than the predefined roles
    # mode='before' makes this validation run before pydantic's model validator
    @field_validator("role", mode="before")
    @classmethod
    def role_validator(cls, v):
        if v not in Role.__members__:
            return Role.unconfirmed
        return v

    # sets role to inactive if status is something else than the predefined status
    @field_validator("status", mode="before")
    @classmethod
    def status_validator(cls, v):
        if v not in Status.__members__:
            return Status.inactive
        return v


class Member(BaseModel):
    id: UUID4
    realName: str
    email: EmailStr
    classof: str
    graduated: bool
    phone: Optional[str] = None
    role: Role
    status: Status
    penalty: int


class Participant(BaseModel):
    id: UUID4
    realName: str
    email: EmailStr
    classof: str
    phone: Optional[str] = None
    role: Role
    food: bool
    transportation: bool
    dietaryRestrictions: str
    gdprConsent: Optional[bool] = None
    submitDate: datetime
    penalty: int
    # indicate if participant has recieved an confirmation mail
    confirmed: Optional[bool] = None
    attended: Optional[bool] = None


class ParticipantPosUpdate(BaseModel):
    updateList: List[
        create_model("ParticipantPosUpdate", id=(UUID4, ...), pos=(int, ...))
    ]


class EventInput(BaseModel):
    title: str
    date: datetime
    address: str
    price: int
    description: str  # short info about the event
    # duration in hours
    duration: Optional[int] = None
    # more detailed practical information
    public: bool
    bindingRegistration: bool
    transportation: bool
    food: bool
    extraInformation: Optional[str] = None
    maxParticipants: Optional[int] = None
    romNumber: Optional[str] = None
    building: Optional[str] = None
    picturePath: Optional[str] = None
    # time before event starting
    registrationOpeningDate: Optional[datetime] = None
    confirmed: Optional[bool] = None


class EventUserView(EventInput):
    eid: UUID4


class Event(EventUserView):
    # The TD member responsible for the event
    host: EmailStr
    # Collects all user penalties registered, ensuring only one penalty is given per event
    registeredPenalties: List[UUID4]
    # Register id
    register_id: Optional[UUID4] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[datetime] = None
    address: Optional[str] = None
    description: Optional[str] = None
    maxParticipants: Optional[int] = None
    public: Optional[bool] = None
    price: Optional[int] = None
    transportation: Optional[bool] = None
    food: Optional[bool] = None
    registrationOpeningDate: Optional[datetime] = None
    confirmed: Optional[bool] = None


class EventConfirmMessage(BaseModel):
    msg: Optional[str] = None


class EventMailMessage(BaseModel):
    subject: str
    msg: str
    confirmedOnly: Optional[bool] = False


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
    food: Optional[bool] = None
    transportation: Optional[bool] = None
    dietaryRestrictions: Optional[str] = None
    gdprConsent: Optional[bool] = None


class PenaltyInput(BaseModel):
    penalty: int = Field(ge=0, description="Penalty must be larger or equal to 0")


class SetAttendancePayload(BaseModel):
    member_id: Optional[str] = None
    attendance: bool


class JobItemPayload(BaseModel):
    company: str
    title: str
    type: str
    tags: List[str]
    description_preview: str
    description: str
    published_date: datetime
    location: str
    link: str
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None


class UpdateJob(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[List[str]] = None
    description_preview: Optional[str] = None
    description: Optional[str] = None
    published_date: Optional[datetime] = None
    location: Optional[str] = None
    link: Optional[str] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None


class JobItem(JobItemPayload):
    id: UUID4


class UniqueVisitsStructure(BaseModel):
    entry_date: date
    # bloom filter object
    bloom_filter: bytes
    timestamps: List[date]


class PageVisitsStructure(BaseModel):
    # tracks
    url_dict: Dict[str, int]


class PageVisitStamp(BaseModel):
    pass


class PageVisit(BaseModel):
    page: str


class PageVisits(PageVisit):
    start: date
    end: date


class Stats(BaseModel):
    date: date


class KioskSuggestionPayload(BaseModel):
    product: str


class KioskSuggestion(KioskSuggestionPayload):
    id: str
    member: Member
    timestamp: datetime
