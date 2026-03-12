from typing import Any, Dict, List

from psycopg2.extensions import connection
from psycopg2.extras import execute_batch


def _extract_clean_data(raw: Any) -> Dict[str, List[Dict[str, Any]]]:
    """
    Chuẩn hoá mọi kiểu payload về:
    {
      "employees": [ ... ],
      "projects": [ ... ],
      "allocations": [ ... ]
    }

    Hỗ trợ:
    1) [
         { "type": "valid", "data": { employees:[...], projects:[...], allocations:[...] } }
       ]
    2) { "employees": [...], "projects": [...], "allocations": [...] }
    3) {
         "employees": { "valid": [...], "invalid": [...] },
         "projects":  { "valid": [...], "invalid": [...] },
         "allocations": { "valid": [...], "invalid": [...] }
       }
    """

    # Kiểu 1: list blocks [{type, data:{...}}]
    if isinstance(raw, list) and raw and isinstance(raw[0], dict):
        first = raw[0]
        if "data" in first and isinstance(first["data"], dict):
            raw = first["data"]

    # Bây giờ raw nên là dict
    if not isinstance(raw, dict):
        raise ValueError(
            "Unsupported payload format for db_sync: expected dict or list with 'data'"
        )

    # Kiểu 3: {sheet: {valid, invalid}}
    if all(k in raw for k in ("employees", "projects", "allocations")) and isinstance(
        raw.get("employees"), dict
    ):
        return {
            "employees": list((raw["employees"].get("valid") or [])),
            "projects": list((raw["projects"].get("valid") or [])),
            "allocations": list((raw["allocations"].get("valid") or [])),
        }

    # Kiểu 2: {sheet: [rows]}
    return {
        "employees": list(raw.get("employees") or []),
        "projects": list(raw.get("projects") or []),
        "allocations": list(raw.get("allocations") or []),
    }


def db_sync(payload: Any, conn: connection) -> Dict[str, int]:
    """
    payload có thể là:
    - [
        { "type": "valid", "data": { employees:[...], projects:[...], allocations:[...] } }
      ]
    - { "employees": [...], "projects": [...], "allocations": [...] }
    - { "employees": {valid,invalid}, ... } sau business / data-cleaning.
    """
    cleaned = _extract_clean_data(payload)

    employees = cleaned.get("employees") or []
    projects = cleaned.get("projects") or []
    allocations = cleaned.get("allocations") or []

    with conn.cursor() as cur:
        # =============================
        # 1️⃣ UPSERT employees (phase 1: không set manager_id để tránh lỗi FK)
        # =============================
        emp_sql = """
        INSERT INTO employees (
            employee_id,
            full_name,
            email,
            phone,
            department,
            position,
            hire_date,
            termination_date,
            status,
            salary,
            manager_id
        )
        VALUES (
            %(employee_id)s,
            %(full_name)s,
            %(email)s,
            %(phone)s,
            %(department)s,
            %(position)s,
            %(hire_date)s,
            %(termination_date)s,
            %(status)s,
            %(salary)s,
            %(manager_id)s
        )
        ON CONFLICT (employee_id)
        DO UPDATE SET
            full_name       = EXCLUDED.full_name,
            email           = EXCLUDED.email,
            phone           = EXCLUDED.phone,
            department      = EXCLUDED.department,
            position        = EXCLUDED.position,
            hire_date       = EXCLUDED.hire_date,
            termination_date= EXCLUDED.termination_date,
            status          = EXCLUDED.status,
            salary          = EXCLUDED.salary,
            updated_at      = NOW();
        """

        if employees:
            # Phase 1: insert/update mọi nhân viên với manager_id = NULL (tạm thời)
            employees_phase1: List[Dict[str, Any]] = []
            for e in employees:
                e1 = dict(e)
                e1["manager_id"] = None
                employees_phase1.append(e1)
            execute_batch(cur, emp_sql, employees_phase1)

            # Phase 2: cập nhật lại manager_id hợp lệ (employee_id tồn tại)
            cur.execute("SELECT employee_id FROM employees")
            existing_ids = {r[0] for r in cur.fetchall()}

            emp_ids = {e["employee_id"] for e in employees if e.get("employee_id")}

            valid_ids = emp_ids | existing_ids
            update_rows: List[Dict[str, Any]] = []
            for e in employees:
                eid = (e.get("employee_id") or "").strip()
                mid = (e.get("manager_id") or "").strip()

                if eid and mid and mid in valid_ids:
                    update_rows.append(
                        {
                            "employee_id": eid,
                            "manager_id": mid,
                        }
                    )
            if update_rows:
                update_sql = """
                UPDATE employees
                SET manager_id = %(manager_id)s
                WHERE employee_id = %(employee_id)s;
                """
                execute_batch(cur, update_sql, update_rows)

        # =============================
        # 2️⃣ UPSERT projects
        # =============================
        proj_sql = """
        INSERT INTO projects (
            project_code,
            project_name,
            client,
            status,
            start_date,
            end_date,
            budget,
            department_owner,
            description
        )
        VALUES (
            %(project_code)s,
            %(project_name)s,
            %(client)s,
            %(status)s,
            %(start_date)s,
            %(end_date)s,
            %(budget)s,
            %(department_owner)s,
            %(description)s
        )
        ON CONFLICT (project_code)
        DO UPDATE SET
            project_name     = EXCLUDED.project_name,
            client           = EXCLUDED.client,
            status           = EXCLUDED.status,
            start_date       = EXCLUDED.start_date,
            end_date         = EXCLUDED.end_date,
            budget           = EXCLUDED.budget,
            department_owner = EXCLUDED.department_owner,
            description      = EXCLUDED.description,
            updated_at       = NOW();
        """

        if projects:
            execute_batch(cur, proj_sql, projects)

        # =============================
        # 3️⃣ INSERT allocations
        # =============================
        clean_allocations: List[Dict[str, Any]] = []
        for a in allocations:
            pct = a.get("allocation_pct")
            if pct is None:
                continue
            try:
                if float(pct) <= 0:
                    continue
            except Exception:
                continue

            clean_allocations.append(
                {
                    "employee_id": a.get("employee_id"),
                    "project_code": a.get("project_code"),
                    "role": a.get("role"),
                    "allocation_pct": a.get("allocation_pct"),
                    "start_date": a.get("start_date"),
                    "end_date": a.get("end_date"),
                    "notes": a.get("notes"),
                    # ưu tiên source_row_id nếu đã được giữ lại,
                    # fallback sang row_number hoặc id nếu cần
                    "source_row_id": (
                        a.get("source_row_id") or a.get("row_number") or a.get("id")
                    ),
                }
            )

        alloc_sql = """
        INSERT INTO allocations (
            employee_id,
            project_code,
            role,
            allocation_pct,
            start_date,
            end_date,
            notes,
            source_row_id
        )
        VALUES (
            %(employee_id)s,
            %(project_code)s,
            %(role)s,
            %(allocation_pct)s,
            %(start_date)s,
            %(end_date)s,
            %(notes)s,
            %(source_row_id)s
        );
        """

        if clean_allocations:
            execute_batch(cur, alloc_sql, clean_allocations)

        # =============================
        # 4️⃣ Ghi log vào sync_log
        # =============================
        total_rows_read = len(employees) + len(projects) + len(allocations)
        total_rows_inserted = len(employees) + len(projects) + len(clean_allocations)
        total_rows_rejected = max(len(allocations) - len(clean_allocations), 0)

        sync_sql = """
        INSERT INTO sync_log (
            sheet_name,
            rows_read,
            rows_inserted,
            rows_updated,
            rows_rejected,
            rejection_detail
        )
        VALUES (
            %(sheet_name)s,
            %(rows_read)s,
            %(rows_inserted)s,
            %(rows_updated)s,
            %(rows_rejected)s,
            %(rejection_detail)s
        );
        """
        cur.execute(
            sync_sql,
            {
                "sheet_name": "batch",
                "rows_read": total_rows_read,
                "rows_inserted": total_rows_inserted,
                "rows_updated": 0,
                "rows_rejected": total_rows_rejected,
                "rejection_detail": None,
            },
        )

    conn.commit()

    return {
        "employees": len(employees),
        "projects": len(projects),
        "allocations": len(clean_allocations),
    }
