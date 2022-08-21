from fastapi import APIRouter, Request, HTTPException, Depends, Response
from uuid import UUID

from app.utils.validation import validate_uuid
from ..db import get_database
from ..models import AccessTokenPayload, AdminMemberUpdate
from ..auth_helpers import authorize, role_required

router = APIRouter()

@router.put('/member/{id}', dependencies=[Depends(validate_uuid)])
def update_member(request: Request, id: str, memberData: AdminMemberUpdate, token: AccessTokenPayload = Depends(authorize)):
    role_required(token, 'admin')
    db = get_database(request)
    id = UUID(id).hex

    values = memberData.dict()
    updateInfo = {}
    for key in values:
        if values[key]:
            updateInfo[key] = values[key]

    if not updateInfo:
        return HTTPException(400)

    user = db.members.find_one({'id': id})

    if not user:
        raise HTTPException(404, "User not found")

    if user["role"] == "admin":
        raise HTTPException(400, "Admin cannot update another admin")

    result = db.members.find_one_and_update(
        {'id': id}, 
        {"$set": updateInfo})

    if not result:
        raise HTTPException(500, "Unexpected error while updating member")

    return Response(status_code=201)
