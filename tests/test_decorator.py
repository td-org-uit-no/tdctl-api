from uuid import uuid4
import pytest
from tests.utils.authentication import perform_request, validate_admin, validate_authentication

# testes decorator function which throws exceptions when params are wrong in a decorator
def test_decorator_request_error_handling(client):
    valid_path = f"api/admin/give-admin-privileges/{uuid4().hex}"
    invalid_method = "yikes"
    # check for invalid method
    with pytest.raises(Exception):
        perform_request(client, valid_path, invalid_method)
    # check for 405, unsupported method
    with pytest.raises(Exception):
        perform_request(client, valid_path, "delete")
    # has to be in separate with or the test will pass when only one is throwing an exception 
    with pytest.raises(Exception):
        perform_request(client, "test", "post")

def test_admin_decorator(client):
    no_auth_path = "api/event/upcoming"
    auth_path = "api/member/"
    admin_path = "api/admin/"
    valid_method = "get"

    assert validate_admin(client, no_auth_path, valid_method) == False
    assert validate_admin(client, auth_path, valid_method) == False
    assert validate_admin(client, admin_path, "post") == True

def test_auth_decorator(client):
    no_auth_path = "api/event/upcoming"
    auth_path = "api/member/"
    valid_method = "get"

    assert validate_authentication(client, no_auth_path, valid_method) == False
    assert validate_authentication(client, auth_path, valid_method) == True
