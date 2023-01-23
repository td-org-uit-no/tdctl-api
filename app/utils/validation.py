from fastapi import HTTPException, Request
from uuid import UUID 
import re

passwordError = '''Password is not strong enough: Requires at least: 1 lower case character, 1 upper case character, 1 digit, 1 special character and a length of 8 character'''

def validate_image_file_type(content_type: str) -> bool:
    regexp = r"image/[^\?(.*)]"
    return bool(re.search(regexp, content_type))

def get_file_type(content_type: str):
    regexp = r"image/([^\/]+$)"
    res = re.findall(regexp, "image/jpg")
    if res != None:
        return res[0]
    return res

def validate_password(password:str) -> bool:
    regexp = r"^(?=.*[a-z\æøå])(?=.*[A-Z\ÆØÅ])(?=.*\d)(?=.*[!-/:-@[-`{-~])[A-Z\ÆØÅa-z\æøå\d!-/:-@[-`{-~]{8,}$"
    if not re.findall(regexp, password):
        return False

    return True

def validate_uuid(request: Request, id: str):
    try:
        UUID(str(id))
        return id
    except ValueError:
        raise HTTPException(400, "invalid UUID")
