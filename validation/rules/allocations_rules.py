from typing import Any, Dict

ALLOCATION_RULES = {
    "employee_id": {"required": True, "type": "string", "max_length": 20},
    "project_code": {"required": True, "type": "string", "max_length": 20},
    "role": {"required": True, "type": "string", "max_length": 100},
    "allocation_pct": {"required": True, "type": "number", "min": 0, "max": 100},
    "start_date": {"required": True, "type": "date"},
    "end_date": {"required": False, "type": "date"},
    "notes": {"required": False, "type": "string", "max_length": 1000},
    "created_at": {"required": True, "type": "datetime"},
}
