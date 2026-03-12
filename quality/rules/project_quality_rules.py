import re


def not_null(value):
    return value is not None and str(value).strip() != ""


def valid_status(value):
    allowed = {"active", "completed", "on_hold", "cancelled"}
    if value is None:
        return True
    return str(value).lower() in allowed


PROJECT_QUALITY_RULES = {
    "project_code": [not_null],
    "project_name": [not_null],
    "start_date": [not_null],
    "budget": [not_null],
    "department_owner": [not_null],
    "description": [not_null],
    "status": [valid_status],
}
