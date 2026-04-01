# Dual-Mode Implementation Guide (FastAPI + Java/Tomcat)

This repository now supports a dual-mode backend split:

- Passenger traffic: Python FastAPI on `http://127.0.0.1:8000`
- Admin reporting traffic: Java servlet (WAR) on Tomcat at `http://127.0.0.1:8080/admin`
- Shared data layer: MySQL `airline_reservation`

## 1) Shared Database Configuration

Both runtimes must use the same environment values:

- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`

Python reads these from `backend/.env`.
Java reads these as OS environment variables.

On Windows PowerShell before starting Tomcat, set environment variables:

```powershell
$env:DB_USER="root"
$env:DB_PASSWORD="your_password"
$env:DB_HOST="localhost"
$env:DB_PORT="3306"
$env:DB_NAME="airline_reservation"
```

## 2) Passenger Backend (FastAPI)

From repository root:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --reload --port 8000
```

## 3) Admin Backend (Java/Tomcat)

### Build WAR

```powershell
cd admin-java
mvn clean package
```

Build output:

- `admin-java/target/admin.war`

### Deploy to Tomcat

Copy `admin.war` into Tomcat `webapps` directory.
Tomcat deploys it automatically to:

- `http://127.0.0.1:8080/admin`

Admin health endpoint:

- `GET http://127.0.0.1:8080/admin/health`

Admin dashboard summary endpoint:

- `GET http://127.0.0.1:8080/admin/dashboard/summary`

## 4) Frontend Configuration (Vite)

In `frontend/.env`:

```dotenv
VITE_PASSENGER_API_BASE_URL=http://127.0.0.1:8000
VITE_ADMIN_API_BASE_URL=http://127.0.0.1:8080/admin
```

`frontend/src/lib/api.js` is already configured to route:

- Passenger calls -> FastAPI
- Admin calls -> Tomcat servlet API

## 5) Run Frontend

```powershell
cd frontend
npm install
npm run dev
```

## 6) Verification Checklist

1. `GET http://127.0.0.1:8000/health` returns OK.
2. `GET http://127.0.0.1:8080/admin/health` returns OK.
3. Frontend login and passenger booking work.
4. Java admin summary endpoint returns booking/revenue stats from MySQL.

## 7) Notes on Data Integrity

- Keep triggers and integrity rules in `database/02_triggers.sql`.
- This ensures both Python and Java clients are constrained identically.
- Continue using normalized schema from `database/01_schema.sql`.
