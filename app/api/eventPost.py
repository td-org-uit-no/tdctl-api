import datetime

from fastapi import APIRouter, Response, Request, HTTPException, Depends
from ..models import Event, EventDB, AccessTokenPayload, Member
from ..auth_helpers import authorize
from ..db import get_database
from ..models import PostData, Post, CommentData
from .utils import get_event_or_404
from uuid import uuid4
from bson import ObjectId

router = APIRouter()
@router.post('/{eid}/post')
def create_event_post(request: Request, eid: str, newPost: PostData, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    
    event = get_event_or_404(db, eid)

    member = db.members.find_one({'id': token.user_id})
    if not member:
        raise HTTPException(404, "User could not be found")

    if len(newPost.message) > 25:
        raise HTTPException(400, "Post to long")

    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    additionalFields = {
        'id': uuid4().hex,
        'author' : token.user_id,
        'created_at' : timestamp,
        'comments': [],
    }

    post = newPost.dict()
    post.update(additionalFields)

    insertedPost = db.events.update({'_id' : event['_id']}, { "$push": { "posts": post } })

    return Response(status_code=200)


@router.get('/{eid}/posts')
def get_event_posts(request: Request, eid:str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)

    event = get_event_or_404(db, eid)
    # return event['posts']
    return [Post.parse_obj(post) for post in event['posts']]

@router.post('/{eid}/comment/{post_id}')
def comment_event_post(request: Request, eid: str, post_id: str, newComment: CommentData, token: AccessTokenPayload=Depends(authorize)):
    db = get_database(request)

    event = get_event_or_404(db, eid)

    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    additionalFields = {
        'author': token.user_id,
        'created_at': timestamp
    }

    comment = newComment.dict()
    comment.update(additionalFields)
    post = db.events.find_one_and_update({"_id": ObjectId(eid), "posts.id": post_id}, 
            {"$push": {"posts.$.comments" : comment}})

    if not post:
        raise HTTPException(400, "invalid post id")

    return Response(status_code=200)
