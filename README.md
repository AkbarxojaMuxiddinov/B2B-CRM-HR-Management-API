# B2B CRM va HR Management API

Django REST API for managing company departments, employees, attendance, and payroll. The project uses JWT authentication, role-based permissions, PostgreSQL, Redis, and Celery.

## Run with Docker

1. Copy `.env.example` to `.env` and set a private Django secret and PostgreSQL password.
2. Start the services:

   ```powershell
   docker compose up --build
   ```

The API will be available at `http://localhost:8000`. Swagger documentation is at `http://localhost:8000/api/docs/`.

Docker Compose starts PostgreSQL, Redis, the Django web service, a Celery worker, Celery Beat, and a one-time migration service.

## Main API routes

- `POST /api/v1/auth/token/` — get access and refresh tokens.
- `POST /api/v1/auth/token/refresh/` — refresh an access token.
- `/api/v1/departments/` — manage departments.
- `/api/v1/users/` — manage users.
- `/api/v1/attendance/` — manage attendance records.
- `POST /api/v1/attendance/check_in/` — record today's check-in.
- `POST /api/v1/attendance/check_out/` — record today's check-out.
- `/api/v1/payrolls/` — manage payroll records.

Business API routes require a JWT access token in the `Authorization: Bearer <token>` header. Admins have full access, HR users manage company records except admin accounts, and employees can access their own records.

## Monthly payroll task

Celery Beat schedules payroll generation for the previous month at 00:10 on the first day of each month in the configured timezone. The task prorates monthly base salary by attended weekdays over scheduled weekdays. Weekends are excluded; public holidays are not currently configured. Existing payroll records are left unchanged.
