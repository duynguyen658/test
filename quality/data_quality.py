from quality.engine.quality_checker import run_quality_checks
from quality.rules.allocation_quality_rules import ALLOCATION_QUALITY_RULES
from quality.rules.employee_quality_rules import EMPLOYEE_QUALITY_RULES
from quality.rules.project_quality_rules import PROJECT_QUALITY_RULES


def _extract_rows(data, sheet: str):
    """
    Cho phép 2 kiểu input:
    - { employees: [...], projects: [...], allocations: [...] }
    - { employees: {valid:[...], invalid:[...]}, ... }
    """
    block = data.get(sheet, [])
    if isinstance(block, dict) and "valid" in block:
        return block.get("valid") or []
    return block or []


def run_data_quality(data):
    # Lấy rows từ input (dù là cleaned hay {valid,invalid})
    employees = _extract_rows(data, "employees")
    projects = _extract_rows(data, "projects")
    allocations = _extract_rows(data, "allocations")

    employees_result = run_quality_checks(employees, EMPLOYEE_QUALITY_RULES)

    projects_result = run_quality_checks(projects, PROJECT_QUALITY_RULES)

    allocations_result = run_quality_checks(allocations, ALLOCATION_QUALITY_RULES)

    report = {
        "employees": employees_result,
        "projects": projects_result,
        "allocations": allocations_result,
    }

    return report
