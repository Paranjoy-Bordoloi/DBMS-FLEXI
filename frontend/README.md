# Frontend (Rudimentary MVP)

This frontend is a basic passenger console wired to the Airline Reservation backend.

## Implemented Screens

- Login
- Flight search
- Seat lock + booking creation
- Booking retrieval + cancellation

## Setup

1. Create env file:

```bash
copy .env.example .env
```

2. Install dependencies:

```bash
npm install
```

3. Start dev server:

```bash
npm run dev
```

## Backend Requirement

Backend must be running at `VITE_API_BASE_URL` (default `http://127.0.0.1:8000`).

## Notes

- Protected routes use token stored in localStorage.
- After login, frontend calls `/auth/me` and auto-populates user/passenger IDs for booking.
