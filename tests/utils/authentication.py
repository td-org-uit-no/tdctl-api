import re
import random
import pytest
from uuid import uuid4
from tests.conftest import client_login
from tests.users import regular_member

# Both decorators follows the URI structure as FastApi meaning {} indicates that a value should be inserted
# only difference is that the data type has to be defined inside the curly brackets e.g "some_path/{int}/" -> some_path/69

def get_request_method(client, method):
    method = method.lower()
    client_func = {
        "get": client.get,
        "post": client.post,
        "put": client.put,
        "delete": client.delete,
    }

    try:
        return client_func[method]
    except KeyError:
        raise Exception(f"{method} is not a valid method")

def get_type(key):
    # random values to insert when detecting {} in path
    supported_types = {
        "uuid": uuid4().hex,
        "int": random.randint(0, 100)
    }
    try:
        return supported_types[key.lower()]
    except KeyError:
        raise Exception(f"ERROR(Got unsupported type in path): got {key}")

# parse path and checks for {type} which indicates that a path needs an arbitrary value inserted instead of {type}
def parse_path(path):
    regexp = r'\{(.*?)\}'
    res = re.findall(regexp, path)
    for r in res:
        val = get_type(r)
        path = re.sub(regexp, f'{val}', path, count=1)
    return path

def perform_request(client, path, method, header=None):
    client_func = get_request_method(client, method)
    path = parse_path(path)
    response = client_func(path, headers=header)

    if response.status_code == 307:
        raise Exception(f"got Temporary redirect on :{path}, possible missing trailing slash ")

    response_json = response.json()
    if response.status_code == 405:
        raise Exception(f"{method.upper()} is a invalid method for {path}")

    # improvement detail directly from FASTAPI
    if response.status_code == 404 and response_json['detail'] == 'Not Found':
        raise Exception(f"{path} is not an existing endpoint")

    return response

def validate_authentication(client, path, method) -> bool:
    response = perform_request(client, path, method)

    return bool(response.status_code == 403 or response.status_code == 401)

def validate_admin(client, path, method) -> bool:
    client_login(client, regular_member["email"], regular_member["password"])
    response = perform_request(client, path, method)

    return bool(response.status_code == 403)

# decorator for testing if an endpoint is correctly enforcing authentication correctly
# pass function to decorator to work with pytes client
def authentication_required(path, method):
    def decorator(func):
        def wrapper(client):
            if not validate_authentication(client, path, method):
                raise Exception("Authentication is not enforced for protected endpoint")
            return func(client)
        return wrapper
    return decorator

# decorator for testing if an endpoint is correctly enforcing admin authentication
def admin_required(path, method):
    def decorator(func):
        def wrapper(client):
            if not validate_authentication(client, path, method):
                raise Exception("No authentication for admin resource")
            if not validate_admin(client, path, method):
                raise Exception("Regular user can acess admin resource")
            return func(client)
        return wrapper
    return decorator
