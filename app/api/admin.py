from fastapi import APIRouter, Request, HTTPException, Depends, Response
from uuid import UUID
from ..db import get_database
from ..models import AccessTokenPayload, AdminMemberUpdate
from ..auth_helpers import authorize, role_required

router = APIRouter()

@router.put('/member/{id}')
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

    result = db.members.find_one_and_update(
        {'id': id, 'role': {'$ne': 'admin'}},
        {"$set": updateInfo})

    if not result:
        raise HTTPException(404, "User not found")

    return Response(status_code=201)
