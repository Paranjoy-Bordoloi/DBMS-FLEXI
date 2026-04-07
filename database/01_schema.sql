CREATE DATABASE IF NOT EXISTS airline_reservation;
USE airline_reservation;

CREATE TABLE airline (
    airline_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(3) NOT NULL UNIQUE
);

CREATE TABLE airport (
    airport_code VARCHAR(3) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    country VARCHAR(50) NOT NULL,
    timezone VARCHAR(50) NOT NULL
);

CREATE TABLE route (
    route_id INT AUTO_INCREMENT PRIMARY KEY,
    origin_code VARCHAR(3) NOT NULL,
    dest_code VARCHAR(3) NOT NULL,
    distance_km INT NOT NULL,
    estimated_duration_minutes INT NOT NULL,
    CONSTRAINT fk_route_origin FOREIGN KEY (origin_code) REFERENCES airport (airport_code),
    CONSTRAINT fk_route_dest FOREIGN KEY (dest_code) REFERENCES airport (airport_code),
    CONSTRAINT chk_route_distinct CHECK (origin_code <> dest_code)
);

CREATE TABLE aircraft (
    aircraft_id INT AUTO_INCREMENT PRIMARY KEY,
    registration_number VARCHAR(20) NOT NULL UNIQUE,
    model VARCHAR(50) NOT NULL,
    manufacturer VARCHAR(50) NOT NULL,
    total_capacity INT NOT NULL,
    business_seats INT NOT NULL,
    economy_seats INT NOT NULL,
    airline_id INT NOT NULL,
    CONSTRAINT fk_aircraft_airline FOREIGN KEY (airline_id) REFERENCES airline (airline_id),
    CONSTRAINT chk_aircraft_capacity CHECK (total_capacity > 0),
    CONSTRAINT chk_aircraft_seat_split CHECK (business_seats >= 0 AND economy_seats >= 0 AND business_seats + economy_seats <= total_capacity)
);

CREATE TABLE flight (
    flight_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    flight_number VARCHAR(10) NOT NULL,
    route_id INT NOT NULL,
    aircraft_id INT NOT NULL,
    departure_time DATETIME NOT NULL,
    arrival_time DATETIME NOT NULL,
    base_price DECIMAL(10, 2) NOT NULL,
    status ENUM('Scheduled', 'Delayed', 'Cancelled', 'Departed') NOT NULL DEFAULT 'Scheduled',
    available_seats INT NOT NULL,
    CONSTRAINT fk_flight_route FOREIGN KEY (route_id) REFERENCES route (route_id),
    CONSTRAINT fk_flight_aircraft FOREIGN KEY (aircraft_id) REFERENCES aircraft (aircraft_id),
    CONSTRAINT chk_flight_time CHECK (departure_time < arrival_time),
    CONSTRAINT chk_flight_price CHECK (base_price >= 0),
    CONSTRAINT chk_flight_available_seats CHECK (available_seats >= 0)
);

CREATE INDEX idx_flight_departure_time ON flight (departure_time);
CREATE INDEX idx_flight_route ON flight (route_id);
CREATE INDEX idx_flight_status ON flight (status);

CREATE TABLE passenger (
    passenger_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    passport_number VARCHAR(20) NOT NULL UNIQUE,
    date_of_birth DATE NOT NULL,
    address VARCHAR(255),
    frequent_flyer_number VARCHAR(30) UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE app_user (
    user_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    passenger_id BIGINT NULL,
    employee_id BIGINT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('Passenger', 'Admin', 'Crew') NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_app_user_passenger FOREIGN KEY (passenger_id) REFERENCES passenger (passenger_id)
);

CREATE TABLE employee (
    employee_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    role ENUM('Pilot', 'CabinCrew', 'AdminStaff') NOT NULL,
    date_hired DATE NOT NULL,
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(20),
    salary DECIMAL(12, 2),
    license_number VARCHAR(30),
    language_skills VARCHAR(255),
    access_level VARCHAR(50)
);

ALTER TABLE app_user
ADD CONSTRAINT fk_app_user_employee FOREIGN KEY (employee_id) REFERENCES employee (employee_id);

CREATE TABLE crew_assignment (
    assignment_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    employee_id BIGINT NOT NULL,
    flight_id BIGINT NOT NULL,
    role_in_flight ENUM('Pilot', 'Co-Pilot', 'CabinCrew', 'HeadSteward') NOT NULL,
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_crew_employee FOREIGN KEY (employee_id) REFERENCES employee (employee_id),
    CONSTRAINT fk_crew_flight FOREIGN KEY (flight_id) REFERENCES flight (flight_id),
    CONSTRAINT uq_crew_unique_assignment UNIQUE (employee_id, flight_id)
);

CREATE TABLE booking (
    booking_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    booking_reference VARCHAR(12) NOT NULL UNIQUE,
    passenger_id BIGINT NOT NULL,
    flight_id BIGINT NOT NULL,
    booking_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    seat_number VARCHAR(5) NOT NULL,
    class_type ENUM('Economy', 'Business', 'First') NOT NULL,
    status ENUM('Pending', 'Confirmed', 'Cancelled') NOT NULL DEFAULT 'Pending',
    total_amount DECIMAL(10, 2) NOT NULL,
    cancellation_time DATETIME NULL,
    CONSTRAINT fk_booking_passenger FOREIGN KEY (passenger_id) REFERENCES passenger (passenger_id),
    CONSTRAINT fk_booking_flight FOREIGN KEY (flight_id) REFERENCES flight (flight_id),
    CONSTRAINT uq_flight_seat UNIQUE (flight_id, seat_number),
    CONSTRAINT chk_booking_amount CHECK (total_amount >= 0)
);

CREATE INDEX idx_booking_pnr_lookup ON booking (booking_reference);
CREATE INDEX idx_booking_passenger ON booking (passenger_id);
CREATE INDEX idx_booking_flight ON booking (flight_id);

CREATE TABLE payment (
    payment_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    booking_id BIGINT NOT NULL UNIQUE,
    amount DECIMAL(10, 2) NOT NULL,
    payment_method ENUM('CreditCard', 'DebitCard', 'UPI', 'NetBanking', 'Wallet') NOT NULL,
    transaction_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    transaction_reference VARCHAR(50) NOT NULL UNIQUE,
    payment_status ENUM('Pending', 'Success', 'Failed', 'Refunded') NOT NULL DEFAULT 'Pending',
    CONSTRAINT fk_payment_booking FOREIGN KEY (booking_id) REFERENCES booking (booking_id),
    CONSTRAINT chk_payment_amount CHECK (amount >= 0)
);

CREATE TABLE seat_lock (
    lock_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    flight_id BIGINT NOT NULL,
    seat_number VARCHAR(5) NOT NULL,
    locked_by_user_id BIGINT NOT NULL,
    lock_created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    CONSTRAINT fk_lock_flight FOREIGN KEY (flight_id) REFERENCES flight (flight_id),
    CONSTRAINT fk_lock_user FOREIGN KEY (locked_by_user_id) REFERENCES app_user (user_id),
    CONSTRAINT uq_active_seat_lock UNIQUE (flight_id, seat_number)
);

CREATE INDEX idx_seat_lock_expires_at ON seat_lock (expires_at);

CREATE TABLE notification (
    notification_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    passenger_id BIGINT NOT NULL,
    booking_id BIGINT NULL,
    channel ENUM('Email', 'SMS') NOT NULL,
    message_body TEXT NOT NULL,
    notification_status ENUM('Queued', 'Sent', 'Failed') NOT NULL DEFAULT 'Queued',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at DATETIME NULL,
    CONSTRAINT fk_notification_passenger FOREIGN KEY (passenger_id) REFERENCES passenger (passenger_id),
    CONSTRAINT fk_notification_booking FOREIGN KEY (booking_id) REFERENCES booking (booking_id)
);

CREATE TABLE refund (
    refund_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    booking_id BIGINT NOT NULL UNIQUE,
    refund_amount DECIMAL(10, 2) NOT NULL,
    reason VARCHAR(255),
    processed_at DATETIME,
    refund_status ENUM('Pending', 'Processed', 'Rejected') NOT NULL DEFAULT 'Pending',
    CONSTRAINT fk_refund_booking FOREIGN KEY (booking_id) REFERENCES booking (booking_id),
    CONSTRAINT chk_refund_amount CHECK (refund_amount >= 0)
);

CREATE TABLE operational_audit_log (
    audit_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(50) NOT NULL,
    actor_user_id BIGINT NOT NULL,
    action_status VARCHAR(20) NOT NULL,
    action_notes VARCHAR(255),
    metadata_json VARCHAR(2000),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_actor_user FOREIGN KEY (actor_user_id) REFERENCES app_user (user_id)
);

CREATE INDEX idx_airport_city ON airport (city);
CREATE INDEX idx_route_origin_dest ON route (origin_code, dest_code);
CREATE INDEX idx_audit_created_at ON operational_audit_log (created_at);
CREATE INDEX idx_audit_entity ON operational_audit_log (entity_type, entity_id);
