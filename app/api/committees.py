import re
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query

from app.auth_helpers import authorize, authorize_admin
from app.db import get_database
from app.models import (
    AccessTokenPayload,
    Committee,
    CommitteeDB,
    CommitteeInput,
    CommitteeApplicationInput,
    CommitteeMemberInput,
    CommitteeMemberListItem,
    CommitteeUpdate,
    Status,
)
from app.utils.validation import validate_uuid


router = APIRouter()
logger = logging.getLogger(__name__)


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def committee_member_count(db, committee_id: UUID) -> int:
    return db.committeeMembers.count_documents({
        "committeeId": committee_id,
        "active": True,
    })


def get_committee_or_404(db, id: str):
    c = db.committees.find_one({"id": UUID(id)})
    if not c:
        raise HTTPException(404, "Committee not found")
    return c


@router.get("/")
def list_committees(
    request: Request,
    status: Optional[Status] = None,
    hasOpenSpots: Optional[bool] = None,
    q: Optional[str] = None,
    sort: Optional[str] = Query("name", description="Sort by field, prefix with - for desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    db = get_database(request)

    query = {}
    if status is not None:
        query["status"] = f"{status}"
    if hasOpenSpots is not None:
        query["hasOpenSpots"] = hasOpenSpots
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]

    sort_field = "name"
    sort_dir = 1
    if sort:
        if sort.startswith("-"):
            sort_field = sort[1:]
            sort_dir = -1
        else:
            sort_field = sort
    if sort_field not in ["name", "createdAt", "updatedAt"]:
        sort_field = "name"

    total = db.committees.count_documents(query)
    cur = (
        db.committees.find(query)
        .sort(sort_field, sort_dir)
        .skip((page - 1) * limit)
        .limit(limit)
    )

    items = []
    for c in cur:
        count = committee_member_count(db, c["id"])
        payload = Committee.model_validate({**c, "memberCount": count})
        items.append(payload)

    return {
        "items": [i.model_dump() for i in items],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/{id}", dependencies=[Depends(validate_uuid)])
def get_committee(request: Request, id: str):
    db = get_database(request)
    c = get_committee_or_404(db, id)
    count = committee_member_count(db, c["id"])
    return Committee.model_validate({**c, "memberCount": count})


@router.post("/")
def create_committee(
    request: Request,
    payload: CommitteeInput,
    token: AccessTokenPayload = Depends(authorize_admin),
):
    db = get_database(request)

    # Derive slug if not provided
    slug = payload.slug or slugify(payload.name)
    # Ensure uniqueness
    exists = db.committees.find_one({"slug": slug})
    if exists:
        raise HTTPException(409, "Slug already in use")

    # CreatedBy is email; fetch current user email
    creator = db.members.find_one({"id": UUID(token.user_id)})
    if not creator:
        raise HTTPException(400, "Creator not found")

    now = datetime.utcnow()
    doc = CommitteeDB(
        id=uuid4(),
        name=payload.name,
        slug=slug,
        description=payload.description,
        status=payload.status,
        hasOpenSpots=payload.hasOpenSpots,
        createdAt=now,
        updatedAt=now,
        createdBy=creator["email"],
        email=payload.email,
    )

    db.committees.insert_one(doc.model_dump())
    return Response(status_code=201)


@router.put("/{id}", dependencies=[Depends(validate_uuid)])
def update_committee(
    request: Request,
    id: str,
    payload: CommitteeUpdate,
    token: AccessTokenPayload = Depends(authorize_admin),
):
    db = get_database(request)
    c = get_committee_or_404(db, id)

    values = payload.model_dump(exclude_unset=True)
    if len(values) == 0:
        raise HTTPException(400, "Update values cannot be empty")

    if "slug" in values and values["slug"]:
        # Normalize and ensure unique
        new_slug = slugify(values["slug"]) if values["slug"] else slugify(c["name"])
        if new_slug != c["slug"]:
            exists = db.committees.find_one({"slug": new_slug})
            if exists:
                raise HTTPException(409, "Slug already in use")
            values["slug"] = new_slug

    values["updatedAt"] = datetime.utcnow()

    res = db.committees.find_one_and_update({"id": c["id"]}, {"$set": values})
    if not res:
        raise HTTPException(500, "Unexpected error when updating committee")
    return Response(status_code=200)


@router.post("/{id}/apply", dependencies=[Depends(validate_uuid)])
def apply_for_committee(
    request: Request,
    id: str,
    payload: CommitteeApplicationInput,
    token: AccessTokenPayload = Depends(authorize),
):
    """Allow a logged-in member to apply to a committee.

    Sends an email to the committee's associated email with applicant details.
    """
    db = get_database(request)
    c = get_committee_or_404(db, id)

    if not c.get("hasOpenSpots", False):
        raise HTTPException(400, "Committee is not open for new members")

    committee_email = c.get("email")
    if not committee_email:
        raise HTTPException(400, "Committee does not have an associated email")

    member = db.members.find_one({"id": UUID(token.user_id)})
    if not member:
        raise HTTPException(404, "User could not be found")

    # Build email content
    message = payload.message or ""
    if message and len(message) > 2000:
        raise HTTPException(400, "Message is too long")

    content_lines = [
        f"New application to {c['name']} committee",
        "",
        f"Applicant: {member['realName']}",
        f"Email: {member['email']}",
    ]
    if message:
        content_lines.extend(["", "Content:", message])
    content = "\n".join(content_lines)

    # Only send mail in production (keeps parity with reset password/confirm flows)
    if request.app.config.ENV == "production":
        from app.api.mail import send_mail
        from app.models import MailPayload

        mail = MailPayload(
            to=[committee_email],
            subject=f"New committee application: {c['name']}",
            content=content,
        )
        send_mail(mail)

    return Response(status_code=202)


@router.delete("/{id}", dependencies=[Depends(validate_uuid)])
def delete_committee(
    request: Request, id: str, token: AccessTokenPayload = Depends(authorize_admin)
):
    db = get_database(request)
    c = get_committee_or_404(db, id)
    # Delete memberships associated (current and historical)
    db.committeeMembers.delete_many({"committeeId": c["id"]})
    res = db.committees.find_one_and_delete({"id": c["id"]})
    if not res:
        raise HTTPException(500, "Unexpected error when deleting committee")
    return Response(status_code=200)


@router.post("/{id}/members", dependencies=[Depends(validate_uuid)])
def add_committee_member(
    request: Request,
    id: str,
    body: CommitteeMemberInput,
    token: AccessTokenPayload = Depends(authorize_admin),
):
    db = get_database(request)
    c = get_committee_or_404(db, id)

    if not c["hasOpenSpots"]:
        raise HTTPException(400, "Committee is not open for new members")

    member = db.members.find_one({"id": UUID(str(body.userId))})
    if not member:
        raise HTTPException(404, "Member not found")

    creator = db.members.find_one({"id": UUID(token.user_id)})
    if not creator:
        raise HTTPException(400, "Creator not found")

    doc = {
        "committeeId": c["id"],
        "userId": member["id"],
        "addedBy": creator["email"],
        "addedAt": datetime.utcnow(),
        "active": True,
        "leftAt": None,
        "leftBy": None,
    }

    # Try insert; if exists, try re-activate if inactive
    try:
        db.committeeMembers.insert_one(doc)
    except Exception:
        # Check if there is an existing inactive record
        existing = db.committeeMembers.find_one(
            {"committeeId": c["id"], "userId": member["id"]}
        )
        if existing and existing.get("active") is False:
            db.committeeMembers.find_one_and_update(
                {"committeeId": c["id"], "userId": member["id"]},
                {"$set": {"active": True, "leftAt": None, "leftBy": None}},
            )
        else:
            raise HTTPException(409, "Member already assigned to committee")

    return Response(status_code=201)


@router.delete("/{id}/members/{userId}", dependencies=[Depends(validate_uuid)])
def remove_committee_member(
    request: Request,
    id: str,
    userId: str,
    token: AccessTokenPayload = Depends(authorize_admin),
):
    db = get_database(request)
    c = get_committee_or_404(db, id)
    admin = db.members.find_one({"id": UUID(token.user_id)})

    res = db.committeeMembers.find_one_and_update(
        {"committeeId": c["id"], "userId": UUID(userId), "active": True},
        {"$set": {"active": False, "leftAt": datetime.utcnow(), "leftBy": admin["email"]}},
    )
    if not res:
        raise HTTPException(404, "Active membership not found")
    return Response(status_code=200)


@router.get("/{id}/members", dependencies=[Depends(validate_uuid)])
def list_committee_members(
    request: Request,
    id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    token: AccessTokenPayload = Depends(authorize_admin),
):
    db = get_database(request)
    c = get_committee_or_404(db, id)

    match = {"committeeId": c["id"], "active": True}
    total = db.committeeMembers.count_documents(match)

    pipeline = [
        {"$match": match},
        {"$lookup": {"from": "members", "localField": "userId", "foreignField": "id", "as": "user"}},
        {"$unwind": "$user"},
        {"$sort": {"user.realName": 1}},
        {"$skip": (page - 1) * limit},
        {"$limit": limit},
        {"$project": {
            "_id": 0,
            "id": "$user.id",
            "realName": "$user.realName",
            "email": "$user.email",
            "classOf": "$user.classof",
            "phone": "$user.phone",
            "role": "$user.role",
        }},
    ]

    rows = list(db.committeeMembers.aggregate(pipeline))
    items = [CommitteeMemberListItem.model_validate(r) for r in rows]
    return {
        "items": [i.model_dump() for i in items],
        "total": total,
        "page": page,
        "limit": limit,
    }
