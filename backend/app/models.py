from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Airline(Base):
    __tablename__ = 'airline'

    airline_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)


class Passenger(Base):
    __tablename__ = 'passenger'

    passenger_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    passport_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    date_of_birth: Mapped[Date] = mapped_column(Date, nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    frequent_flyer_number: Mapped[str | None] = mapped_column(String(30), nullable=True, unique=True)

    user = relationship('AppUser', back_populates='passenger', uselist=False)


class AppUser(Base):
    __tablename__ = 'app_user'

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    passenger_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('passenger.passenger_id'))
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Enum('Passenger', 'Admin', 'Crew', name='app_user_role'), nullable=False)

    passenger = relationship('Passenger', back_populates='user')


class Airport(Base):
    __tablename__ = 'airport'

    airport_code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)


class Route(Base):
    __tablename__ = 'route'

    route_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    origin_code: Mapped[str] = mapped_column(String(3), ForeignKey('airport.airport_code'), nullable=False)
    dest_code: Mapped[str] = mapped_column(String(3), ForeignKey('airport.airport_code'), nullable=False)
    distance_km: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)


class Aircraft(Base):
    __tablename__ = 'aircraft'

    aircraft_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    registration_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(50), nullable=False)
    total_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    business_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    economy_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    airline_id: Mapped[int] = mapped_column(Integer, ForeignKey('airline.airline_id'), nullable=False)


class Flight(Base):
    __tablename__ = 'flight'

    flight_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    flight_number: Mapped[str] = mapped_column(String(10), nullable=False)
    route_id: Mapped[int] = mapped_column(Integer, ForeignKey('route.route_id'), nullable=False)
    aircraft_id: Mapped[int] = mapped_column(Integer, nullable=False)
    departure_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    arrival_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum('Scheduled', 'Delayed', 'Cancelled', 'Departed', name='flight_status'),
        nullable=False,
    )
    available_seats: Mapped[int] = mapped_column(Integer, nullable=False)


class Booking(Base):
    __tablename__ = 'booking'

    booking_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    booking_reference: Mapped[str] = mapped_column(String(12), nullable=False, unique=True)
    passenger_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('passenger.passenger_id'), nullable=False)
    flight_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('flight.flight_id'), nullable=False)
    booking_date: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    seat_number: Mapped[str] = mapped_column(String(5), nullable=False)
    class_type: Mapped[str] = mapped_column(
        Enum('Economy', 'Business', 'First', name='booking_class_type'),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum('Pending', 'Confirmed', 'Cancelled', name='booking_status'),
        nullable=False,
    )
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cancellation_time: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)


class Payment(Base):
    __tablename__ = 'payment'

    payment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('booking.booking_id'), nullable=False, unique=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(
        Enum('CreditCard', 'DebitCard', 'UPI', 'NetBanking', 'Wallet', name='payment_method_type'),
        nullable=False,
    )
    transaction_date: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    transaction_reference: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    payment_status: Mapped[str] = mapped_column(
        Enum('Pending', 'Success', 'Failed', 'Refunded', name='payment_status_type'),
        nullable=False,
    )


class SeatLock(Base):
    __tablename__ = 'seat_lock'

    lock_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    flight_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('flight.flight_id'), nullable=False)
    seat_number: Mapped[str] = mapped_column(String(5), nullable=False)
    locked_by_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('app_user.user_id'), nullable=False)
    lock_created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)


class Refund(Base):
    __tablename__ = 'refund'

    refund_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('booking.booking_id'), nullable=False, unique=True)
    refund_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    processed_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    refund_status: Mapped[str] = mapped_column(
        Enum('Pending', 'Processed', 'Rejected', name='refund_status_type'),
        nullable=False,
    )


class Employee(Base):
    __tablename__ = 'employee'

    employee_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(Enum('Pilot', 'CabinCrew', 'AdminStaff', name='employee_role'), nullable=False)
    date_hired: Mapped[Date] = mapped_column(Date, nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)


class CrewAssignment(Base):
    __tablename__ = 'crew_assignment'

    assignment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('employee.employee_id'), nullable=False)
    flight_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('flight.flight_id'), nullable=False)
    role_in_flight: Mapped[str] = mapped_column(
        Enum('Pilot', 'Co-Pilot', 'CabinCrew', 'HeadSteward', name='role_in_flight_type'),
        nullable=False,
    )
    assigned_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)


class OperationalAuditLog(Base):
    __tablename__ = 'operational_audit_log'

    audit_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('app_user.user_id'), nullable=False)
    action_status: Mapped[str] = mapped_column(String(20), nullable=False)
    action_notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
