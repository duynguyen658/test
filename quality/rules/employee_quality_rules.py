import re


def not_null(value):
    return value is not None and str(value).strip() != ""


def valid_email(value):
    if value is None:
        return False
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, value))


def salary_positive(value):
    if value is None or value == "":
        return True
    try:
        return float(value) >= 0
    except:
        return False


def valid_status(value):
    allowed = {"active", "on_leave", "terminated"}
    if value is None:
        return True
    return str(value).lower() in allowed


def valid_phone(value):
    if value is None:
        return False
    pattern = r"^\+?[0-9\-\.\s]{7,20}$"
    return bool(re.match(pattern, value))


EMPLOYEE_QUALITY_RULES = {
    "employee_id": [not_null],
    "full_name": [not_null],
    "email": [valid_email],
    "phone": [valid_phone],
    "salary": [salary_positive],
    "status": [valid_status],
}
