from typing import Any, Dict, List

from psycopg2.extensions import connection
from psycopg2.extras import Json


def _normalize_logs(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return payload
    raise ValueError("Payload for error_logs must be object or list")


def save_error_logs(payload: Any, conn: connection) -> int:
    logs = _normalize_logs(payload)
    if not logs:
        return 0

    inserted = 0
    with conn.cursor() as cur:
        sql = """
        INSERT INTO error_logs (
            source,
            format,
            summary,
            errors,
            raw_sample
        )
        VALUES (
            %s, %s, %s, %s, %s
        );
        """
        for item in logs:
            cur.execute(
                sql,
                (
                    item.get("source"),
                    item.get("format"),
                    Json(item.get("summary") or {}),
                    Json(item.get("errors") or {}),
                    (
                        Json(item.get("raw_sample"))
                        if item.get("raw_sample") is not None
                        else None
                    ),
                ),
            )
            inserted += 1

    conn.commit()
    return inserted
