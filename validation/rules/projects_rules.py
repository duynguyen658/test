from typing import Any, Dict

PROJECT_RULES = {
    "project_code": {
        "required": True,
        "unique": True,
        "type": "string",
        "max_length": 20,
    },
    "project_name": {
        "required": True,
        "type": "string",
        "max_length": 200,
        "unique": True,
    },
    "client": {"required": False, "type": "string", "max_length": 200},
    "status": {
        "required": True,
        "type": "enum",
        "allowed": ["on_hold", "active", "completed", "cancelled"],
    },
    "start_date": {"required": True, "type": "date"},
    "end_date": {"required": False, "type": "date"},
    "budget": {"required": True, "type": "number", "regex": r"^\d+(\.\d+)?$", "min": 0},
    "department_owner": {"required": True, "type": "string", "max_length": 100},
    "description": {"required": False, "type": "string", "max_length": 1000},
}
