# Candidate Data Pipeline API

## 1. Giới thiệu

Đây là một hệ thống **Data Pipeline API** được xây dựng bằng FastAPI để tiếp nhận, kiểm tra, làm sạch và đồng bộ dữ liệu từ các nguồn bên ngoài (Google Sheets hoặc các dịch vụ trên Google Cloud) vào **PostgreSQL**.

Hệ thống được tích hợp với **n8n** để tự động hóa quy trình xử lý dữ liệu.

Hệ thống nhận dữ liệu dạng JSON và xử lý theo pipeline gồm các bước:

1.  Schema Validation -- kiểm tra cấu trúc dữ liệu
2.  Business Validation -- kiểm tra logic nghiệp vụ
3.  Data Cleaning -- chuẩn hóa dữ liệu
4.  Data Quality Check -- đánh giá chất lượng dữ liệu
5.  Database Sync -- đồng bộ dữ liệu vào PostgreSQL

Các bản ghi không hợp lệ có thể được lưu vào bảng **error_logs** để phân
tích sau.

---

## 2. Kiến trúc hệ thống

    Nguồn dữ liệu (Google Sheets / API)
            │
            ▼
            n8n
            │
            ▼
    Candidate Data Pipeline API
            │
            ├── Schema Validation
            ├── Business Validation
            ├── Data Cleaning
            ├── Data Quality Check
            └── Database Sync
                    │
                    ▼
                PostgreSQL

Pipeline giúp đảm bảo dữ liệu được kiểm tra và làm sạch trước khi lưu
vào database.

---

## 3. Công nghệ sử dụng

### Backend

- Python 3.11
- FastAPI
- Uvicorn

### Database

- PostgreSQL

### Orchestration

- n8n

### Infrastructure

- Docker
- Docker Compose

### Code Quality Tools

Python: Black - isort - Flake8 - pydocstyle - pre-commit

JavaScript: ESLint - Prettier - Jest

---

## 4. Cấu trúc dự án

    .
    ├── candidate/
    │       schema.sql
    │
    ├── cleaning/
    │       data_cleaning.py
    │
    ├── data/
    │     nodes/
    │     torage/
    │
    │
    ├── database/
    │       db_sync.py
    │       error_logs.py
    │
    ├── quality/
    │       data_quality.py
    │           engine/
    │                quality_checker.py
    │           rules/
    │               allocation_quality_rules.py
    │               employee_quality_rules.py
    │               project_quality_rules.py
    │
    ├── validation/
    │       schema_validation.py
    │       business_validation.py
    │           rules/
    │               allocations_rules.py
    │                employees_rules.py
    │                projects_rules.py
    │
    ├── server.py
    ├── Dockerfile
    ├── docker-compose.yml
    ├── requirements.txt
    ├── pyproject.toml
    ├── .pre-commit-config.yaml
    ├── eslint.config.cjs
    ├── prettier.config.cjs
    └── package.json

---

## 5. Cấu hình môi trường

Tạo file `.env`:

    POSTGRES_HOST=your_host
    POSTGRES_PORT=5432
    POSTGRES_DB=your_database
    POSTGRES_USER=your_user
    POSTGRES_PASSWORD=your_password

    API_PORT=3000

---

## 6. Cài đặt

### Tạo môi trường Python

```bash
python -m venv .venv
```

Kích hoạt môi trường:

Windows

```bash
.venv\Scripts\activate
```

Cài đặt thư viện:

```bash
pip install -r requirements.txt
```

---

### Cài đặt Node tooling

```bash
npm install
```

Cài đặt ESLint, Prettier và Jest.

---

### Cài đặt pre-commit

```bash
pre-commit install
```

Chạy thủ công:

```bash
pre-commit run --all-files
```

---

## 7. Chạy hệ thống bằng Docker

```bash
docker-compose up -d
```

Các service:

Service Port

---

API 3000
n8n 5678
PostgreSQL 5432

---

## 8. API chính

### Health Check

    GET /health

Response

    {
      "status": "ok"
    }

---

### Schema Validation

    POST /api/schema-validate

Kiểm tra cấu trúc dữ liệu đầu vào.

---

### Business Validation

    POST /api/business-validate

Áp dụng các rule nghiệp vụ:

- trùng employee_id
- trùng project_code
- kiểm tra foreign key
- kiểm tra logic ngày tháng
- kiểm tra allocation %

---

### Data Cleaning

    POST /api/data-cleaning

Chuẩn hóa dữ liệu:

- trim string
- chuẩn hóa date
- convert kiểu dữ liệu

---

### Data Quality

    POST /api/data-quality

Chạy các rule đánh giá chất lượng dữ liệu.

---

### Database Sync

    POST /api/db-sync

Đồng bộ dữ liệu vào PostgreSQL.

---

### Error Logs

    POST /api/error-logs

Lưu các bản ghi lỗi vào bảng error_logs.

---

## 9. Workflow n8n

**Luồng tổng quát**

```text
Data Source (Google Sheets)
        │
        ▼
Data Merge (n8n)
        │
        ▼
Schema Validation (API)
        │
        ├── Invalid Data → Error Logs (API + PostgreSQL)
        │
        ▼
Business Validation (API)
        │
        ▼
Data Cleaning (API)
        │
        ▼
Data Quality Check (API)
        │
        ▼
Database Sync (API → PostgreSQL)
```

Pipeline xử lý dữ liệu được tự động hóa bằng **n8n** và các API trong hệ thống này.

<p align="center">
  <img src="images/n8n-workflow-1.png" alt="n8n workflow 1" width="48%">
  <img src="images/n8n-workflow-2.png" alt="n8n workflow 2" width="48%">
</p>

---

## 10. Logging & Monitoring

- API log (request / error) được ghi bằng `logging` trong `server.py`.
- Bảng `sync_log` lưu:
  - `sheet_name`
  - `run_at`
  - `rows_read`
  - `rows_inserted`
  - `rows_updated`
  - `rows_rejected`
  - `rejection_detail` (JSONB – có thể lưu lý do reject tổng hợp)
- Bảng `error_logs` lưu:
  - `source` – ví dụ: `schema_validation`, `business_validation`, `check`
  - `format` – `sheets`, `joined`, ...
  - `summary` – thống kê tổng lỗi theo sheet
  - `errors` – chi tiết lỗi theo từng dòng
  - `raw_sample` – 1 bản ghi đại diện để debug nhanh

Khuyến nghị:

- Dùng `source` + `created_at` để filter log theo ngày, theo pipeline step.
- Có thể build dashboard (Metabase / Grafana) đọc từ `sync_log` và `error_logs`.

---

## 11. Code Quality

### Python

- Format: **Black**
- Sắp xếp import: **isort**
- Lint: **Flake8**
- Docstring: **pydocstyle** (style Google, nhưng đã nới bớt rule quá chặt)

### JavaScript / Nodejs

- Format: **Prettier**
- Lint: **ESLint** (flat config `eslint.config.cjs`)

---

## 12. Hướng phát triển tương lai

- Bổ sung UI hoặc dashboard cho:
  - `sync_log` (theo thời gian, theo sheet).
  - `error_logs` (top lỗi phổ biến, theo nguồn).
- Thêm layer **authorization** cho API (API key / OAuth tùy yêu cầu).
- Chuẩn hóa thêm test tự động (pytest + Jest) và CI/CD (GitHub Actions / GitLab CI).
- Bổ sung metric (Prometheus) và health check nâng cao (kiểm tra kết nối DB, migration, v.v.).
