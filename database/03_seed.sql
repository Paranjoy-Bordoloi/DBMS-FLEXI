USE airline_reservation;

INSERT INTO airline (name, code)
VALUES
('Air India', 'AIC'),
('IndiGo', 'IGO');

INSERT INTO airport (airport_code, name, city, country, timezone)
VALUES
('PNQ', 'Pune Airport', 'Pune', 'India', 'Asia/Kolkata'),
('DEL', 'Indira Gandhi International Airport', 'Delhi', 'India', 'Asia/Kolkata'),
('BOM', 'Chhatrapati Shivaji Maharaj International Airport', 'Mumbai', 'India', 'Asia/Kolkata'),
('BLR', 'Kempegowda International Airport', 'Bengaluru', 'India', 'Asia/Kolkata'),
('HYD', 'Rajiv Gandhi International Airport', 'Hyderabad', 'India', 'Asia/Kolkata'),
('MAA', 'Chennai International Airport', 'Chennai', 'India', 'Asia/Kolkata'),
('CCU', 'Netaji Subhas Chandra Bose International Airport', 'Kolkata', 'India', 'Asia/Kolkata'),
('GOI', 'Goa International Airport', 'Goa', 'India', 'Asia/Kolkata');

INSERT INTO route (origin_code, dest_code, distance_km, estimated_duration_minutes)
VALUES
('PNQ', 'DEL', 1170, 130),
('DEL', 'BOM', 1150, 125),
('BOM', 'BLR', 840, 110),
('BLR', 'PNQ', 735, 95),
('HYD', 'DEL', 1250, 145),
('MAA', 'BOM', 1035, 125),
('CCU', 'DEL', 1530, 150),
('GOI', 'PNQ', 360, 70),
('DEL', 'HYD', 1250, 145),
('PNQ', 'GOI', 360, 70);

INSERT INTO aircraft (registration_number, model, manufacturer, total_capacity, business_seats, economy_seats, airline_id)
VALUES
('VT-AX1', 'A320neo', 'Airbus', 180, 20, 160, 1),
('VT-BX2', 'B737-800', 'Boeing', 189, 12, 177, 2),
('VT-CX3', 'A321neo', 'Airbus', 200, 24, 176, 1),
('VT-DX4', 'B787-8', 'Boeing', 242, 30, 212, 1);

INSERT INTO flight (flight_number, route_id, aircraft_id, departure_time, arrival_time, base_price, status, available_seats)
VALUES
('AI201', 1, 1, '2026-03-15 08:00:00', '2026-03-15 10:10:00', 5200.00, 'Scheduled', 180),
('6E402', 2, 2, '2026-03-15 12:00:00', '2026-03-15 14:05:00', 4800.00, 'Scheduled', 189),
('AI301', 3, 1, '2026-03-15 16:00:00', '2026-03-15 17:50:00', 4300.00, 'Scheduled', 180),
('AI501', 4, 3, '2026-03-16 08:30:00', '2026-03-16 10:05:00', 3900.00, 'Scheduled', 200),
('AI511', 5, 4, '2026-03-16 11:00:00', '2026-03-16 13:25:00', 5600.00, 'Scheduled', 242),
('6E622', 6, 2, '2026-03-16 15:00:00', '2026-03-16 17:05:00', 4700.00, 'Scheduled', 189),
('AI701', 7, 3, '2026-03-17 06:20:00', '2026-03-17 08:50:00', 6100.00, 'Delayed', 200),
('6E105', 8, 2, '2026-03-17 09:30:00', '2026-03-17 10:40:00', 2800.00, 'Scheduled', 189),
('AI106', 9, 1, '2026-03-17 13:00:00', '2026-03-17 14:10:00', 2900.00, 'Scheduled', 180),
('AI910', 10, 4, '2026-03-18 07:15:00', '2026-03-18 09:40:00', 5750.00, 'Scheduled', 242),
('6E911', 11, 2, '2026-03-18 18:30:00', '2026-03-18 19:40:00', 2650.00, 'Scheduled', 189);

INSERT INTO passenger (first_name, last_name, email, phone, address, passport_number, frequent_flyer_number, age)
VALUES
('Paranjoy', 'Bordoloi', 'paranjoy@example.com', '9999000011', 'Pune, India', 'P1234567', 'FF1001', 20),
('Divyaansh', 'Parmar', 'divyaansh@example.com', '9999000022', 'Pune, India', 'P1234568', 'FF1002', 20),
('Parth', 'Giri', 'parth@example.com', '9999000033', 'Pune, India', 'P1234569', 'FF1003', 20),
('Aarav', 'Shah', 'aarav.shah@example.com', '9999000044', 'Mumbai, India', 'P2234561', 'FF1004', 29),
('Ira', 'Menon', 'ira.menon@example.com', '9999000055', 'Delhi, India', 'P2234562', 'FF1005', 31),
('Kabir', 'Sood', 'kabir.sood@example.com', '9999000066', 'Bengaluru, India', 'P2234563', 'FF1006', 27),
('Meera', 'Rao', 'meera.rao@example.com', '9999000077', 'Hyderabad, India', 'P2234564', 'FF1007', 33);

INSERT INTO employee (first_name, last_name, role, date_hired, email, phone, salary, license_number, language_skills, access_level)
VALUES
('Aman', 'Sharma', 'Pilot', '2022-01-01', 'aman.sharma@airline.com', '9000011111', 1800000.00, 'LIC1001', NULL, NULL),
('Nina', 'Davis', 'CabinCrew', '2023-06-15', 'nina.davis@airline.com', '9000022222', 650000.00, NULL, 'English,Hindi', NULL),
('Rohit', 'Mehta', 'AdminStaff', '2021-03-11', 'rohit.mehta@airline.com', '9000033333', 900000.00, NULL, NULL, 'OperationsAdmin');

INSERT INTO app_user (passenger_id, employee_id, email, password_hash, role)
VALUES
(1, NULL, 'paranjoy@example.com', '$2b$12$placeholderhashforpassenger1', 'Passenger'),
(2, NULL, 'divyaansh@example.com', '$2b$12$placeholderhashforpassenger2', 'Passenger'),
(3, NULL, 'parth@example.com', '$2b$12$placeholderhashforpassenger3', 'Passenger'),
(NULL, 3, 'admin@airline.com', '$2b$12$placeholderhashforadminuser', 'Admin');

INSERT INTO crew_assignment (employee_id, flight_id, role_in_flight)
VALUES
(1, 1, 'Pilot'),
(2, 1, 'CabinCrew'),
(1, 2, 'Co-Pilot');

INSERT INTO booking (booking_reference, passenger_id, flight_id, seat_number, class_type, status, total_amount)
VALUES
('PNR00000001', 1, 1, '12A', 'Economy', 'Confirmed', 6200.00),
('PNR00000002', 2, 1, '12B', 'Economy', 'Pending', 6200.00),
('PNR00000003', 3, 2, '14A', 'Economy', 'Confirmed', 5600.00),
('PNR00000004', 4, 3, '15C', 'Economy', 'Confirmed', 4950.00),
('PNR00000005', 5, 4, '6A', 'Business', 'Confirmed', 8900.00),
('PNR00000006', 6, 5, '10D', 'Economy', 'Pending', 6750.00),
('PNR00000007', 7, 6, '11F', 'Economy', 'Confirmed', 5300.00),
('PNR00000008', 8, 8, '9C', 'Economy', 'Cancelled', 3600.00);

INSERT INTO payment (booking_id, amount, payment_method, transaction_reference, payment_status)
VALUES
(1, 6200.00, 'CreditCard', 'TXN-2026-0001', 'Success'),
(3, 5600.00, 'UPI', 'TXN-2026-0003', 'Success'),
(4, 4950.00, 'DebitCard', 'TXN-2026-0004', 'Success'),
(5, 8900.00, 'CreditCard', 'TXN-2026-0005', 'Success'),
(7, 5300.00, 'NetBanking', 'TXN-2026-0007', 'Success'),
(8, 3600.00, 'UPI', 'TXN-2026-0008', 'Refunded');
