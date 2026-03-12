# Data Engineer Interview Test

## Context

You are joining the data team at a mid-size tech consulting company. The company manages its workforce and project allocations in Google Sheets (three separate sheets). Your task is to build a reliable sync pipeline that moves this data into a PostgreSQL database so it can be queried reliably for reporting and analytics.

---

## The Data

Three Google Sheets are available (URLs will be provided separately):

| Sheet           | Description                                                |
| --------------- | ---------------------------------------------------------- |
| **Employees**   | Company headcount — active, on-leave, and terminated staff |
| **Projects**    | All client and internal projects                           |
| **Allocations** | Point-in-time records of employee-to-project assignments   |

> The allocation sheet is **transactional** — each row represents a specific time window during which an employee was allocated to a project. Multiple rows for the same (employee, project) pair are valid if they cover different date ranges.

---

## Your Task

Write a **Node.js** script (or small service) that:

1. **Reads** data from the three Google Sheets via the Google Sheets API v4
2. **Validates and cleans** the data according to the quality rules below
3. **Loads** clean records into PostgreSQL (tables: `employees`, `projects`, `allocations`)
4. **Produces a rejection report** — a summary of every row that was skipped or auto-corrected and why

The sync must be **idempotent**: running the script multiple times on the same data must not create duplicate rows in the database.

---

## Technical Requirements

- **Runtime**: Node.js (any version ≥ 18)
- **Database**: PostgreSQL (any version ≥ 14)
- **Google API**: `googleapis` npm package (OAuth2 service account recommended)
- **DB client**: `pg` or `knex` — your choice
- You may use any additional npm packages you find helpful

Provide a `package.json`, a `.env.example` showing required environment variables, and a brief `SOLUTION.md` explaining your design decisions.

---

## Data Quality Rules

### Employees

| Rule                                                                               | Action                                                                                    |
| ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Duplicate `employee_id` — identical rows                                           | Keep one, discard the rest                                                                |
| Duplicate `employee_id` — conflicting data                                         | Flag for review; apply a documented resolution strategy (e.g. latest wins, or reject all) |
| Missing `employee_id` or `full_name`                                               | **Reject**                                                                                |
| Invalid email format                                                               | **Reject** the record                                                                     |
| `salary` stored as currency string (e.g. `"$85,000"`)                              | **Clean**: strip symbols, parse as number                                                 |
| Negative `salary`                                                                  | **Reject**                                                                                |
| `hire_date` in non-standard format (e.g. `MM/DD/YYYY`)                             | **Normalise** to `YYYY-MM-DD`                                                             |
| `termination_date` before `hire_date`                                              | **Reject**                                                                                |
| `hire_date` in the future                                                          | Flag as warning; **reject** or accept based on your decision (document it)                |
| `status` not in `active / terminated / on_leave` (e.g. `"yes"`, `"1"`, `"ACTIVE"`) | **Normalise** if mapping is unambiguous; otherwise **reject**                             |
| Employee has `termination_date` in the past but `status = active`                  | **Correct** status to `terminated`                                                        |
| `manager_id` references a non-existent `employee_id`                               | **Null out** the field and log a warning                                                  |
| Completely blank row                                                               | **Skip** silently                                                                         |
| Literal string `"NULL"` in name field                                              | Treat as missing → **Reject**                                                             |

### Projects

| Rule                                                       | Action                                          |
| ---------------------------------------------------------- | ----------------------------------------------- |
| Duplicate `project_code` — identical rows                  | Keep one                                        |
| Duplicate `project_code` — conflicting data                | Flag; document resolution strategy              |
| Missing `project_code` or `project_name`                   | **Reject**                                      |
| `end_date` before `start_date`                             | **Reject**                                      |
| Invalid `start_date` (e.g. `"N/A"`)                        | **Reject**                                      |
| `budget` as currency string                                | **Clean**                                       |
| `status` not in `active / completed / on_hold / cancelled` | **Normalise** if possible; otherwise **reject** |

### Allocations

| Rule                                                                         | Action                                                                                                    |
| ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `employee_id` not found in `employees` table                                 | **Reject**                                                                                                |
| `project_code` not found in `projects` table                                 | **Reject**                                                                                                |
| Missing `employee_id` or `project_code`                                      | **Reject**                                                                                                |
| Missing `start_date`                                                         | **Reject**                                                                                                |
| `end_date` before `start_date`                                               | **Reject**                                                                                                |
| `allocation_pct` ≤ 0 or > 100                                                | **Reject**                                                                                                |
| Exact duplicate row                                                          | Keep one                                                                                                  |
| Allocation record for an employee after their `termination_date`             | **Reject**                                                                                                |
| Employee total allocation across all concurrent projects > 100% at any point | Flag as **warning** in the rejection report (do not silently drop — this requires date-overlap detection) |

---

## Deliverables

```
solution/
├── src/
│   ├── index.js          # entry point
│   ├── sheets.js         # Google Sheets reader
│   ├── transform/
│   │   ├── employees.js
│   │   ├── projects.js
│   │   └── allocations.js
│   └── db/
│       ├── client.js
│       └── upsert.js
├── schema.sql            # DDL to create the target tables
├── package.json
├── .env.example
└── SOLUTION.md           # design notes and assumptions
```

Structure is a suggestion — you may organise however you see fit.

---

## Evaluation Criteria

| Area                          | What we look for                                                                             |
| ----------------------------- | -------------------------------------------------------------------------------------------- |
| **Correctness**               | All valid rows land in the DB; all invalid rows are caught and reported                      |
| **Idempotency**               | Re-running produces no duplicates or phantom updates                                         |
| **Data quality coverage**     | Edge cases handled: type coercion, normalisation, referential integrity, duplicate detection |
| **Over-allocation detection** | Correctly identifies employees exceeding 100% via date-overlap logic                         |
| **Code quality**              | Readable, modular, easy to extend                                                            |
| **Error handling**            | Partial failures don't crash the whole pipeline; errors are reported clearly                 |
| **Schema design**             | Appropriate types, constraints, indexes                                                      |
| **Documentation**             | Clear explanation of decisions and trade-offs in `SOLUTION.md`                               |

---

## Bonus Points

- Incremental sync: only process rows changed since the last run
- Dry-run mode: validate and report without writing to the database
- Unit tests for the transform/validation layer
- Docker Compose setup for local PostgreSQL

---

## Getting Started

1. Create a Google Cloud project and enable the **Google Sheets API**
2. Create a **service account**, download the JSON key, and share the Google Sheets with the service account email
3. Clone/copy this repo, run `npm install`
4. Copy `.env.example` → `.env` and fill in your credentials
5. Run `psql -f schema.sql` to create the tables
6. Run `node src/index.js`

Good luck!
