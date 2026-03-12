import re


def not_null(value):
    return value is not None and str(value).strip() != ""


def allocation_range(value):
    if value is None or value == "":
        return False

    try:
        v = float(value)
        return 0 < v <= 100
    except:
        return False


ALLOCATION_QUALITY_RULES = {
    "employee_id": [not_null],
    "project_code": [not_null],
    "allocation_pct": [allocation_range],
    "start_date": [not_null],
    "created_at": [not_null],
}
