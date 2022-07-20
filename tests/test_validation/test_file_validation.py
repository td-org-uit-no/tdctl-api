from app.utils.validation import validate_image_file_type

def test_image_validation():
    valid_type = "image/png"
    assert validate_image_file_type(valid_type) == True
    invalid_type = "application/pdf"
    assert validate_image_file_type(invalid_type) == False
    invalid_type = "image/"
    assert validate_image_file_type(invalid_type) == False
