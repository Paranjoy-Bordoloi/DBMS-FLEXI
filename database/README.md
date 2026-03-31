# Database Setup (Step 1)

This folder contains the first implementation phase of the Airline Reservation System database.

## Files

- `01_schema.sql`: Core tables, keys, constraints, and indexes.
- `02_triggers.sql`: Business-rule triggers and maintenance procedure.
- `03_seed.sql`: Initial sample data for testing.

## Requirements

- MySQL 8.0+

## Run Order

```sql
SOURCE database/01_schema.sql;
SOURCE database/02_triggers.sql;
SOURCE database/03_seed.sql;
```

## Covered Requirements

- FR-01 to FR-08 base data model support.
- FR-09 integrity constraints:
  - No overlapping schedules for same aircraft.
  - Booking capacity cannot exceed aircraft seats.
  - Flight departure must be earlier than arrival.
  - Unique seat per flight.
- FR-10 performance baseline:
  - Indexes on common lookup and search fields.

## Notes

- `seat_lock` table supports 10-minute temporary seat hold flow.
- `sp_clear_expired_seat_locks()` can be run by a scheduler job every minute.
- Password values in seed data are placeholders and must be replaced by real bcrypt hashes in application setup.
