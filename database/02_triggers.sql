USE airline_reservation;

DELIMITER $$

CREATE TRIGGER tr_flight_before_insert
BEFORE INSERT ON flight
FOR EACH ROW
BEGIN
    DECLARE overlapping_count INT DEFAULT 0;
    DECLARE aircraft_capacity INT DEFAULT 0;

    IF NEW.departure_time >= NEW.arrival_time THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Departure time must be earlier than arrival time.';
    END IF;

    SELECT COUNT(*) INTO overlapping_count
    FROM flight f
    WHERE f.aircraft_id = NEW.aircraft_id
      AND NEW.departure_time < f.arrival_time
      AND NEW.arrival_time > f.departure_time
      AND f.status <> 'Cancelled';

    IF overlapping_count > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Aircraft is already assigned to an overlapping flight time block.';
    END IF;

    SELECT total_capacity INTO aircraft_capacity
    FROM aircraft
    WHERE aircraft_id = NEW.aircraft_id;

    IF aircraft_capacity IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid aircraft assignment.';
    END IF;

    IF NEW.available_seats > aircraft_capacity THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Available seats cannot exceed aircraft total capacity.';
    END IF;
END$$

CREATE TRIGGER tr_flight_before_update
BEFORE UPDATE ON flight
FOR EACH ROW
BEGIN
    DECLARE overlapping_count INT DEFAULT 0;
    DECLARE aircraft_capacity INT DEFAULT 0;

    IF NEW.departure_time >= NEW.arrival_time THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Departure time must be earlier than arrival time.';
    END IF;

    SELECT COUNT(*) INTO overlapping_count
    FROM flight f
    WHERE f.aircraft_id = NEW.aircraft_id
      AND f.flight_id <> NEW.flight_id
      AND NEW.departure_time < f.arrival_time
      AND NEW.arrival_time > f.departure_time
      AND f.status <> 'Cancelled';

    IF overlapping_count > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Aircraft is already assigned to an overlapping flight time block.';
    END IF;

    SELECT total_capacity INTO aircraft_capacity
    FROM aircraft
    WHERE aircraft_id = NEW.aircraft_id;

    IF NEW.available_seats > aircraft_capacity THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Available seats cannot exceed aircraft total capacity.';
    END IF;
END$$

CREATE TRIGGER tr_booking_before_insert
BEFORE INSERT ON booking
FOR EACH ROW
BEGIN
    DECLARE current_bookings INT DEFAULT 0;
    DECLARE aircraft_capacity INT DEFAULT 0;

    SELECT a.total_capacity INTO aircraft_capacity
    FROM flight f
    JOIN aircraft a ON a.aircraft_id = f.aircraft_id
    WHERE f.flight_id = NEW.flight_id;

    IF aircraft_capacity IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Flight does not exist or has no valid aircraft.';
    END IF;

    SELECT COUNT(*) INTO current_bookings
    FROM booking b
    WHERE b.flight_id = NEW.flight_id
      AND b.status IN ('Pending', 'Confirmed');

    IF current_bookings >= aircraft_capacity THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot create booking: flight capacity reached.';
    END IF;
END$$

CREATE TRIGGER tr_booking_before_update
BEFORE UPDATE ON booking
FOR EACH ROW
BEGIN
    DECLARE current_bookings INT DEFAULT 0;
    DECLARE aircraft_capacity INT DEFAULT 0;

    IF NEW.flight_id <> OLD.flight_id OR NEW.status <> OLD.status THEN
        SELECT a.total_capacity INTO aircraft_capacity
        FROM flight f
        JOIN aircraft a ON a.aircraft_id = f.aircraft_id
        WHERE f.flight_id = NEW.flight_id;

        SELECT COUNT(*) INTO current_bookings
        FROM booking b
        WHERE b.flight_id = NEW.flight_id
          AND b.status IN ('Pending', 'Confirmed')
          AND b.booking_id <> OLD.booking_id;

        IF NEW.status IN ('Pending', 'Confirmed') AND current_bookings >= aircraft_capacity THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot update booking: flight capacity reached.';
        END IF;
    END IF;
END$$

CREATE TRIGGER tr_booking_after_insert
AFTER INSERT ON booking
FOR EACH ROW
BEGIN
    IF NEW.status IN ('Pending', 'Confirmed') THEN
        UPDATE flight
        SET available_seats = available_seats - 1
        WHERE flight_id = NEW.flight_id
          AND available_seats > 0;
    END IF;
END$$

CREATE TRIGGER tr_booking_after_update
AFTER UPDATE ON booking
FOR EACH ROW
BEGIN
    IF OLD.status IN ('Pending', 'Confirmed') AND NEW.status = 'Cancelled' THEN
        UPDATE flight
        SET available_seats = available_seats + 1
        WHERE flight_id = NEW.flight_id;
    ELSEIF OLD.status = 'Cancelled' AND NEW.status IN ('Pending', 'Confirmed') THEN
        UPDATE flight
        SET available_seats = available_seats - 1
        WHERE flight_id = NEW.flight_id
          AND available_seats > 0;
    END IF;
END$$

CREATE TRIGGER tr_seat_lock_before_insert
BEFORE INSERT ON seat_lock
FOR EACH ROW
BEGIN
    DECLARE existing_booking_count INT DEFAULT 0;

    IF NEW.expires_at <= NOW() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Seat lock expiration must be in the future.';
    END IF;

    SELECT COUNT(*) INTO existing_booking_count
    FROM booking b
    WHERE b.flight_id = NEW.flight_id
      AND b.seat_number = NEW.seat_number
      AND b.status IN ('Pending', 'Confirmed');

    IF existing_booking_count > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Seat already booked and cannot be locked.';
    END IF;
END$$

CREATE PROCEDURE sp_clear_expired_seat_locks()
BEGIN
    DELETE FROM seat_lock
    WHERE expires_at <= NOW();
END$$

DELIMITER ;
