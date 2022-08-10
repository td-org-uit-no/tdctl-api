from app.utils.validation import validate_password

def test_validate_password():
    too_few_letters = "test123*"
    assert validate_password(too_few_letters) == False

    missingUpperCase = "*test1234"
    assert validate_password(missingUpperCase) == False

    missingLowerCase = "*TEST1234"
    assert validate_password(missingLowerCase) == False

    noDigits = "*testeR"
    assert validate_password(noDigits) == False

    noSpecialChar = "Tester1234"
    assert validate_password(noSpecialChar) == False

    valid_pwd = "*validPwd1234"
    assert validate_password(valid_pwd) == True
