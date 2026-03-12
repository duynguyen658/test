# Solution Design Notes

## Architecture

```
candidate/
├── src/
│   └── index.js      # entry point
├── scripts/
│   ├── server.py     # FastAPI: validate, data-cleaning, sync
│   ├── data_cleaning.py
│   ├── schema_transform.py
│   └── db_sync.py
├── schema.sql
├── package.json
├── .env.example
├── N8N.md            # Hướng dẫn gọi API (validate, data-cleaning, sync) từ n8n
└── SOLUTION.md       ← you are here
```

## Pipeline Order

_Describe the order your pipeline executes and why._

## Idempotency

_Explain how re-running the script on the same data produces no duplicates._

## Duplicate Resolution Strategy

_Document your strategy for conflicting duplicate rows (e.g. first-row wins, latest wins)._

## Status Normalisation Maps

_List the input values you normalise for `employees.status` and `projects.status`._

## Employee-Specific Rules

_Document any judgement calls made (future hire dates, missing email, etc.)._

## Over-Allocation Detection

_Explain your algorithm for detecting employees exceeding 100% at any point in time._

## Error Handling

_Describe how partial failures are handled without crashing the whole pipeline._

## Assumptions & Trade-offs

_Anything not covered above — design choices, known limitations, what you would improve with more time._
