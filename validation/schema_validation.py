import logging
import re
from typing import Any, Dict, List, Tuple

from validation.rules.allocations_rules import ALLOCATION_RULES
from validation.rules.employees_rules import EMPLOYEE_RULES
from validation.rules.projects_rules import PROJECT_RULES

logger = logging.getLogger(__name__)

# -----------------------------
# Config
# -----------------------------

VALID_SHEETS = ["employees", "projects", "allocations"]
VALID_SHEETS_SET = set(VALID_SHEETS)

MAX_ROWS_PER_SHEET = 5000

RULE_MAP = {
    "employees": EMPLOYEE_RULES,
    "projects": PROJECT_RULES,
    "allocations": ALLOCATION_RULES,
}


# -----------------------------
# Payload validation
# -----------------------------


def _validate_sheet_payload(body: Any) -> Tuple[str, List[Dict]]:

    if not isinstance(body, dict):
        raise ValueError("Payload must be JSON object")

    sheet = body.get("sheet")
    rows = body.get("data")

    if sheet not in VALID_SHEETS_SET:
        raise ValueError(f"Invalid sheet '{sheet}'")

    if not isinstance(rows, list):
        raise ValueError("'data' must be list")

    if len(rows) > MAX_ROWS_PER_SHEET:
        raise ValueError(
            f"Too many rows in sheet '{sheet}' (limit={MAX_ROWS_PER_SHEET})"
        )

    return sheet, rows


# -----------------------------
# Row structure validation
# -----------------------------


def _validate_row_structure(sheet: str, idx: int, row: Any):

    if not isinstance(row, dict):

        return {
            "sheet": sheet,
            "row": idx + 1,
            "error_code": "INVALID_ROW_TYPE",
            "message": "Row must be JSON object",
            "raw": row,
        }

    if not row:

        return {
            "sheet": sheet,
            "row": idx + 1,
            "error_code": "EMPTY_ROW",
            "message": "Row is empty",
            "raw": row,
        }

    return None


# -----------------------------
# Rule validation
# -----------------------------


def _validate_row_rules(sheet: str, idx: int, row: Dict):

    rules = RULE_MAP.get(sheet, {})

    errors = []

    for field, rule in rules.items():

        value = row.get(field)

        # required
        if rule.get("required") and (value is None or value == ""):
            errors.append(f"{field} is required")
            continue

        if value is None or value == "":
            continue

        # type
        rtype = rule.get("type")

        if rtype == "string":
            if not isinstance(value, str):
                errors.append(f"{field} must be string")

        elif rtype == "number":
            try:
                value = float(value)
            except Exception:
                errors.append(f"{field} must be number")
                continue

        elif rtype == "date":
            if not isinstance(value, str):
                errors.append(f"{field} must be date string")
                continue
            if value.strip().lower() in {"n/a", "na", "N/A", "NA", "null", "none", "-"}:
                errors.append(f"{field} contains invalid date value")

        # max_length
        if "max_length" in rule:
            if len(str(value)) > rule["max_length"]:
                errors.append(f"{field} exceeds max_length")

        # enum
        if "allowed" in rule:
            if value not in rule["allowed"]:
                errors.append(f"{field} must be one of {rule['allowed']}")

        # min
        if "min" in rule:
            try:
                if float(value) < rule["min"]:
                    errors.append(f"{field} below minimum")
            except Exception:
                pass

        # max
        if "max" in rule:
            try:
                if float(value) > rule["max"]:
                    errors.append(f"{field} exceeds maximum")
            except Exception:
                pass

        # regex
        if "regex" in rule:
            if not re.match(rule["regex"], str(value)):
                errors.append(f"{field} format invalid")

    if errors:

        return {
            "sheet": sheet,
            "row": idx + 1,
            "error_code": "RULE_VIOLATION",
            "message": "; ".join(errors),
            "raw": row,
        }

    return None


# -----------------------------
# Validate payload
# -----------------------------


def validate_payload(body: Any) -> Dict[str, Dict[str, List[Dict]]]:

    if isinstance(body, dict) and "sheet" in body:
        body_list = [body]

    elif isinstance(body, list):
        body_list = body

    else:
        raise ValueError("Payload must be sheet object or list")

    result: Dict[str, Dict[str, List[Dict]]] = {
        sheet: {"valid": [], "invalid": []} for sheet in VALID_SHEETS
    }

    seen_sheets = set()

    for item in body_list:

        sheet, rows = _validate_sheet_payload(item)

        if sheet in seen_sheets:
            raise ValueError(f"Duplicate sheet '{sheet}' in payload")

        seen_sheets.add(sheet)

        for idx, row in enumerate(rows):

            # structure validation
            error = _validate_row_structure(sheet, idx, row)

            if error:
                result[sheet]["invalid"].append(error)
                continue

            # rule validation
            rule_error = _validate_row_rules(sheet, idx, row)

            if rule_error:

                result[sheet]["invalid"].append(rule_error)

                logger.warning(f"Rule violation: sheet={sheet}, row={idx+1}")

            else:

                result[sheet]["valid"].append(row)

    # missing sheets warning

    missing = VALID_SHEETS_SET - seen_sheets
    if missing:
        logger.warning(f"Missing sheets in payload: {missing}")

    # summary

    summary = {
        sheet: {
            "valid": len(result[sheet]["valid"]),
            "invalid": len(result[sheet]["invalid"]),
        }
        for sheet in VALID_SHEETS
    }

    logger.info(f"Schema validation summary: {summary}")

    return result
