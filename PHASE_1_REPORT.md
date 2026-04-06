# Phase 1 Report

## Title
Airline Reservation System: Database Design, Normalization, and Initial Implementation

## 1. Objective

The goal of the first phase was to design a reliable airline reservation database and implement the base application layers needed for passenger booking, admin reporting, and data integrity.

## 2. System Scope

The system covers:
- passenger registration and authentication
- flight search and airport lookup
- booking creation, ticket retrieval, and cancellation
- optional seat locking
- refund processing
- admin dashboard reporting
- live flight import support

## 3. Functional Requirements Covered

- FR-01: Passenger registration and login
- FR-02: Flight search with sorting
- FR-03: Seat lock support
- FR-04: Booking creation and payment record
- FR-05: Booking retrieval, ticket view, and cancellation
- FR-06: Route/aircraft/flight administration
- FR-07: Booking manifest reporting
- FR-08: Dashboard summary reporting
- FR-09: Integrity constraints and business rules
- FR-10: Search and lookup performance through indexes

## 4. Functional Dependencies

The following functional dependencies guided the schema design and normalization work.

### Airline
- `airline_id -> name, code`
- `code -> airline_id, name`

### Airport
- `airport_code -> name, city, country, timezone`

### Route
- `route_id -> origin_code, dest_code, distance_km, estimated_duration_minutes`
- `(origin_code, dest_code) -> distance_km, estimated_duration_minutes`

### Aircraft
- `aircraft_id -> registration_number, model, manufacturer, total_capacity, business_seats, economy_seats, airline_id`
- `registration_number -> aircraft_id, model, manufacturer, total_capacity, business_seats, economy_seats, airline_id`

### Passenger
- `passenger_id -> first_name, last_name, email, phone, passport_number, date_of_birth, address, frequent_flyer_number`
- `email -> passenger_id, first_name, last_name, phone, passport_number, date_of_birth, address, frequent_flyer_number`
- `passport_number -> passenger_id, first_name, last_name, email, phone, date_of_birth, address, frequent_flyer_number`

### App User
- `user_id -> passenger_id, employee_id, email, password_hash, role, is_active, created_at`
- `email -> user_id, passenger_id, employee_id, password_hash, role, is_active, created_at`

### Flight
- `flight_id -> flight_number, route_id, aircraft_id, departure_time, arrival_time, base_price, status, available_seats`
- `(flight_number, departure_time) -> route_id, aircraft_id, arrival_time, base_price, status, available_seats`

### Booking
- `booking_id -> booking_reference, passenger_id, flight_id, booking_date, seat_number, class_type, status, total_amount, cancellation_time`
- `booking_reference -> booking_id, passenger_id, flight_id, booking_date, seat_number, class_type, status, total_amount, cancellation_time`
- `(flight_id, seat_number) -> booking_id`

### Payment
- `payment_id -> booking_id, amount, payment_method, transaction_date, transaction_reference, payment_status`
- `booking_id -> payment_id, amount, payment_method, transaction_date, transaction_reference, payment_status`
- `transaction_reference -> payment_id, booking_id, amount, payment_method, transaction_date, payment_status`

### Seat Lock
- `lock_id -> flight_id, seat_number, locked_by_user_id, lock_created_at, expires_at`
- `(flight_id, seat_number) -> lock_id, locked_by_user_id, lock_created_at, expires_at`

### Refund
- `refund_id -> booking_id, refund_amount, reason, processed_at, refund_status`
- `booking_id -> refund_id, refund_amount, reason, processed_at, refund_status`

## 5. Normalization to 3NF

### 1NF
The design was brought to 1NF by ensuring:
- all attributes are atomic
- no repeating groups
- no multivalued fields stored inside one column

Examples:
- airport details are stored one airport per row
- passenger details are stored in a separate passenger table
- booking and payment details are stored separately

### 2NF
The schema avoids partial dependency by using surrogate primary keys and by splitting entities into separate tables.

Examples:
- flight details are not mixed into booking records
- passenger details are not stored in booking records
- aircraft details are not stored in flight records beyond foreign keys

### 3NF
The schema removes transitive dependency by ensuring non-key attributes depend only on the key and not on other non-key attributes.

Examples:
- route data is stored in `route`, not repeated in `flight`
- airport details are stored in `airport`, not repeated in `route`
- airline details are stored in `airline`, not repeated in `aircraft`
- payment details are stored in `payment`, not repeated in `booking`
- refund details are stored in `refund`, not repeated in `booking`

## 6. Anomalies Found and Corrected

### Insertion Anomaly
Problem:
- If flight, airport, and airline data were kept in one table, inserting a booking would require repeated flight and airport data.

Fix:
- Split the schema into master and transactional tables.
- Airports, airlines, aircraft, and routes are stored independently.

### Update Anomaly
Problem:
- Changing airport or airline details in a denormalized table would require updating many rows.

Fix:
- Airport, airline, and aircraft details are normalized into separate master tables.
- One update changes the master record for all dependent rows.

### Deletion Anomaly
Problem:
- Deleting the last booking could accidentally delete flight or passenger information in a combined table.

Fix:
- Transactional tables are separated from master data.
- Cascading behavior is controlled through keys and application logic.

### Seat Conflict Anomaly
Problem:
- Multiple bookings could try to reserve the same seat.

Fix:
- Unique constraint on `(flight_id, seat_number)` in booking.
- Seat lock table temporarily reserves seats before booking.

### Schedule Overlap Anomaly
Problem:
- The same aircraft could be assigned to overlapping flights.

Fix:
- Trigger logic checks overlapping departure and arrival windows for the same aircraft.

## 7. Why the Design Is Efficient

- Search performance is improved with indexes on departure time, route, booking reference, and seat lock expiry.
- Integrity rules are enforced at the database level using constraints and triggers.
- Dual backend architecture separates passenger transactions from admin reporting.

## 8. Functional Dependencies and Design Decisions

The dependencies directly shaped the schema:
- airports, airlines, and aircraft were separated to remove repetition
- routes were isolated because they depend on origin and destination airport pairs
- bookings depend on passenger and flight, but not the reverse
- payments and refunds are linked to bookings but stored separately to avoid transitive data
- seat locks are a separate operational entity to support temporary reservation without permanent booking

## 9. Technology Choices

### Python + FastAPI
Used for:
- passenger authentication
- flight search APIs
- booking and cancellation workflows
- seat lock handling
- integration with SQLAlchemy and MySQL

### Java + Tomcat
Used for:
- admin dashboard reporting
- servlet-based deployment
- JDBC database access
- WAR packaging for admin reporting

### Why both were used
The project demonstrates two application styles:
- a modern Python API for passenger-facing transactional operations
- a classic Java servlet backend for admin/reporting operations

This helps show separation of concerns and supports a dual-mode architecture while keeping the database shared.

## 10. Implementation Changes Made in Phase 1

- designed and implemented the MySQL schema
- added triggers for overlapping flights, capacity rules, and seat locks
- added seed data for airports, airlines, routes, flights, passengers, and bookings
- built the FastAPI backend for passenger and admin APIs
- created the React frontend for passenger operations
- added the Java/Tomcat admin backend
- added live flight import support using AeroDataBox through RapidAPI
- added startup and smoke test scripts

## 11. Outcome

The first phase produced a working database-centered airline reservation platform with a normalized schema, enforced constraints, live schedule import support, and a working dual-backend application stack.

## 12. Suggested Next Steps

- expand live flight ingestion to a scheduled background task
- add more admin CRUD screens
- improve reporting with charts and filters
- add seat-map visualization
- add automated tests for booking and cancellation flows
