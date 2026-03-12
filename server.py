import json
import logging
from typing import Any, Dict

import psycopg2
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from psycopg2.extras import Json

from cleaning.data_cleaning import run_data_cleaning
from database.db_sync import db_sync
from database.error_logs import save_error_logs
from quality.data_quality import run_data_quality
from validation.business_validation import run_business_validation
from validation.schema_validation import validate_payload

app = FastAPI()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("api")


# ------------------------------------------------
# Helpers
# ------------------------------------------------


async def _get_json(request: Request) -> Any:

    try:
        return await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")


def _summary(result: Dict):

    return {
        sheet: {
            "valid_rows": len(result[sheet]["valid"]),
            "invalid_rows": len(result[sheet]["invalid"]),
        }
        for sheet in result
    }


# ------------------------------------------------
# Health check
# ------------------------------------------------


@app.get("/health")
def health():
    return {"status": "ok"}


# ------------------------------------------------
# Schema validation
# ------------------------------------------------


@app.post("/api/schema-validate")
async def api_schema_validate(request: Request):

    try:

        body = await _get_json(request)

        logger.info("Schema validation started")

        result = validate_payload(body)

        summary = _summary(result)

        logger.info(f"Schema validation summary: {summary}")

        return {"ok": True, "summary": summary, "data": result}

    except ValueError as err:

        raise HTTPException(status_code=400, detail=str(err))

    except Exception:

        logger.exception("Schema validation error")

        raise HTTPException(status_code=500, detail="Internal server error")


# ------------------------------------------------
# Business validation
# ------------------------------------------------
@app.post("/api/business-validate")
async def api_business_validate(request: Request):
    try:
        body = await _get_json(request)
        logger.info("Business validation started")
        # body là list [{ type, data: {employees,projects,allocations} }, ...]
        if (
            isinstance(body, list)
            and body
            and isinstance(body[0], dict)
            and "data" in body[0]
        ):
            result = run_business_validation(body)
        # body là dict đã schema-normalized
        elif isinstance(body, dict) and all(
            k in body for k in ("employees", "projects", "allocations")
        ):
            result = run_business_validation(body)
        else:
            # payload gốc (joined/sheets) -> schema trước rồi business
            logger.info("Running schema validation first")
            schema_result = validate_payload(body)
            result = run_business_validation(schema_result)
        summary = _summary(result)
        logger.info(f"Business validation summary: {summary}")
        return {
            "ok": True,
            "summary": summary,
            "data": result,
        }
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception:
        logger.exception("Business validation error")
        raise HTTPException(status_code=500, detail="Internal server error")


# ------------------------------------------------
# Data cleaning
# ------------------------------------------------
@app.post("/api/data-cleaning")
async def api_data_cleaning(request: Request):
    try:
        body = await _get_json(request)
        logger.info("Data cleaning started")

        # Gỡ bọc n8n: { "items": [ { "json": ... } ] }
        if (
            isinstance(body, dict)
            and "items" in body
            and isinstance(body["items"], list)
            and body["items"]
        ):
            first = body["items"][0]
            if isinstance(first, dict) and "json" in first:
                body = first["json"]

        # 1) dict đã schema/business-normalized
        if isinstance(body, dict) and all(
            k in body for k in ("employees", "projects", "allocations")
        ):
            bv_result = run_business_validation(body)

        # 2) list blocks từ n8n (có field "data")
        elif (
            isinstance(body, list)
            and body
            and isinstance(body[0], dict)
            and "data" in body[0]
        ):
            bv_result = run_business_validation(body)

        # 3) payload gốc -> schema trước rồi business
        else:
            logger.info("Data cleaning: running schema validation first")
            schema_result = validate_payload(body)
            bv_result = run_business_validation(schema_result)

        # Cleaning chỉ chạy trên hàng valid
        cleaned = run_data_cleaning(bv_result)

        # Ghép lại theo format:
        # data.{sheet}.valid  = rows đã clean
        # data.{sheet}.invalid = rows invalid từ business_validate
        data_out = {
            "employees": {
                "valid": cleaned.get("employees", []),
                "invalid": bv_result["employees"]["invalid"],
            },
            "projects": {
                "valid": cleaned.get("projects", []),
                "invalid": bv_result["projects"]["invalid"],
            },
            "allocations": {
                "valid": cleaned.get("allocations", []),
                "invalid": bv_result["allocations"]["invalid"],
            },
        }

        # Summary giống business-validate nhưng theo data_out
        summary = _summary(data_out)

        logger.info("Data cleaning completed")

        return {
            "ok": True,
            "summary": summary,
            "data": data_out,
        }

    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception:
        logger.exception("Data cleaning error")
        raise HTTPException(status_code=500, detail="Internal server error")


# ------------------------------------------------
# Data quality
# ------------------------------------------------
@app.post("/api/data-quality")
async def data_quality(request: Request):
    try:
        body = await _get_json(request)
        logger.info("Data quality started")

        # Gỡ bọc n8n: { "items": [ { "json": ... } ] }
        if (
            isinstance(body, dict)
            and "items" in body
            and isinstance(body["items"], list)
            and body["items"]
        ):
            first = body["items"][0]
            if isinstance(first, dict) and "json" in first:
                body = first["json"]

        # 1) Nếu đã là dict {employees:{valid,invalid}, ...} hoặc {employees: [...], ...}
        if isinstance(body, dict) and all(
            k in body for k in ("employees", "projects", "allocations")
        ):
            base_data = body

        # 2) list blocks n8n
        elif (
            isinstance(body, list)
            and body
            and isinstance(body[0], dict)
            and "data" in body[0]
        ):
            # đi qua business + cleaning để ra cleaned data
            bv_result = run_business_validation(body)
            base_data = run_data_cleaning(bv_result)

        # 3) payload gốc -> schema + business + cleaning
        else:
            logger.info("Data quality: running schema + business + cleaning first")
            schema_result = validate_payload(body)
            bv_result = run_business_validation(schema_result)
            base_data = run_data_cleaning(bv_result)

        report = run_data_quality(base_data)

        data_out = {
            "employees": {
                "valid": report["employees"]["valid_data"],
                "invalid": report["employees"]["invalid_data"],
            },
            "projects": {
                "valid": report["projects"]["valid_data"],
                "invalid": report["projects"]["invalid_data"],
            },
            "allocations": {
                "valid": report["allocations"]["valid_data"],
                "invalid": report["allocations"]["invalid_data"],
            },
        }
        summary = {
            "employees": {
                "valid_rows": report["employees"]["valid_rows"],
                "invalid_rows": report["employees"]["invalid_rows"],
            },
            "projects": {
                "valid_rows": report["projects"]["valid_rows"],
                "invalid_rows": report["projects"]["invalid_rows"],
            },
            "allocations": {
                "valid_rows": report["allocations"]["valid_rows"],
                "invalid_rows": report["allocations"]["invalid_rows"],
            },
        }

        logger.info("Data quality completed")

        return {
            "ok": True,
            "summary": summary,
            "data": data_out,
        }

    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception:
        logger.exception("Data quality error")
        raise HTTPException(status_code=500, detail="Internal server error")


# ------------------------------------------------
# DB sync
# ------------------------------------------------
@app.post("/api/db-sync")
async def api_db_sync(request: Request):
    try:
        body = await _get_json(request)

        if (
            isinstance(body, dict)
            and "items" in body
            and isinstance(body["items"], list)
            and body["items"]
        ):
            first = body["items"][0]
            if isinstance(first, dict) and "json" in first:
                body = first["json"]

        conn = psycopg2.connect(
            host="localhost",
            dbname="test",
            user="postgres",
            password="123456",
        )

        try:
            result = db_sync(
                body, conn
            )  # {employees: ..., projects: ..., allocations: ...}
        finally:
            conn.close()
        return {
            "ok": True,
            "employees": result.get("employees", 0),
            "projects": result.get("projects", 0),
            "allocations": result.get("allocations", 0),
            "total_rows": (
                result.get("employees", 0)
                + result.get("projects", 0)
                + result.get("allocations", 0)
            ),
        }

    except Exception:
        logger.exception("DB sync error")
        raise HTTPException(status_code=500, detail="Internal server error")


# ------------------------------------------------
# Error logs
# ------------------------------------------------
@app.post("/api/error-logs")
async def api_error_logs(request: Request):
    try:
        body = await _get_json(request)

        if (
            isinstance(body, dict)
            and "items" in body
            and isinstance(body["items"], list)
            and body["items"]
        ):
            first = body["items"][0]
            if isinstance(first, dict) and "json" in first:
                body = first["json"]

        conn = psycopg2.connect(
            host="localhost",
            dbname="test",
            user="postgres",
            password="123456",
        )

        try:
            inserted = save_error_logs(body, conn)
        finally:
            conn.close()

        return {
            "ok": True,
            "inserted": inserted,
        }

    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception:
        logger.exception("Error logging failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# ------------------------------------------------
# Run server
# ------------------------------------------------

if __name__ == "__main__":

    logger.info("Starting API server on http://0.0.0.0:3000")

    uvicorn.run("server:app", host="0.0.0.0", port=3000, reload=True)
