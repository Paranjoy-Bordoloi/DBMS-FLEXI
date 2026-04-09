from datetime import date, datetime, time, timedelta
import json
import random
import string

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.exc import DatabaseError, IntegrityError, OperationalError
from sqlalchemy import asc, desc, func, text
from sqlalchemy.orm import Session

from .config import settings
from .database import engine, get_db
from .models import (
    Aircraft,
    Airline,
    Airport,
    AppUser,
    Booking,
    CrewAssignment,
    Employee,
    Flight,
    OperationalAuditLog,
    Passenger,
    Payment,
    Refund,
    Route,
    SeatLock,
)
from .schemas import (
    AdminCancelFlightRequest,
    AdminBookingExplorerResponse,
    AdminCreateAircraftRequest,
    AdminCreateFlightRequest,
    AdminCreateRouteRequest,
    AdminReaccommodateResponse,
    AdminMessageResponse,
    AdminRetimeFlightRequest,
    AdminSwapAircraftRequest,
    AdminUpdateFlightRequest,
    AircraftUtilizationResponse,
    AuditLogResponse,
    AirportOptionResponse,
    BookingChangeResponse,
    BookingDetailResponse,
    CancelBookingRequest,
    CancelBookingResponse,
    ChangeFlightRequest,
    ChangeSeatRequest,
    CrewUtilizationResponse,
    CreateBookingRequest,
    CreateBookingResponse,
    CurrentBookingResponse,
    CurrentUserResponse,
    DashboardSummaryResponse,
    FlightSearchResponse,
    LoginRequest,
    ManifestEntryResponse,
    RegisterRequest,
    SeatMapResponse,
    SeatMapSeatResponse,
    SeatLockRequest,
    SeatLockResponse,
    TokenResponse,
)
from .security import create_access_token, get_password_hash, verify_password


app = FastAPI(title='Airline Reservation API', version='0.1.0')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')

CLASS_FARE_MULTIPLIERS: dict[str, float] = {
    'Economy': 1.00,
    'Business': 1.70,
    'First': 2.35,
}

REBOOKING_CHANGE_FEE = 650.0

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:5173',
        'http://localhost:5174',
        'http://127.0.0.1:5173',
        'http://127.0.0.1:5174',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/')
def root() -> dict[str, str]:
    return {
        'message': 'Airline Reservation API is running.',
        'health': '/health',
        'docs': '/docs',
    }


@app.on_event('startup')
def ensure_operational_tables() -> None:
    # This keeps new operational MVP tables available without requiring a separate migration tool.
    try:
        OperationalAuditLog.__table__.create(bind=engine, checkfirst=True)
    except OperationalError:
        # If permissions are restricted, existing app features should still run.
        pass


def _validate_password_complexity(password: str) -> None:
    has_upper = any(char.isupper() for char in password)
    has_lower = any(char.islower() for char in password)
    has_digit = any(char.isdigit() for char in password)
    has_special = any(not char.isalnum() for char in password)

    if not (has_upper and has_lower and has_digit and has_special):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Password must include upper, lower, digit, and special character.',
        )


def _validate_date_of_birth(date_of_birth: date) -> None:
    if date_of_birth >= date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Date of birth must be a past date.',
        )


def _generate_booking_reference(db: Session) -> str:
    while True:
        suffix = ''.join(random.choices(string.digits, k=10))
        candidate = f'PN{suffix}'
        exists = db.query(Booking).filter(Booking.booking_reference == candidate).first()
        if not exists:
            return candidate


def _calculate_refund_ratio(hours_before_departure: float) -> float:
    if hours_before_departure > 48:
        return 0.90
    if hours_before_departure >= 24:
        return 0.70
    return 0.40


def _class_fare_multiplier(class_type: str) -> float:
    return CLASS_FARE_MULTIPLIERS.get(class_type, 1.0)


def _class_prices(base_price: float) -> dict[str, float]:
    return {
        'Economy': round(base_price * CLASS_FARE_MULTIPLIERS['Economy'], 2),
        'Business': round(base_price * CLASS_FARE_MULTIPLIERS['Business'], 2),
        'First': round(base_price * CLASS_FARE_MULTIPLIERS['First'], 2),
    }


def _seat_candidates(capacity: int) -> list[str]:
    letters = ['A', 'B', 'C', 'D', 'E', 'F']
    candidates = []
    rows = (capacity + len(letters) - 1) // len(letters)
    for row in range(1, rows + 1):
        for letter in letters:
            candidates.append(f'{row}{letter}')
            if len(candidates) >= capacity:
                return candidates
    return candidates


def _seat_index(seat_number: str) -> int:
    seat = (seat_number or '').strip().upper()
    if len(seat) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Seat number format is invalid.')

    row_part = ''.join(ch for ch in seat if ch.isdigit())
    letter_part = ''.join(ch for ch in seat if ch.isalpha())
    if not row_part or not letter_part:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Seat number format is invalid.')

    try:
        row = int(row_part)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Seat number format is invalid.') from error

    letter = letter_part[0]
    seat_letters = ['A', 'B', 'C', 'D', 'E', 'F']
    if row < 1 or letter not in seat_letters:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Seat number format is invalid.')

    return (row - 1) * len(seat_letters) + seat_letters.index(letter) + 1


def _first_class_seat_count(business_seats: int) -> int:
    if business_seats <= 0:
        return 0
    if business_seats < 8:
        return 0
    return min(max(round(business_seats * 0.35), 4), business_seats)


def _class_seat_numbers(capacity: int, business_seats: int, class_type: str) -> set[str]:
    seat_map = _seat_candidates(capacity)
    business_cap = max(min(business_seats, capacity), 0)
    first_cap = _first_class_seat_count(business_cap)

    if class_type == 'First':
        if first_cap == 0:
            return set()
        return set(seat_map[:first_cap])

    if class_type == 'Business':
        business_start = first_cap
        if business_cap <= business_start:
            return set()
        return set(seat_map[business_start:business_cap])

    return set(seat_map[business_cap:])


def _seat_type_for_number(seat_number: str) -> str:
    seat = seat_number.strip().upper()
    letter = ''.join(ch for ch in seat if ch.isalpha())[:1]
    if letter in {'A', 'F'}:
        return 'Window'
    if letter in {'C', 'D'}:
        return 'Aisle'
    return 'Middle'


def _log_operational_action(
    db: Session,
    action_type: str,
    entity_type: str,
    entity_id: str,
    actor_user_id: int,
    action_status: str,
    action_notes: str | None = None,
    metadata: dict | None = None,
) -> None:
    record = OperationalAuditLog(
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        action_status=action_status,
        action_notes=action_notes,
        metadata_json=json.dumps(metadata) if metadata else None,
        created_at=datetime.now(),
    )
    db.add(record)


def _available_class_seats(db: Session, flight_id: int, class_seats: set[str]) -> list[str]:
    now = datetime.now()
    booked_or_locked = {
        seat
        for (seat,) in db.query(Booking.seat_number)
        .filter(Booking.flight_id == flight_id)
        .filter(Booking.status.in_(['Pending', 'Confirmed']))
        .all()
    }
    locked_seats = {
        seat
        for (seat,) in db.query(SeatLock.seat_number)
        .filter(SeatLock.flight_id == flight_id)
        .filter(SeatLock.expires_at > now)
        .all()
    }
    unavailable = booked_or_locked.union(locked_seats)
    return [seat for seat in sorted(class_seats, key=_seat_index) if seat not in unavailable]


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> AppUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials.',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        subject = payload.get('sub')
        if subject is None:
            raise credentials_exception
        user_id = int(subject)
    except (JWTError, ValueError) as error:
        raise credentials_exception from error

    user = db.query(AppUser).filter(AppUser.user_id == user_id).first()
    if not user:
        raise credentials_exception
    return user


def require_roles(*roles: str):
    def role_dependency(current_user: AppUser = Depends(get_current_user)) -> AppUser:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient permissions.')
        return current_user

    return role_dependency


@app.get('/health')
def health_check() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/auth/register', status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    _validate_password_complexity(payload.password)
    _validate_date_of_birth(payload.date_of_birth)

    existing_user = db.query(AppUser).filter(AppUser.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already registered.')

    existing_passport = db.query(Passenger).filter(Passenger.passport_number == payload.passport_number).first()
    if existing_passport:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Passport already exists.')

    passenger = Passenger(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        passport_number=payload.passport_number,
        date_of_birth=payload.date_of_birth,
        address=payload.address,
    )
    db.add(passenger)
    db.flush()

    user = AppUser(
        passenger_id=passenger.passenger_id,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role='Passenger',
    )
    db.add(user)
    db.commit()
    return {'message': 'Registration successful.'}


@app.post('/auth/login', response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(AppUser).filter(AppUser.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials.')

    token = create_access_token(subject=str(user.user_id))
    return TokenResponse(access_token=token)


@app.get('/auth/me', response_model=CurrentUserResponse)
def auth_me(current_user: AppUser = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        role=current_user.role,
        passenger_id=current_user.passenger_id,
    )


@app.get('/flights/search', response_model=list[FlightSearchResponse])
def search_flights(
    origin_code: str = Query(min_length=3, max_length=3),
    destination_code: str = Query(min_length=3, max_length=3),
    travel_date: str = Query(description='YYYY-MM-DD'),
    flex_days: int = Query(default=0, ge=0, le=3),
    sort_by: str = Query(default='price', pattern='^(price|duration)$'),
    sort_order: str = Query(default='asc', pattern='^(asc|desc)$'),
    max_price: float | None = Query(default=None, ge=0),
    departure_from_hour: int | None = Query(default=None, ge=0, le=23),
    departure_to_hour: int | None = Query(default=None, ge=0, le=23),
    db: Session = Depends(get_db),
) -> list[FlightSearchResponse]:
    now = datetime.now()

    try:
        date_value = datetime.strptime(travel_date, '%Y-%m-%d').date()
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid date format. Use YYYY-MM-DD.') from error

    day_start = datetime.combine(date_value - timedelta(days=flex_days), time.min)
    day_end = datetime.combine(date_value + timedelta(days=flex_days), time.max)

    origin_alias = Airport.__table__.alias('origin_airport')
    destination_alias = Airport.__table__.alias('destination_airport')

    query = (
        db.query(
            Flight.flight_id,
            Flight.flight_number,
            Route.origin_code,
            Route.dest_code,
            Flight.departure_time,
            Flight.arrival_time,
            Route.estimated_duration_minutes,
            Flight.base_price,
            Flight.available_seats,
            Flight.status,
        )
        .join(Route, Route.route_id == Flight.route_id)
        .join(origin_alias, origin_alias.c.airport_code == Route.origin_code)
        .join(destination_alias, destination_alias.c.airport_code == Route.dest_code)
        .filter(Route.origin_code == origin_code.upper())
        .filter(Route.dest_code == destination_code.upper())
        .filter(Flight.departure_time >= day_start)
        .filter(Flight.departure_time <= day_end)
        .filter(Flight.departure_time > now)
        .filter(Flight.status.in_(['Scheduled', 'Delayed']))
    )

    if max_price is not None:
        query = query.filter(Flight.base_price <= max_price)

    if departure_from_hour is not None and departure_to_hour is not None:
        if departure_from_hour <= departure_to_hour:
            query = query.filter(func.hour(Flight.departure_time) >= departure_from_hour).filter(
                func.hour(Flight.departure_time) <= departure_to_hour
            )
        else:
            query = query.filter(
                (func.hour(Flight.departure_time) >= departure_from_hour)
                | (func.hour(Flight.departure_time) <= departure_to_hour)
            )

    sort_column = Flight.base_price if sort_by == 'price' else Route.estimated_duration_minutes
    ordering = asc(sort_column) if sort_order == 'asc' else desc(sort_column)
    records = query.order_by(ordering).all()

    responses: list[FlightSearchResponse] = []
    for row in records:
        price_map = _class_prices(float(row.base_price))
        responses.append(
            FlightSearchResponse(
                flight_id=row.flight_id,
                flight_number=row.flight_number,
                origin_code=row.origin_code,
                destination_code=row.dest_code,
                departure_time=row.departure_time,
                arrival_time=row.arrival_time,
                duration_minutes=row.estimated_duration_minutes,
                price=price_map['Economy'],
                economy_price=price_map['Economy'],
                business_price=price_map['Business'],
                first_price=price_map['First'],
                available_seats=row.available_seats,
                status=row.status,
            )
        )
    return responses


@app.get('/airports', response_model=list[AirportOptionResponse])
def list_airports(db: Session = Depends(get_db)) -> list[AirportOptionResponse]:
    records = db.query(Airport).order_by(Airport.airport_code.asc()).all()
    return [
        AirportOptionResponse(
            airport_code=row.airport_code,
            city=row.city,
            name=row.name,
            country=row.country,
        )
        for row in records
    ]


@app.post('/bookings/seat-lock', response_model=SeatLockResponse, status_code=status.HTTP_201_CREATED)
def lock_seat(
    payload: SeatLockRequest,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_roles('Passenger', 'Admin')),
) -> SeatLockResponse:
    now = datetime.now()

    if current_user.role != 'Admin' and current_user.user_id != payload.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You can only lock seats for your own user account.')

    try:
        db.query(SeatLock).filter(SeatLock.expires_at <= now).delete(synchronize_session=False)
        db.commit()
    except DatabaseError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Failed to cleanup expired seat locks.') from error

    user = db.query(AppUser).filter(AppUser.user_id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')

    flight = db.query(Flight).filter(Flight.flight_id == payload.flight_id).first()
    if not flight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Flight not found.')

    aircraft = db.query(Aircraft).filter(Aircraft.aircraft_id == flight.aircraft_id).first()
    if not aircraft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Aircraft not found for selected flight.')

    existing_booking = (
        db.query(Booking)
        .filter(Booking.flight_id == payload.flight_id)
        .filter(Booking.seat_number == payload.seat_number)
        .filter(Booking.status.in_(['Pending', 'Confirmed']))
        .first()
    )
    if existing_booking:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Seat is already booked.')

    existing_lock = (
        db.query(SeatLock)
        .filter(SeatLock.flight_id == payload.flight_id)
        .filter(SeatLock.seat_number == payload.seat_number)
        .filter(SeatLock.expires_at > now)
        .first()
    )
    if existing_lock:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Seat is currently locked by another user.')

    seat_lock = SeatLock(
        flight_id=payload.flight_id,
        seat_number=payload.seat_number,
        locked_by_user_id=payload.user_id,
        lock_created_at=now,
        expires_at=now + timedelta(minutes=payload.lock_minutes),
    )
    try:
        db.add(seat_lock)
        db.commit()
        db.refresh(seat_lock)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Seat is currently locked or invalid for this flight.') from error
    except DatabaseError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Seat lock request violates database rules.') from error

    return SeatLockResponse(
        lock_id=seat_lock.lock_id,
        flight_id=seat_lock.flight_id,
        seat_number=seat_lock.seat_number,
        expires_at=seat_lock.expires_at,
    )


@app.post('/bookings', response_model=CreateBookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: CreateBookingRequest,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_roles('Passenger', 'Admin')),
) -> CreateBookingResponse:
    now = datetime.now()
    lock_surcharge = 200.0

    if current_user.role != 'Admin' and current_user.user_id != payload.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You can only create bookings for your own user account.')

    passenger = db.query(Passenger).filter(Passenger.passenger_id == payload.passenger_id).first()
    if not passenger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Passenger not found.')

    flight = db.query(Flight).filter(Flight.flight_id == payload.flight_id).first()
    if not flight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Flight not found.')

    aircraft = db.query(Aircraft).filter(Aircraft.aircraft_id == flight.aircraft_id).first()
    if not aircraft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Aircraft not found for selected flight.')

    if flight.departure_time <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Cannot book a departed flight.')

    seat_number = payload.seat_number.strip().upper() if payload.seat_number else None
    allowed_seats = _class_seat_numbers(aircraft.total_capacity, aircraft.business_seats, payload.class_type)

    if payload.class_type in {'Business', 'First'} and not allowed_seats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'{payload.class_type} class is not available on this aircraft configuration.',
        )

    if payload.random_allotment:
        booked_or_locked = {
            seat
            for (seat,) in db.query(Booking.seat_number)
            .filter(Booking.flight_id == payload.flight_id)
            .filter(Booking.status.in_(['Pending', 'Confirmed']))
            .all()
        }
        locked_seats = {
            seat
            for (seat,) in db.query(SeatLock.seat_number)
            .filter(SeatLock.flight_id == payload.flight_id)
            .filter(SeatLock.expires_at > now)
            .all()
        }
        unavailable = booked_or_locked.union(locked_seats)
        options = [seat for seat in sorted(allowed_seats, key=_seat_index) if seat not in unavailable]
        if not options:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'No {payload.class_type} seats available for random allotment.',
            )
        seat_number = random.choice(options)
    elif not seat_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Seat number is required when random allotment is disabled.')

    if seat_number not in allowed_seats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Seat {seat_number} does not belong to {payload.class_type} class for this aircraft.',
        )

    foreign_lock = (
        db.query(SeatLock)
        .filter(SeatLock.flight_id == payload.flight_id)
        .filter(SeatLock.seat_number == seat_number)
        .filter(SeatLock.locked_by_user_id != payload.user_id)
        .filter(SeatLock.expires_at > now)
        .first()
    )
    if foreign_lock:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Selected seat is temporarily locked by another user.')

    active_lock = (
        db.query(SeatLock)
        .filter(SeatLock.flight_id == payload.flight_id)
        .filter(SeatLock.seat_number == seat_number)
        .filter(SeatLock.locked_by_user_id == payload.user_id)
        .filter(SeatLock.expires_at > now)
        .first()
    )

    if payload.use_seat_lock and not active_lock:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Seat lock option selected, but active lock not found for this seat.')

    surcharge = lock_surcharge if payload.use_seat_lock and active_lock else 0.0
    class_multiplier = _class_fare_multiplier(payload.class_type)
    class_adjusted_fare = float(flight.base_price) * class_multiplier
    total_amount = class_adjusted_fare + payload.tax_amount + payload.service_charge + surcharge
    total_amount = round(total_amount, 2)
    booking_reference = _generate_booking_reference(db)

    booking = Booking(
        booking_reference=booking_reference,
        passenger_id=payload.passenger_id,
        flight_id=payload.flight_id,
        booking_date=now,
        seat_number=seat_number,
        class_type=payload.class_type,
        status='Confirmed',
        total_amount=total_amount,
        cancellation_time=None,
    )

    payment = Payment(
        booking_id=0,
        amount=total_amount,
        payment_method=payload.payment_method,
        transaction_date=now,
        transaction_reference=payload.transaction_reference,
        payment_status='Success',
    )

    try:
        db.add(booking)
        db.flush()
        payment.booking_id = booking.booking_id
        db.add(payment)
        if active_lock:
            db.query(SeatLock).filter(SeatLock.lock_id == active_lock.lock_id).delete(synchronize_session=False)
        db.commit()
        db.refresh(booking)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Booking conflict or duplicate transaction reference.') from error
    except DatabaseError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Booking request violates database rules.') from error

    return CreateBookingResponse(
        booking_reference=booking.booking_reference,
        booking_id=booking.booking_id,
        seat_number=booking.seat_number,
        status=booking.status,
        total_amount=float(booking.total_amount),
    )


@app.get('/bookings/retrieve', response_model=BookingDetailResponse)
def retrieve_booking(
    pnr: str = Query(min_length=4, max_length=12),
    last_name: str = Query(min_length=1, max_length=50),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_roles('Passenger', 'Admin')),
) -> BookingDetailResponse:
    booking_row = (
        db.query(
            Booking.booking_reference,
            Passenger.first_name,
            Passenger.last_name,
            Flight.flight_number,
            Flight.departure_time,
            Flight.arrival_time,
            Booking.seat_number,
            Booking.class_type,
            Booking.status,
            Booking.total_amount,
        )
        .join(Passenger, Passenger.passenger_id == Booking.passenger_id)
        .join(Flight, Flight.flight_id == Booking.flight_id)
        .filter(Booking.booking_reference == pnr)
        .filter(Passenger.last_name == last_name)
        .first()
    )

    if not booking_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Booking not found.')

    if current_user.role == 'Passenger':
        booking_owner = db.query(Booking).filter(Booking.booking_reference == pnr).first()
        if not booking_owner or booking_owner.passenger_id != current_user.passenger_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You can only access your own bookings.')

    return BookingDetailResponse(
        booking_reference=booking_row.booking_reference,
        passenger_name=f'{booking_row.first_name} {booking_row.last_name}',
        flight_number=booking_row.flight_number,
        departure_time=booking_row.departure_time,
        arrival_time=booking_row.arrival_time,
        seat_number=booking_row.seat_number,
        class_type=booking_row.class_type,
        booking_status=booking_row.status,
        total_amount=float(booking_row.total_amount),
    )


@app.get('/bookings/current', response_model=list[CurrentBookingResponse])
def list_current_bookings(
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_roles('Passenger', 'Admin')),
) -> list[CurrentBookingResponse]:
    query = (
        db.query(
            Booking.booking_reference,
            Passenger.first_name,
            Passenger.last_name,
            Flight.flight_number,
            Flight.departure_time,
            Flight.arrival_time,
            Booking.seat_number,
            Booking.class_type,
            Booking.status,
            Booking.total_amount,
        )
        .join(Passenger, Passenger.passenger_id == Booking.passenger_id)
        .join(Flight, Flight.flight_id == Booking.flight_id)
        .filter(Flight.departure_time >= datetime.now())
        .filter(Booking.status != 'Cancelled')
        .order_by(Flight.departure_time.asc())
    )

    if current_user.role == 'Passenger':
        query = query.filter(Booking.passenger_id == current_user.passenger_id)

    rows = query.limit(100).all()
    return [
        CurrentBookingResponse(
            booking_reference=row.booking_reference,
            passenger_name=f'{row.first_name} {row.last_name}',
            flight_number=row.flight_number,
            departure_time=row.departure_time,
            arrival_time=row.arrival_time,
            seat_number=row.seat_number,
            class_type=row.class_type,
            booking_status=row.status,
            total_amount=float(row.total_amount),
        )
        for row in rows
    ]


@app.get('/admin/bookings', response_model=list[AdminBookingExplorerResponse])
def admin_list_all_bookings(
    status: str | None = Query(default=None, pattern='^(Pending|Confirmed|Cancelled)$'),
    flight_id: int | None = Query(default=None),
    passenger_id: int | None = Query(default=None),
    passenger_email: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
    _: AppUser = Depends(require_roles('Admin')),
) -> list[AdminBookingExplorerResponse]:
    """List all bookings across all passengers (admin only).
    
    Filters:
    - status: Pending, Confirmed, or Cancelled
    - flight_id: bookings for a specific flight
    - passenger_id: bookings by a specific passenger
    - passenger_email: bookings by email (partial match)
    """
    query = (
        db.query(
            Booking.booking_id,
            Booking.booking_reference,
            Booking.total_amount,
            Booking.status,
            Booking.seat_number,
            Booking.class_type,
            Booking.booking_date,
            Passenger.first_name,
            Passenger.last_name,
            Passenger.email,
            Flight.flight_id,
            Flight.flight_number,
            Flight.departure_time,
            Flight.arrival_time,
            Route.origin_code,
            Route.dest_code,
        )
        .join(Passenger, Passenger.passenger_id == Booking.passenger_id)
        .join(Flight, Flight.flight_id == Booking.flight_id)
        .join(Route, Route.route_id == Flight.route_id)
        .order_by(Booking.booking_date.desc())
    )

    if status:
        query = query.filter(Booking.status == status)
    if flight_id:
        query = query.filter(Booking.flight_id == flight_id)
    if passenger_id:
        query = query.filter(Booking.passenger_id == passenger_id)
    if passenger_email:
        query = query.filter(Passenger.email.ilike(f'%{passenger_email}%'))

    rows = query.limit(limit).all()

    return [
        AdminBookingExplorerResponse(
            booking_id=row.booking_id,
            booking_reference=row.booking_reference,
            passenger_first_name=row.first_name,
            passenger_last_name=row.last_name,
            passenger_email=row.email,
            flight_id=row.flight_id,
            flight_number=row.flight_number,
            origin_code=row.origin_code,
            destination_code=row.dest_code,
            departure_time=row.departure_time,
            arrival_time=row.arrival_time,
            seat_number=row.seat_number,
            class_type=row.class_type,
            booking_date=row.booking_date,
            status=row.status,
            total_amount=float(row.total_amount),
        )
        for row in rows
    ]


@app.get('/flights/{flight_id}/seat-map', response_model=SeatMapResponse)
def get_flight_seat_map(
    flight_id: int,
    class_type: str | None = Query(default=None, pattern='^(Economy|Business|First)$'),
    db: Session = Depends(get_db),
    _: AppUser = Depends(require_roles('Passenger', 'Admin')),
) -> SeatMapResponse:
    now = datetime.now()
    flight = db.query(Flight).filter(Flight.flight_id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Flight not found.')

    aircraft = db.query(Aircraft).filter(Aircraft.aircraft_id == flight.aircraft_id).first()
    if not aircraft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Aircraft not found for selected flight.')

    all_seats = _seat_candidates(aircraft.total_capacity)
    first_zone = _class_seat_numbers(aircraft.total_capacity, aircraft.business_seats, 'First')
    business_zone = _class_seat_numbers(aircraft.total_capacity, aircraft.business_seats, 'Business')
    economy_zone = _class_seat_numbers(aircraft.total_capacity, aircraft.business_seats, 'Economy')

    booked = {
        seat
        for (seat,) in db.query(Booking.seat_number)
        .filter(Booking.flight_id == flight_id)
        .filter(Booking.status.in_(['Pending', 'Confirmed']))
        .all()
    }
    locked = {
        seat
        for (seat,) in db.query(SeatLock.seat_number)
        .filter(SeatLock.flight_id == flight_id)
        .filter(SeatLock.expires_at > now)
        .all()
    }

    seats: list[SeatMapSeatResponse] = []
    for seat in all_seats:
        if seat in first_zone:
            cabin_class = 'First'
        elif seat in business_zone:
            cabin_class = 'Business'
        else:
            cabin_class = 'Economy'

        status_label = 'Available'
        if seat in booked:
            status_label = 'Booked'
        elif seat in locked:
            status_label = 'Locked'

        selectable = status_label == 'Available' and (class_type is None or cabin_class == class_type)
        seats.append(
            SeatMapSeatResponse(
                seat_number=seat,
                cabin_class=cabin_class,
                seat_type=_seat_type_for_number(seat),
                status=status_label,
                is_selectable=selectable,
            )
        )

    return SeatMapResponse(
        flight_id=flight.flight_id,
        aircraft_id=aircraft.aircraft_id,
        total_capacity=aircraft.total_capacity,
        business_seats=aircraft.business_seats,
        economy_seats=aircraft.economy_seats,
        seats=seats,
    )


@app.post('/bookings/{pnr}/change-seat', response_model=BookingChangeResponse)
def change_booking_seat(
    pnr: str,
    payload: ChangeSeatRequest,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_roles('Passenger', 'Admin')),
) -> BookingChangeResponse:
    now = datetime.now()
    booking = db.query(Booking).filter(Booking.booking_reference == pnr).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Booking not found.')

    if current_user.role == 'Passenger' and booking.passenger_id != current_user.passenger_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You can only modify your own bookings.')

    if booking.status == 'Cancelled':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Cannot modify a cancelled booking.')

    flight = db.query(Flight).filter(Flight.flight_id == booking.flight_id).first()
    if not flight or flight.departure_time <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Seat changes are allowed only before departure.')

    aircraft = db.query(Aircraft).filter(Aircraft.aircraft_id == flight.aircraft_id).first()
    if not aircraft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Aircraft not found for selected flight.')

    new_seat = payload.new_seat_number.strip().upper()
    class_zone = _class_seat_numbers(aircraft.total_capacity, aircraft.business_seats, booking.class_type)
    if new_seat not in class_zone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Seat {new_seat} is not in your booking class zone.')

    available = set(_available_class_seats(db, flight.flight_id, class_zone))
    if new_seat != booking.seat_number and new_seat not in available:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Requested seat is not available.')

    old_seat = booking.seat_number
    booking.seat_number = new_seat
    db.commit()

    return BookingChangeResponse(
        booking_reference=booking.booking_reference,
        message='Seat updated successfully.',
        old_flight_id=booking.flight_id,
        new_flight_id=booking.flight_id,
        old_seat_number=old_seat,
        new_seat_number=new_seat,
        additional_amount=0,
        updated_total_amount=float(booking.total_amount),
    )


@app.post('/bookings/{pnr}/change-flight', response_model=BookingChangeResponse)
def change_booking_flight(
    pnr: str,
    payload: ChangeFlightRequest,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_roles('Passenger', 'Admin')),
) -> BookingChangeResponse:
    now = datetime.now()
    booking = db.query(Booking).filter(Booking.booking_reference == pnr).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Booking not found.')

    if current_user.role == 'Passenger' and booking.passenger_id != current_user.passenger_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You can only modify your own bookings.')

    if booking.status == 'Cancelled':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Cannot modify a cancelled booking.')

    old_flight = db.query(Flight).filter(Flight.flight_id == booking.flight_id).first()
    new_flight = db.query(Flight).filter(Flight.flight_id == payload.new_flight_id).first()
    if not old_flight or not new_flight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Source or target flight not found.')

    if old_flight.departure_time <= now or new_flight.departure_time <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Flight changes are allowed only for future flights.')

    old_route = db.query(Route).filter(Route.route_id == old_flight.route_id).first()
    new_route = db.query(Route).filter(Route.route_id == new_flight.route_id).first()
    if not old_route or not new_route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Route details missing for selected flights.')

    if (old_route.origin_code, old_route.dest_code) != (new_route.origin_code, new_route.dest_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='MVP rebooking supports only same origin-destination route.')

    new_aircraft = db.query(Aircraft).filter(Aircraft.aircraft_id == new_flight.aircraft_id).first()
    if not new_aircraft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Aircraft not found for target flight.')

    class_zone = _class_seat_numbers(new_aircraft.total_capacity, new_aircraft.business_seats, booking.class_type)
    if booking.class_type in {'Business', 'First'} and not class_zone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'{booking.class_type} is not available on target flight.')

    available = _available_class_seats(db, new_flight.flight_id, class_zone)
    requested = payload.new_seat_number.strip().upper() if payload.new_seat_number else None

    if requested:
        if requested not in class_zone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Seat {requested} is not in your booking class zone.')
        if requested not in available:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Requested seat is not available on target flight.')
        new_seat = requested
    else:
        if not available:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='No seats available in your booking class on target flight.')
        new_seat = available[0]

    class_multiplier = _class_fare_multiplier(booking.class_type)
    old_class_fare = float(old_flight.base_price) * class_multiplier
    new_class_fare = float(new_flight.base_price) * class_multiplier
    fare_increase = max(0.0, new_class_fare - old_class_fare)
    additional_amount = round(fare_increase + REBOOKING_CHANGE_FEE, 2)

    old_flight_id = booking.flight_id
    old_seat = booking.seat_number
    booking.flight_id = new_flight.flight_id
    booking.seat_number = new_seat
    booking.total_amount = round(float(booking.total_amount) + additional_amount, 2)

    payment = db.query(Payment).filter(Payment.booking_id == booking.booking_id).first()
    if payment and payment.payment_status in {'Success', 'Pending'}:
        payment.amount = booking.total_amount

    db.commit()

    return BookingChangeResponse(
        booking_reference=booking.booking_reference,
        message='Flight changed successfully.',
        old_flight_id=old_flight_id,
        new_flight_id=new_flight.flight_id,
        old_seat_number=old_seat,
        new_seat_number=new_seat,
        additional_amount=additional_amount,
        updated_total_amount=float(booking.total_amount),
    )


@app.get('/bookings/{pnr}/ticket', response_model=BookingDetailResponse)
def get_ticket(
    pnr: str,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_roles('Passenger', 'Admin')),
) -> BookingDetailResponse:
    booking_row = (
        db.query(
            Booking.booking_reference,
            Passenger.first_name,
            Passenger.last_name,
            Flight.flight_number,
            Flight.departure_time,
            Flight.arrival_time,
            Booking.seat_number,
            Booking.class_type,
            Booking.status,
            Booking.total_amount,
        )
        .join(Passenger, Passenger.passenger_id == Booking.passenger_id)
        .join(Flight, Flight.flight_id == Booking.flight_id)
        .filter(Booking.booking_reference == pnr)
        .first()
    )

    if not booking_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Booking not found.')

    if current_user.role == 'Passenger':
        booking_owner = db.query(Booking).filter(Booking.booking_reference == pnr).first()
        if not booking_owner or booking_owner.passenger_id != current_user.passenger_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You can only access your own bookings.')

    return BookingDetailResponse(
        booking_reference=booking_row.booking_reference,
        passenger_name=f'{booking_row.first_name} {booking_row.last_name}',
        flight_number=booking_row.flight_number,
        departure_time=booking_row.departure_time,
        arrival_time=booking_row.arrival_time,
        seat_number=booking_row.seat_number,
        class_type=booking_row.class_type,
        booking_status=booking_row.status,
        total_amount=float(booking_row.total_amount),
    )


@app.post('/bookings/{pnr}/cancel', response_model=CancelBookingResponse)
def cancel_booking(
    pnr: str,
    payload: CancelBookingRequest,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_roles('Passenger', 'Admin')),
) -> CancelBookingResponse:
    now = datetime.now()

    booking = db.query(Booking).filter(Booking.booking_reference == pnr).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Booking not found.')

    if current_user.role == 'Passenger' and booking.passenger_id != current_user.passenger_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You can only cancel your own bookings.')

    if booking.status == 'Cancelled':
        existing_refund = db.query(Refund).filter(Refund.booking_id == booking.booking_id).first()
        return CancelBookingResponse(
            booking_reference=booking.booking_reference,
            booking_status=booking.status,
            refund_amount=float(existing_refund.refund_amount) if existing_refund else 0.0,
            refund_status=existing_refund.refund_status if existing_refund else 'Pending',
        )

    flight = db.query(Flight).filter(Flight.flight_id == booking.flight_id).first()
    if not flight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Associated flight not found.')

    if flight.departure_time <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Cannot cancel after departure.')

    hours_before_departure = (flight.departure_time - now).total_seconds() / 3600
    refund_ratio = _calculate_refund_ratio(hours_before_departure)
    refund_amount = float(booking.total_amount) * refund_ratio

    refund = db.query(Refund).filter(Refund.booking_id == booking.booking_id).first()
    if not refund:
        refund = Refund(
            booking_id=booking.booking_id,
            refund_amount=refund_amount,
            reason=payload.reason,
            processed_at=now,
            refund_status='Processed',
        )
        db.add(refund)
    else:
        refund.refund_amount = refund_amount
        refund.reason = payload.reason
        refund.processed_at = now
        refund.refund_status = 'Processed'

    booking.status = 'Cancelled'
    booking.cancellation_time = now

    payment = db.query(Payment).filter(Payment.booking_id == booking.booking_id).first()
    if payment and payment.payment_status == 'Success':
        payment.payment_status = 'Refunded'

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Cancellation update conflict occurred.') from error
    except DatabaseError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Cancellation request violates database rules.') from error

    return CancelBookingResponse(
        booking_reference=booking.booking_reference,
        booking_status=booking.status,
        refund_amount=refund_amount,
        refund_status='Processed',
    )


@app.post('/admin/routes', response_model=AdminMessageResponse, status_code=status.HTTP_201_CREATED)
def admin_create_route(
    payload: AdminCreateRouteRequest,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_roles('Admin')),
) -> AdminMessageResponse:
    origin = db.query(Airport).filter(Airport.airport_code == payload.origin_code.upper()).first()
    destination = db.query(Airport).filter(Airport.airport_code == payload.dest_code.upper()).first()
    if not origin or not destination:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Origin or destination airport is invalid.')

    route = Route(
        origin_code=payload.origin_code.upper(),
        dest_code=payload.dest_code.upper(),
        distance_km=payload.distance_km,
        estimated_duration_minutes=payload.estimated_duration_minutes,
    )
    db.add(route)
    db.flush()
    _log_operational_action(
        db,
        action_type='CREATE_ROUTE',
        entity_type='Route',
        entity_id=str(route.route_id),
        actor_user_id=current_user.user_id,
        action_status='SUCCESS',
        action_notes='Route created from admin console.',
        metadata={'origin_code': route.origin_code, 'dest_code': route.dest_code},
    )
    db.commit()
    return AdminMessageResponse(message='Route created successfully.')


@app.post('/admin/aircraft', response_model=AdminMessageResponse, status_code=status.HTTP_201_CREATED)
def admin_create_aircraft(
    payload: AdminCreateAircraftRequest,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_roles('Admin')),
) -> AdminMessageResponse:
    if payload.business_seats + payload.economy_seats > payload.total_capacity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Seat split exceeds total capacity.')

    airline = db.query(Airline).filter(Airline.airline_id == payload.airline_id).first()
    if not airline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Airline not found.')

    aircraft = Aircraft(
        registration_number=payload.registration_number,
        model=payload.model,
        manufacturer=payload.manufacturer,
        total_capacity=payload.total_capacity,
        business_seats=payload.business_seats,
        economy_seats=payload.economy_seats,
        airline_id=payload.airline_id,
    )
    db.add(aircraft)
    db.flush()
    _log_operational_action(
        db,
        action_type='CREATE_AIRCRAFT',
        entity_type='Aircraft',
        entity_id=str(aircraft.aircraft_id),
        actor_user_id=current_user.user_id,
        action_status='SUCCESS',
        action_notes='Aircraft created from admin console.',
        metadata={'registration_number': aircraft.registration_number, 'airline_id': aircraft.airline_id},
    )
    db.commit()
    return AdminMessageResponse(message='Aircraft added successfully.')


@app.post('/admin/flights', response_model=AdminMessageResponse, status_code=status.HTTP_201_CREATED)
def admin_create_flight(
    payload: AdminCreateFlightRequest,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_roles('Admin')),
) -> AdminMessageResponse:
    route = db.query(Route).filter(Route.route_id == payload.route_id).first()
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Route not found.')

    aircraft = db.query(Aircraft).filter(Aircraft.aircraft_id == payload.aircraft_id).first()
    if not aircraft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Aircraft not found.')

    if payload.departure_time >= payload.arrival_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Departure must be before arrival.')

    flight = Flight(
        flight_number=payload.flight_number,
        route_id=payload.route_id,
        aircraft_id=payload.aircraft_id,
        departure_time=payload.departure_time,
        arrival_time=payload.arrival_time,
        base_price=payload.base_price,
        status='Scheduled',
        available_seats=aircraft.total_capacity,
    )
    db.add(flight)
    db.flush()
    _log_operational_action(
        db,
        action_type='CREATE_FLIGHT',
        entity_type='Flight',
        entity_id=str(flight.flight_id),
        actor_user_id=current_user.user_id,
        action_status='SUCCESS',
        action_notes='Flight created from admin console.',
        metadata={'flight_number': flight.flight_number, 'route_id': flight.route_id, 'aircraft_id': flight.aircraft_id},
    )
    db.commit()
    return AdminMessageResponse(message='Flight schedule created successfully.')


@app.patch('/admin/flights/{flight_id}', response_model=AdminMessageResponse)
def admin_update_flight(
    flight_id: int,
    payload: AdminUpdateFlightRequest,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_roles('Admin')),
) -> AdminMessageResponse:
    flight = db.query(Flight).filter(Flight.flight_id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Flight not found.')

    if payload.departure_time is not None:
        flight.departure_time = payload.departure_time
    if payload.arrival_time is not None:
        flight.arrival_time = payload.arrival_time
    if payload.base_price is not None:
        flight.base_price = payload.base_price
    if payload.status is not None:
        flight.status = payload.status

    if flight.departure_time >= flight.arrival_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Departure must be before arrival.')

    _log_operational_action(
        db,
        action_type='UPDATE_FLIGHT',
        entity_type='Flight',
        entity_id=str(flight.flight_id),
        actor_user_id=current_user.user_id,
        action_status='SUCCESS',
        action_notes='Flight updated from admin console.',
        metadata={
            'departure_time': flight.departure_time.isoformat(),
            'arrival_time': flight.arrival_time.isoformat(),
            'base_price': float(flight.base_price),
            'status': flight.status,
        },
    )
    db.commit()
    return AdminMessageResponse(message='Flight updated successfully.')


def _try_reaccommodate_bookings(
    db: Session,
    source_flight: Flight,
    max_hours_window: int,
) -> tuple[int, int, int | None]:
    route = db.query(Route).filter(Route.route_id == source_flight.route_id).first()
    if not route:
        return 0, 0, None

    window_end = source_flight.departure_time + timedelta(hours=max_hours_window)
    candidates = (
        db.query(Flight)
        .join(Route, Route.route_id == Flight.route_id)
        .filter(Flight.flight_id != source_flight.flight_id)
        .filter(Route.origin_code == route.origin_code)
        .filter(Route.dest_code == route.dest_code)
        .filter(Flight.status.in_(['Scheduled', 'Delayed']))
        .filter(Flight.departure_time >= datetime.now())
        .filter(Flight.departure_time <= window_end)
        .order_by(Flight.departure_time.asc())
        .all()
    )

    if not candidates:
        return 0, 0, None

    bookings = (
        db.query(Booking)
        .filter(Booking.flight_id == source_flight.flight_id)
        .filter(Booking.status.in_(['Pending', 'Confirmed']))
        .all()
    )

    moved = 0
    failed = 0
    target_flight_id: int | None = None

    for booking in bookings:
        moved_this_booking = False
        for candidate in candidates:
            candidate_aircraft = db.query(Aircraft).filter(Aircraft.aircraft_id == candidate.aircraft_id).first()
            if not candidate_aircraft:
                continue

            class_zone = _class_seat_numbers(candidate_aircraft.total_capacity, candidate_aircraft.business_seats, booking.class_type)
            available = _available_class_seats(db, candidate.flight_id, class_zone)
            if not available:
                continue

            booking.flight_id = candidate.flight_id
            booking.seat_number = available[0]
            target_flight_id = candidate.flight_id
            moved += 1
            moved_this_booking = True
            break

        if not moved_this_booking:
            failed += 1

    return moved, failed, target_flight_id


@app.post('/admin/operations/flights/{flight_id}/cancel', response_model=AdminReaccommodateResponse)
def admin_cancel_flight_with_reaccommodation(
    flight_id: int,
    payload: AdminCancelFlightRequest,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_roles('Admin')),
) -> AdminReaccommodateResponse:
    flight = db.query(Flight).filter(Flight.flight_id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Flight not found.')

    flight.status = 'Cancelled'
    moved = 0
    failed = 0
    target_flight_id: int | None = None

    if payload.auto_reaccommodate:
        moved, failed, target_flight_id = _try_reaccommodate_bookings(db, flight, payload.max_hours_window)

    _log_operational_action(
        db,
        action_type='DISRUPTION_CANCEL_FLIGHT',
        entity_type='Flight',
        entity_id=str(flight.flight_id),
        actor_user_id=current_user.user_id,
        action_status='SUCCESS',
        action_notes=payload.reason,
        metadata={
            'auto_reaccommodate': payload.auto_reaccommodate,
            'max_hours_window': payload.max_hours_window,
            'moved_bookings': moved,
            'failed_bookings': failed,
            'target_flight_id': target_flight_id,
        },
    )
    db.commit()

    return AdminReaccommodateResponse(
        source_flight_id=flight.flight_id,
        target_flight_id=target_flight_id,
        moved_bookings=moved,
        failed_bookings=failed,
        message='Flight cancelled and disruption workflow completed.',
    )


@app.post('/admin/operations/flights/{flight_id}/retime', response_model=AdminMessageResponse)
def admin_retime_flight(
    flight_id: int,
    payload: AdminRetimeFlightRequest,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_roles('Admin')),
) -> AdminMessageResponse:
    flight = db.query(Flight).filter(Flight.flight_id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Flight not found.')

    if payload.new_departure_time >= payload.new_arrival_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Departure must be before arrival.')

    flight.departure_time = payload.new_departure_time
    flight.arrival_time = payload.new_arrival_time
    if flight.status == 'Cancelled':
        flight.status = 'Scheduled'

    _log_operational_action(
        db,
        action_type='DISRUPTION_RETIME_FLIGHT',
        entity_type='Flight',
        entity_id=str(flight.flight_id),
        actor_user_id=current_user.user_id,
        action_status='SUCCESS',
        action_notes=payload.reason,
        metadata={
            'new_departure_time': payload.new_departure_time.isoformat(),
            'new_arrival_time': payload.new_arrival_time.isoformat(),
        },
    )
    db.commit()
    return AdminMessageResponse(message='Flight retimed successfully.')


@app.post('/admin/operations/flights/{flight_id}/swap-aircraft', response_model=AdminMessageResponse)
def admin_swap_aircraft(
    flight_id: int,
    payload: AdminSwapAircraftRequest,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_roles('Admin')),
) -> AdminMessageResponse:
    flight = db.query(Flight).filter(Flight.flight_id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Flight not found.')

    aircraft = db.query(Aircraft).filter(Aircraft.aircraft_id == payload.new_aircraft_id).first()
    if not aircraft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='New aircraft not found.')

    active_bookings = (
        db.query(func.count(Booking.booking_id))
        .filter(Booking.flight_id == flight.flight_id)
        .filter(Booking.status.in_(['Pending', 'Confirmed']))
        .scalar()
        or 0
    )
    if aircraft.total_capacity < active_bookings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Selected aircraft does not have enough capacity for active bookings.')

    old_aircraft_id = flight.aircraft_id
    flight.aircraft_id = aircraft.aircraft_id
    flight.available_seats = max(0, aircraft.total_capacity - active_bookings)

    _log_operational_action(
        db,
        action_type='DISRUPTION_SWAP_AIRCRAFT',
        entity_type='Flight',
        entity_id=str(flight.flight_id),
        actor_user_id=current_user.user_id,
        action_status='SUCCESS',
        action_notes=payload.reason,
        metadata={'old_aircraft_id': old_aircraft_id, 'new_aircraft_id': aircraft.aircraft_id},
    )
    db.commit()
    return AdminMessageResponse(message='Aircraft swapped successfully.')


@app.get('/admin/operations/utilization/aircraft', response_model=list[AircraftUtilizationResponse])
def admin_aircraft_utilization(
    next_days: int = Query(default=14, ge=1, le=90),
    db: Session = Depends(get_db),
    _: AppUser = Depends(require_roles('Admin')),
) -> list[AircraftUtilizationResponse]:
    now = datetime.now()
    until = now + timedelta(days=next_days)
    rows = (
        db.query(
            Aircraft.aircraft_id,
            Aircraft.registration_number,
            Aircraft.airline_id,
            func.count(Flight.flight_id).label('scheduled_flights'),
            func.coalesce(func.sum(func.timestampdiff(text('MINUTE'), Flight.departure_time, Flight.arrival_time)), 0).label('minutes'),
        )
        .join(Flight, Flight.aircraft_id == Aircraft.aircraft_id)
        .filter(Flight.departure_time >= now)
        .filter(Flight.departure_time <= until)
        .group_by(Aircraft.aircraft_id, Aircraft.registration_number, Aircraft.airline_id)
        .order_by(desc('minutes'))
        .all()
    )

    return [
        AircraftUtilizationResponse(
            aircraft_id=row.aircraft_id,
            registration_number=row.registration_number,
            airline_id=row.airline_id,
            scheduled_flights=int(row.scheduled_flights or 0),
            utilization_hours=round((float(row.minutes or 0) / 60.0), 2),
        )
        for row in rows
    ]


@app.get('/admin/operations/utilization/crew', response_model=list[CrewUtilizationResponse])
def admin_crew_utilization(
    next_days: int = Query(default=14, ge=1, le=90),
    db: Session = Depends(get_db),
    _: AppUser = Depends(require_roles('Admin')),
) -> list[CrewUtilizationResponse]:
    now = datetime.now()
    until = now + timedelta(days=next_days)
    rows = (
        db.query(
            Employee.employee_id,
            Employee.first_name,
            Employee.last_name,
            Employee.role,
            func.count(CrewAssignment.assignment_id).label('assigned_flights'),
            func.coalesce(func.sum(func.timestampdiff(text('MINUTE'), Flight.departure_time, Flight.arrival_time)), 0).label('minutes'),
        )
        .join(CrewAssignment, CrewAssignment.employee_id == Employee.employee_id)
        .join(Flight, Flight.flight_id == CrewAssignment.flight_id)
        .filter(Flight.departure_time >= now)
        .filter(Flight.departure_time <= until)
        .group_by(Employee.employee_id, Employee.first_name, Employee.last_name, Employee.role)
        .order_by(desc('minutes'))
        .all()
    )

    return [
        CrewUtilizationResponse(
            employee_id=row.employee_id,
            employee_name=f'{row.first_name} {row.last_name}',
            role=row.role,
            assigned_flights=int(row.assigned_flights or 0),
            utilization_hours=round((float(row.minutes or 0) / 60.0), 2),
        )
        for row in rows
    ]


@app.get('/admin/operations/audit-logs', response_model=list[AuditLogResponse])
def admin_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: AppUser = Depends(require_roles('Admin')),
) -> list[AuditLogResponse]:
    rows = (
        db.query(OperationalAuditLog)
        .order_by(OperationalAuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        AuditLogResponse(
            audit_id=row.audit_id,
            action_type=row.action_type,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            actor_user_id=row.actor_user_id,
            action_status=row.action_status,
            action_notes=row.action_notes,
            metadata_json=row.metadata_json,
            created_at=row.created_at,
        )
        for row in rows
    ]


@app.get('/admin/flights/{flight_id}/manifest', response_model=list[ManifestEntryResponse])
def admin_get_manifest(
    flight_id: int,
    db: Session = Depends(get_db),
    _: AppUser = Depends(require_roles('Admin')),
) -> list[ManifestEntryResponse]:
    rows = (
        db.query(
            Booking.booking_reference,
            Passenger.first_name,
            Passenger.last_name,
            Booking.seat_number,
            Booking.class_type,
            Booking.status,
        )
        .join(Passenger, Passenger.passenger_id == Booking.passenger_id)
        .filter(Booking.flight_id == flight_id)
        .filter(Booking.status.in_(['Pending', 'Confirmed']))
        .order_by(Booking.seat_number.asc())
        .all()
    )

    return [
        ManifestEntryResponse(
            booking_reference=row.booking_reference,
            passenger_name=f'{row.first_name} {row.last_name}',
            seat_number=row.seat_number,
            class_type=row.class_type,
            booking_status=row.status,
        )
        for row in rows
    ]


@app.get('/admin/dashboard/summary', response_model=DashboardSummaryResponse)
def admin_dashboard_summary(
    db: Session = Depends(get_db),
    _: AppUser = Depends(require_roles('Admin')),
) -> DashboardSummaryResponse:
    total_bookings = db.query(func.count(Booking.booking_id)).scalar() or 0
    confirmed_bookings = (
        db.query(func.count(Booking.booking_id))
        .filter(Booking.status == 'Confirmed')
        .scalar()
        or 0
    )

    total_revenue = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.payment_status == 'Success')
        .scalar()
        or 0
    )

    occupancy_rows = (
        db.query(
            Flight.flight_id,
            Aircraft.total_capacity,
            func.count(Booking.booking_id).label('active_bookings'),
        )
        .join(Aircraft, Aircraft.aircraft_id == Flight.aircraft_id)
        .outerjoin(
            Booking,
            (Booking.flight_id == Flight.flight_id)
            & (Booking.status.in_(['Pending', 'Confirmed'])),
        )
        .group_by(Flight.flight_id, Aircraft.total_capacity)
        .all()
    )

    if occupancy_rows:
        occupancy_values = [
            (row.active_bookings / row.total_capacity) * 100 if row.total_capacity else 0
            for row in occupancy_rows
        ]
        average_occupancy_percent = sum(occupancy_values) / len(occupancy_values)
    else:
        average_occupancy_percent = 0

    return DashboardSummaryResponse(
        total_bookings=total_bookings,
        confirmed_bookings=confirmed_bookings,
        total_revenue=float(total_revenue),
        average_occupancy_percent=round(average_occupancy_percent, 2),
    )
