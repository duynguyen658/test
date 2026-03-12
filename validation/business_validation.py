import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _parse_date(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(value), fmt).date()
        except Exception:
            continue
    return None


def _reshape_from_blocks(
    blocks: List[Dict[str, Any]]
) -> Dict[str, Dict[str, List[Dict]]]:
    """
    Hỗ trợ 2 kiểu block:
    1) [{ "type": "valid", "sheet": "...", "data": [...] }, ...]
    2) [{ "type": "valid", "data": { "employees": [...], "projects": [...], "allocations": [...] } }]
    """

    result: Dict[str, Dict[str, List[Dict]]] = {
        "employees": {"valid": [], "invalid": []},
        "projects": {"valid": [], "invalid": []},
        "allocations": {"valid": [], "invalid": []},
    }

    if not blocks:
        return result

    # Kiểu 2: [{ type, data: {employees,projects,allocations} }]
    if (
        len(blocks) == 1
        and isinstance(blocks[0], dict)
        and isinstance(blocks[0].get("data"), dict)
    ):
        d = blocks[0]["data"]
        for sheet in ("employees", "projects", "allocations"):
            rows = d.get(sheet) or []
            if isinstance(rows, list):
                result[sheet]["valid"].extend(rows)
        return result

    # Kiểu 1: [{ type, sheet, data }, ...]
    for block in blocks:
        if not isinstance(block, dict):
            continue
        sheet = block.get("sheet")
        block_type = block.get("type")  # "valid"|"invalid"
        rows = block.get("data") or []

        if sheet not in result or block_type not in ("valid", "invalid"):
            continue
        if isinstance(rows, list):
            result[sheet][block_type].extend(rows)

    return result


def run_business_validation(data_or_blocks: Any) -> Dict[str, Dict[str, List[Dict]]]:
    """
    Input có thể là:
    - dict đã qua schema_validate:
        { employees: {valid, invalid}, projects: {...}, allocations: {...} }
    - dict “thô” sau cleaning round 1:
        { employees: [...], projects: [...], allocations: [...] }
    - hoặc list blocks như payload từ n8n:
        [
          { "type": "valid", "data": { employees:[...], projects:[...], allocations:[...] } }
        ]
        hoặc
        [
          { "type": "valid", "sheet": "...", "data":[...] },
          ...
        ]
    """

    # Trường hợp 1: đã đúng dạng {sheet: {valid, invalid}}
    if isinstance(data_or_blocks, dict) and all(
        isinstance(data_or_blocks.get(k), dict)
        and "valid" in data_or_blocks[k]
        and "invalid" in data_or_blocks[k]
        for k in ("employees", "projects", "allocations")
    ):
        data: Dict[str, Dict[str, List[Dict]]] = data_or_blocks

    # Trường hợp 2: dict “thô” {sheet: [rows]}
    elif isinstance(data_or_blocks, dict) and all(
        k in data_or_blocks for k in ("employees", "projects", "allocations")
    ):
        data = {
            "employees": {
                "valid": list(data_or_blocks.get("employees") or []),
                "invalid": [],
            },
            "projects": {
                "valid": list(data_or_blocks.get("projects") or []),
                "invalid": [],
            },
            "allocations": {
                "valid": list(data_or_blocks.get("allocations") or []),
                "invalid": [],
            },
        }

    # Trường hợp 3: list blocks từ n8n
    elif isinstance(data_or_blocks, list):
        data = _reshape_from_blocks(data_or_blocks)

    # Trường hợp fallback
    else:
        logger.warning(
            "run_business_validation: unsupported input format, returning empty result"
        )
        data = {
            "employees": {"valid": [], "invalid": []},
            "projects": {"valid": [], "invalid": []},
            "allocations": {"valid": [], "invalid": []},
        }

    employees_valid = data["employees"]["valid"]
    projects_valid = data["projects"]["valid"]
    allocations_valid = data["allocations"]["valid"]

    employees_invalid = data["employees"]["invalid"]
    projects_invalid = data["projects"]["invalid"]
    allocations_invalid = data["allocations"]["invalid"]

    # -------------------- Employees --------------------
    seen_employee_ids = set()
    clean_employees = []

    for idx, row in enumerate(employees_valid):
        employee_id = row.get("employee_id")
        errors = []

        if employee_id in seen_employee_ids:
            errors.append("duplicate employee_id")

        if errors:
            employees_invalid.append(
                {
                    "row": row.get("row_number") or idx + 1,
                    "error": "; ".join(errors),
                    "raw": row,
                }
            )
        else:
            seen_employee_ids.add(employee_id)
            clean_employees.append(row)

    data["employees"]["valid"] = clean_employees

    # -------------------- Projects --------------------
    clean_projects = []
    project_dates = {}

    for idx, row in enumerate(projects_valid):
        project_code = row.get("project_code")
        start = _parse_date(row.get("start_date"))
        end = _parse_date(row.get("end_date"))

        errors = []
        if start and end and end < start:
            errors.append("end_date must be after start_date")

        if errors:
            projects_invalid.append(
                {
                    "row": row.get("row_number") or idx + 1,
                    "error": "; ".join(errors),
                    "raw": row,
                }
            )
        else:
            clean_projects.append(row)
            project_dates[project_code] = (start, end)

    data["projects"]["valid"] = clean_projects

    # -------------------- Allocations --------------------
    employee_ids = {e["employee_id"] for e in data["employees"]["valid"]}
    project_codes = {p["project_code"] for p in data["projects"]["valid"]}

    clean_allocations = []
    allocation_sum = {}
    allocation_keys = set()
    employee_allocations = {}

    for idx, row in enumerate(allocations_valid):
        employee_id = row.get("employee_id")
        project_code = row.get("project_code")

        start = _parse_date(row.get("start_date"))
        end = _parse_date(row.get("end_date"))

        pct = row.get("allocation_pct")
        errors = []

        # FK
        if employee_id not in employee_ids:
            errors.append("employee_id not found")
        if project_code not in project_codes:
            errors.append("project_code not found")

        # date logic
        if start and end and end < start:
            errors.append("allocation end_date must be after start_date")

        # duplicate allocation
        alloc_key = (employee_id, project_code, start, end)
        if alloc_key in allocation_keys:
            errors.append("duplicate allocation record")
        allocation_keys.add(alloc_key)

        # overlap per employee
        emp_list = employee_allocations.setdefault(employee_id, [])
        for ex_start, ex_end in emp_list:
            if start and end and ex_start and ex_end:
                overlap = not (end < ex_start or start > ex_end)
                if overlap:
                    errors.append("allocation date overlap")
        emp_list.append((start, end))

        # pct sum
        allocation_sum.setdefault(employee_id, 0)
        try:
            allocation_sum[employee_id] += float(pct)
        except Exception:
            pass

        if errors:
            allocations_invalid.append(
                {
                    "row": row.get("row_number") or idx + 1,
                    "error": "; ".join(errors),
                    "raw": row,
                }
            )
        else:
            clean_allocations.append(row)

    for emp, total in allocation_sum.items():
        if total > 100:
            logger.warning(f"Employee {emp} allocation exceeds 100% ({total})")

    data["allocations"]["valid"] = clean_allocations

    summary = {
        "employees_valid": len(data["employees"]["valid"]),
        "employees_invalid": len(data["employees"]["invalid"]),
        "projects_valid": len(data["projects"]["valid"]),
        "projects_invalid": len(data["projects"]["invalid"]),
        "allocations_valid": len(data["allocations"]["valid"]),
        "allocations_invalid": len(data["allocations"]["invalid"]),
    }
    logger.info(f"Business validation summary: {summary}")

    return data
