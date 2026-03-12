from typing import Any, Dict

EMPLOYEE_RULES: Dict[str, Dict[str, Any]] = {
    "employee_id": {
        "required": True,
        "unique": True,
        "type": "string",
        "max_length": 10,
    },
    "full_name": {"required": True, "type": "string", "max_length": 200},
    "email": {
        "required": True,
        "unique": True,
        "type": "email",
        "regex": r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
        "max_length": 255,
    },
    "phone": {
        "required": True,
        "type": "string",
        "min_length": 7,
        "max_length": 20,
        "regex": r"^\+?[0-9\-\.\s]{7,20}$",
    },
    "department": {"required": True, "type": "string", "max_length": 100},
    "position": {"required": True, "type": "string", "max_length": 100},
    "hire_date": {"required": True, "max": "today", "type": "date"},
    "termination_date": {"required": False, "type": "date"},
    "status": {
        "required": True,
        "type": "enum",
        "allowed": ["active", "on_leave", "terminated"],
    },
    "salary": {"required": True, "type": "number", "regex": r"^\d+(\.\d+)?$", "min": 0},
    "manager_id": {"required": True, "type": "string", "max_length": 20},
}
