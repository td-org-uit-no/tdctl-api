from datetime import datetime
from fastapi import APIRouter, HTTPException, Response, Request, Depends
from app.auth_helpers import authorize, authorize_admin, authorize_kiosk_admin
from app.db import get_database
from ..models import AccessTokenPayload, KioskSuggestionPayload, Role

router = APIRouter()


@router.post("/suggestion")
def add_suggestion(
    request: Request,
    newSuggestion: KioskSuggestionPayload,
    token: AccessTokenPayload = Depends(authorize),
):
    db = get_database(request)

    member = db.members.find_one({"id": UUID(token.user_id)})
    if member is None:
        raise HTTPException(500)

    formatted_product = newSuggestion.product.lower().capitalize()

    suggestion = {
        "product": formatted_product,
        "member": member,
        "timestamp": datetime.now(),
    }

    db.kioskSuggestions.insert_one(suggestion)

    return Response(status_code=201)


@router.get("/suggestions")
def get_suggestions(
    request: Request, token: AccessTokenPayload = Depends(authorize_kiosk_admin)
):
    db = get_database(request)

    # Kiosk admin has access to list, but only admin should get member names
    isAdmin = token.role == Role.admin

    # Return all suggestions in collection
    suggestions = db.kioskSuggestions.aggregate([{"$sort": {"date": -1}}])

    # Only return username to admins
    ret = [
        {
            "id": s["id"],
            "product": s["product"],
            "username": s["member"].get("realName", None) if isAdmin else "-",
            "timestamp": s["timestamp"],
        }
        for s in suggestions
    ]

    if len(ret) == 0:
        raise HTTPException(404, "No kiosk suggestions found")

    return ret
