from fastapi import APIRouter, Request, HTTPException, Depends, Response
from ..db import get_database, get_JobImage_path
from ..models import JobItem, JobItemPayload, AccessTokenPayload, UpdateJob
from app.utils.validation import validate_image_file_type, validate_uuid
from ..auth_helpers import authorize_admin
from fastapi.datastructures import UploadFile
from fastapi.param_functions import File
from pydantic import ValidationError
import os
import shutil
from datetime import datetime
from uuid import UUID, uuid4
from starlette.responses import FileResponse


router = APIRouter()


@router.get('/')
def get_jobs(request: Request):
    db = get_database(request)
    jobs = db.jobs.find()
    return [JobItem.parse_obj(job) for job in jobs]


@router.get('/{id}')
def get_job_by_id(request: Request, id: str):
    db = get_database(request)
    job = db.jobs.find_one({'id': UUID(id)})
    if job == None:
        raise HTTPException(404, "No such job with this id")
    return JobItem.parse_obj(job)


@router.post('/')
def create_job(request: Request, job: JobItemPayload, token: AccessTokenPayload = Depends(authorize_admin)):
    db = get_database(request)
    item = job.dict()
    jid = uuid4()
    item['id'] = jid
    item['published_date'] = datetime.now()
    _job = JobItem.parse_obj(item)
    retval = db.jobs.insert_one(_job.dict())
    if not retval:
        raise HTTPException(500, "Job could not be created")

    return {'id': jid.hex}


@router.delete('/{id}')
def delete_job_by_id(request: Request, id: str, token: AccessTokenPayload = Depends(authorize_admin)):
    db = get_database(request)
    job = db.jobs.find_one_and_delete({'id': UUID(id)})
    if not job:
        raise HTTPException(400, "Job could not be found")
    return {'id': id}


@router.put('/{id}')
def update_job(request: Request, id: str, job: UpdateJob, token: AccessTokenPayload = Depends(authorize_admin)):
    db = get_database(request)
    orig_job = db.jobs.find_one({'id': UUID(id)})

    if not orig_job:
        raise HTTPException(404, "Job could not be found")

    _job = job.dict(exclude_unset=True)
    if len(_job) == 0:
        raise HTTPException(400, "Update values cannot be empty")

    try:
        JobItem.parse_obj({**orig_job, **_job})
    except ValidationError:
        raise HTTPException(
            400, "Cannot remove field as this is required filed for all jobs")

    res = db.jobs.find_one_and_update(
        {'id': UUID(id)},  {'$set': _job})

    if not res:
        raise HTTPException(500, "Error updating job")

    return Response(status_code=200)


@router.get('/{id}/image', dependencies=[Depends(validate_uuid)])
def get_job_picture(request: Request, id: str):
    image_path = get_JobImage_path(request)
    file_name = f"{image_path}/{UUID(id).hex}.png"
    if not os.path.exists(file_name):
        raise HTTPException(404, "picture not found")
    return FileResponse(file_name)


@router.post('/{id}/image', dependencies=[Depends(validate_uuid)])
def upload_job_picture(request: Request, id: str, image: UploadFile = File(...), token: AccessTokenPayload = Depends(authorize_admin)):
    if not validate_image_file_type(image.content_type):
        raise HTTPException(400, "Unsupported file type")

    jobImage_path = get_JobImage_path(request)

    if not os.path.isdir(jobImage_path):
        os.mkdir(jobImage_path)

    picturePath = f"{jobImage_path}/{UUID(id).hex}.png"

    with open(picturePath, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    return Response(status_code=200)
