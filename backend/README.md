# Backend API

This service now includes core passenger and admin flows for the Airline Reservation System.

## Implemented

- Passenger registration + login (`FR-01`)
- Flight search with sorting (`FR-02`)
- Seat lock + booking + payment record (`FR-03`, `FR-04`)
- Booking retrieval, ticket view, cancellation + refund (`FR-05`)
- Admin route/aircraft/flight management + manifest + dashboard (`FR-06`, `FR-07`, `FR-08`)
- Integrity and business rule handling through DB constraints/triggers (`FR-09`)

## Folder structure

- `app/config.py`: environment settings
- `app/database.py`: SQLAlchemy engine/session
- `app/models.py`: ORM models (initial subset)
- `app/schemas.py`: request/response schemas
- `app/security.py`: password hashing + JWT
- `app/main.py`: FastAPI routes

## Setup

1. Install dependencies:

```powershell
pip install -r backend/requirements.txt
```

2. Create `.env` in `backend/`:

```env
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=airline_reservation
JWT_SECRET=replace-with-strong-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

3. Start server from workspace root:

```powershell
uvicorn backend.app.main:app --reload
```

4. Open docs:

- `http://127.0.0.1:8000/docs`

## Auth Usage (Postman)

1. Call `POST /auth/login` and copy `access_token`.
2. For protected endpoints, send header:

```text
Authorization: Bearer <access_token>
```

3. Verify token identity with:

- `GET /auth/me`

## Notes

- `/admin/*` endpoints require role `Admin`.
- `/bookings/*` endpoints require role `Passenger` or `Admin`, with ownership checks for passenger users.
