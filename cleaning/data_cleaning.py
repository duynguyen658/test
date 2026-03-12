import re
from datetime import datetime
from typing import Any, Dict, List

# =========================
# Basic cleaning helpers
# =========================


def clean_string(value: Any) -> Any:

    if value is None:
        return None

    if isinstance(value, str):

        value = value.strip()

        if value == "":
            return None

        return value

    return value


def clean_email(value: Any):

    value = clean_string(value)

    if value is None:
        return None

    return value.lower()


def clean_phone(value: Any):

    value = clean_string(value)

    if value is None:
        return None

    digits = re.sub(r"\D", "", value)

    if digits == "":
        return None

    return digits


def clean_number(value: Any):

    if value is None or value == "":
        return None

    try:
        return float(value)
    except Exception:
        return None


def clean_date(value: Any):

    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        return value.date()

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]

    for fmt in formats:
        try:
            # Hỗ trợ cả chuỗi có time (vd "2023-01-10 9:00:00") bằng cách chỉ parse 10 ký tự đầu
            s = str(value).strip()
            if not s:
                return None
            return datetime.strptime(s[:10], fmt).date()
        except Exception:
            pass

    return None


# =========================
# Employees cleaning
# =========================


def clean_employees(rows: List[Dict]):

    cleaned = []

    for row in rows:

        r = {
            "employee_id": clean_string(row.get("employee_id")),
            "full_name": clean_string(row.get("full_name")),
            "email": clean_email(row.get("email")),
            "phone": clean_phone(row.get("phone")),
            "department": clean_string(row.get("department")),
            "position": clean_string(row.get("position")),
            "hire_date": clean_date(row.get("hire_date")),
            "termination_date": clean_date(row.get("termination_date")),
            "status": clean_string(row.get("status")),
            "salary": clean_number(row.get("salary")),
            "manager_id": clean_string(row.get("manager_id")),
        }

        cleaned.append(r)

    return cleaned


# =========================
# Projects cleaning
# =========================


def clean_projects(rows: List[Dict]):

    cleaned = []

    for row in rows:

        r = {
            "project_code": clean_string(row.get("project_code")),
            "project_name": clean_string(row.get("project_name")),
            "client": clean_string(row.get("client")),
            "status": clean_string(row.get("status")),
            "start_date": clean_date(row.get("start_date")),
            "end_date": clean_date(row.get("end_date")),
            "budget": clean_number(row.get("budget")),
            "department_owner": clean_string(row.get("department_owner")),
            "description": clean_string(row.get("description")),
        }

        cleaned.append(r)

    return cleaned


# =========================
# Allocations cleaning
# =========================


def clean_allocations(rows: List[Dict], employees, projects):

    employee_ids = {e["employee_id"] for e in employees}
    project_codes = {p["project_code"] for p in projects}

    cleaned = []

    for row in rows:

        employee_id = clean_string(row.get("employee_id"))
        project_code = clean_string(row.get("project_code"))

        # remove invalid FK
        if employee_id not in employee_ids:
            continue

        if project_code not in project_codes:
            continue

        allocation_pct = clean_number(row.get("allocation_pct"))

        if allocation_pct is not None:
            allocation_pct = min(max(allocation_pct, 0), 100)

        start_date = clean_date(row.get("start_date"))
        end_date = clean_date(row.get("end_date"))

        # invalid date range
        if start_date and end_date and start_date > end_date:
            continue

        r = {
            "employee_id": employee_id,
            "project_code": project_code,
            "role": clean_string(row.get("role")),
            "allocation_pct": allocation_pct,
            "start_date": start_date,
            "end_date": end_date,
            "notes": clean_string(row.get("notes")),
            "created_at": clean_date(row.get("created_at")),
            "source_row_id": row.get("source_row_id")
            or row.get("row_number")
            or row.get("id"),
        }

        cleaned.append(r)

    return cleaned


# =========================
# Main pipeline
# =========================


def run_data_cleaning(data: Dict[str, Dict[str, List[Dict]]]):

    employees_raw = data["employees"]["valid"]
    projects_raw = data["projects"]["valid"]
    allocations_raw = data["allocations"]["valid"]

    employees = clean_employees(employees_raw)

    projects = clean_projects(projects_raw)

    allocations = clean_allocations(allocations_raw, employees, projects)

    return {"employees": employees, "projects": projects, "allocations": allocations}
