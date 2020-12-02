import re

passwordError = '''Password is not strong enough: Requires at least: 1 lower case character, 1 upper case character, 1 digit, 1 special character and a length of 8 character'''

def validate_password(password:str) -> bool:
    req = "^(?=.*[a-z\æøå])(?=.*[A-Z\ÆØÅ])(?=.*\d)(?=.*[@$!%*?&])[A-Z\ÆØÅa-z\æøå\d@$!%*?&]{8,}$"
    if not re.findall(req, password):
        return False

    return True

