from datetime import datetime, time, timedelta
import random
import string

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.exc import DatabaseError, IntegrityError
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Aircraft, Airline, Airport, AppUser, Booking, Flight, Passenger, Payment, Refund, Route, SeatLock
from .schemas import (
    AdminCreateAircraftRequest,
    AdminCreateFlightRequest,
    AdminCreateRouteRequest,
    AdminMessageResponse,
    AdminUpdateFlightRequest,
    BookingDetailResponse,
    CancelBookingRequest,
    CancelBookingResponse,
    CreateBookingRequest,
    CreateBookingResponse,
    CurrentUserResponse,
    DashboardSummaryResponse,
    FlightSearchResponse,
    LoginRequest,
    ManifestEntryResponse,
    RegisterRequest,
    SeatLockRequest,
    SeatLockResponse,
    TokenResponse,
)
from .security import create_access_token, get_password_hash, verify_password


app = FastAPI(title='Airline Reservation API', version='0.1.0')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:5173',
        'http://127.0.0.1:5173',
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
        age=payload.age,
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
    sort_by: str = Query(default='price', pattern='^(price|duration)$'),
    sort_order: str = Query(default='asc', pattern='^(asc|desc)$'),
    db: Session = Depends(get_db),
) -> list[FlightSearchResponse]:
    try:
        date_value = datetime.strptime(travel_date, '%Y-%m-%d').date()
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid date format. Use YYYY-MM-DD.') from error

    day_start = datetime.combine(date_value, time.min)
    day_end = datetime.combine(date_value, time.max)

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
        .filter(Flight.status.in_(['Scheduled', 'Delayed']))
    )

    sort_column = Flight.base_price if sort_by == 'price' else Route.estimated_duration_minutes
    ordering = asc(sort_column) if sort_order == 'asc' else desc(sort_column)
    records = query.order_by(ordering).all()

    return [
        FlightSearchResponse(
            flight_id=row.flight_id,
            flight_number=row.flight_number,
            origin_code=row.origin_code,
            destination_code=row.dest_code,
            departure_time=row.departure_time,
            arrival_time=row.arrival_time,
            duration_minutes=row.estimated_duration_minutes,
            price=float(row.base_price),
            available_seats=row.available_seats,
            status=row.status,
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

    if current_user.role != 'Admin' and current_user.user_id != payload.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You can only create bookings for your own user account.')

    passenger = db.query(Passenger).filter(Passenger.passenger_id == payload.passenger_id).first()
    if not passenger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Passenger not found.')

    flight = db.query(Flight).filter(Flight.flight_id == payload.flight_id).first()
    if not flight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Flight not found.')

    if flight.departure_time <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Cannot book a departed flight.')

    active_lock = (
        db.query(SeatLock)
        .filter(SeatLock.flight_id == payload.flight_id)
        .filter(SeatLock.seat_number == payload.seat_number)
        .filter(SeatLock.locked_by_user_id == payload.user_id)
        .filter(SeatLock.expires_at > now)
        .first()
    )
    if not active_lock:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Active seat lock required before booking.')

    total_amount = float(flight.base_price) + payload.tax_amount + payload.service_charge
    booking_reference = _generate_booking_reference(db)

    booking = Booking(
        booking_reference=booking_reference,
        passenger_id=payload.passenger_id,
        flight_id=payload.flight_id,
        booking_date=now,
        seat_number=payload.seat_number,
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
    _: AppUser = Depends(require_roles('Admin')),
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
    db.commit()
    return AdminMessageResponse(message='Route created successfully.')


@app.post('/admin/aircraft', response_model=AdminMessageResponse, status_code=status.HTTP_201_CREATED)
def admin_create_aircraft(
    payload: AdminCreateAircraftRequest,
    db: Session = Depends(get_db),
    _: AppUser = Depends(require_roles('Admin')),
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
    db.commit()
    return AdminMessageResponse(message='Aircraft added successfully.')


@app.post('/admin/flights', response_model=AdminMessageResponse, status_code=status.HTTP_201_CREATED)
def admin_create_flight(
    payload: AdminCreateFlightRequest,
    db: Session = Depends(get_db),
    _: AppUser = Depends(require_roles('Admin')),
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
    db.commit()
    return AdminMessageResponse(message='Flight schedule created successfully.')


@app.patch('/admin/flights/{flight_id}', response_model=AdminMessageResponse)
def admin_update_flight(
    flight_id: int,
    payload: AdminUpdateFlightRequest,
    db: Session = Depends(get_db),
    _: AppUser = Depends(require_roles('Admin')),
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

    db.commit()
    return AdminMessageResponse(message='Flight updated successfully.')


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
