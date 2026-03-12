-- ============================================================
-- Target PostgreSQL Schema
-- Data Engineering Interview Test
-- ============================================================

-- employees: one row per employee (deduplicated, validated)
CREATE TABLE employees (
    id              SERIAL PRIMARY KEY,
    employee_id     VARCHAR(20)  UNIQUE NOT NULL,
    full_name       VARCHAR(200) NOT NULL,
    email           VARCHAR(255) UNIQUE,
    phone           VARCHAR(50),
    department      VARCHAR(100),
    position        VARCHAR(100),
    hire_date       DATE         NOT NULL,
    termination_date DATE,
    status          VARCHAR(20)  NOT NULL CHECK (status IN ('active', 'terminated', 'on_leave')),
    salary          NUMERIC(12, 2),
    manager_id      VARCHAR(20)  REFERENCES employees(employee_id),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- business-rule constraints (can be enforced at DB or application level)
    CONSTRAINT chk_termination_after_hire
        CHECK (termination_date IS NULL OR termination_date > hire_date),
    CONSTRAINT chk_salary_positive
        CHECK (salary IS NULL OR salary >= 0)
);

-- projects: one row per project (deduplicated, validated)
CREATE TABLE projects (
    id               SERIAL PRIMARY KEY,
    project_code     VARCHAR(20)  UNIQUE NOT NULL,
    project_name     VARCHAR(200) NOT NULL,
    client           VARCHAR(200),
    status           VARCHAR(20)  NOT NULL CHECK (status IN ('active', 'completed', 'on_hold', 'cancelled')),
    start_date       DATE         NOT NULL,
    end_date         DATE,
    budget           NUMERIC(15, 2),
    department_owner VARCHAR(100),
    description      TEXT,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_project_end_after_start
        CHECK (end_date IS NULL OR end_date > start_date),
    CONSTRAINT chk_budget_positive
        CHECK (budget IS NULL OR budget >= 0)
);

-- allocations: transactional / point-in-time records
-- Each row represents one period of an employee's allocation to a project.
-- Multiple rows per (employee, project) are valid for different time windows.
CREATE TABLE allocations (
    id              SERIAL PRIMARY KEY,
    employee_id     VARCHAR(20)  NOT NULL REFERENCES employees(employee_id),
    project_code    VARCHAR(20)  NOT NULL REFERENCES projects(project_code),
    role            VARCHAR(100),
    allocation_pct  NUMERIC(5, 2) NOT NULL
                        CHECK (allocation_pct > 0 AND allocation_pct <= 100),
    start_date      DATE         NOT NULL,
    end_date        DATE,
    notes           TEXT,
    source_row_id   INTEGER,            -- original row id from source sheet for traceability
    synced_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_allocation_end_after_start
        CHECK (end_date IS NULL OR end_date > start_date)
);

-- Indexes for common query patterns
CREATE INDEX idx_employees_status      ON employees(status);
CREATE INDEX idx_employees_department  ON employees(department);
CREATE INDEX idx_projects_status       ON projects(status);
CREATE INDEX idx_allocations_employee  ON allocations(employee_id);
CREATE INDEX idx_allocations_project   ON allocations(project_code);
CREATE INDEX idx_allocations_dates     ON allocations(start_date, end_date);

-- ============================================================
-- Optional: sync_log table to track each sync run
-- ============================================================
CREATE TABLE sync_log (
    id              SERIAL PRIMARY KEY,
    sheet_name      VARCHAR(100) NOT NULL,
    run_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    rows_read       INTEGER      NOT NULL DEFAULT 0,
    rows_inserted   INTEGER      NOT NULL DEFAULT 0,
    rows_updated    INTEGER      NOT NULL DEFAULT 0,
    rows_rejected   INTEGER      NOT NULL DEFAULT 0,
    rejection_detail JSONB
);

-- ============================================================
-- Optional: error_logs table to track validation errors
-- ============================================================
CREATE TABLE error_logs (
    id          SERIAL PRIMARY KEY,
    source      VARCHAR(50)  NOT NULL,  -- ví dụ: 'validate'
    format      VARCHAR(20),            -- 'joined' | 'sheets' | NULL
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    summary     JSONB,
    errors      JSONB,
    raw_sample  JSONB                    -- một phần payload gốc để debug
);

CREATE INDEX idx_error_logs_source
    ON error_logs(source);

CREATE INDEX idx_error_logs_created_at
    ON error_logs(created_at DESC);

