from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    passport_number: str = Field(min_length=5, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    age: int | None = Field(default=None, ge=0)
    address: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class CurrentUserResponse(BaseModel):
    user_id: int
    email: str
    role: str
    passenger_id: int | None = None


class FlightSearchResponse(BaseModel):
    flight_id: int
    flight_number: str
    origin_code: str
    destination_code: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    price: float
    available_seats: int
    status: str


class AirportOptionResponse(BaseModel):
    airport_code: str
    city: str
    name: str
    country: str


class SeatLockRequest(BaseModel):
    user_id: int
    flight_id: int
    seat_number: str = Field(min_length=1, max_length=5)
    lock_minutes: int = Field(default=10, ge=1, le=30)


class SeatLockResponse(BaseModel):
    lock_id: int
    flight_id: int
    seat_number: str
    expires_at: datetime


class CreateBookingRequest(BaseModel):
    passenger_id: int
    user_id: int
    flight_id: int
    seat_number: str | None = Field(default=None, min_length=1, max_length=5)
    class_type: str = Field(pattern='^(Economy|Business|First)$')
    payment_method: str = Field(pattern='^(CreditCard|DebitCard|UPI|NetBanking|Wallet)$')
    transaction_reference: str = Field(min_length=5, max_length=50)
    tax_amount: float = Field(default=0, ge=0)
    service_charge: float = Field(default=0, ge=0)
    random_allotment: bool = False
    use_seat_lock: bool = False


class CreateBookingResponse(BaseModel):
    booking_reference: str
    booking_id: int
    status: str
    total_amount: float


class BookingDetailResponse(BaseModel):
    booking_reference: str
    passenger_name: str
    flight_number: str
    departure_time: datetime
    arrival_time: datetime
    seat_number: str
    class_type: str
    booking_status: str
    total_amount: float


class CancelBookingRequest(BaseModel):
    reason: str = Field(default='User requested cancellation', max_length=255)


class CancelBookingResponse(BaseModel):
    booking_reference: str
    booking_status: str
    refund_amount: float
    refund_status: str


class AdminCreateRouteRequest(BaseModel):
    origin_code: str = Field(min_length=3, max_length=3)
    dest_code: str = Field(min_length=3, max_length=3)
    distance_km: int = Field(ge=1)
    estimated_duration_minutes: int = Field(ge=1)


class AdminCreateAircraftRequest(BaseModel):
    registration_number: str = Field(min_length=3, max_length=20)
    model: str = Field(min_length=2, max_length=50)
    manufacturer: str = Field(min_length=2, max_length=50)
    total_capacity: int = Field(ge=1)
    business_seats: int = Field(ge=0)
    economy_seats: int = Field(ge=0)
    airline_id: int = Field(ge=1)


class AdminCreateFlightRequest(BaseModel):
    flight_number: str = Field(min_length=2, max_length=10)
    route_id: int = Field(ge=1)
    aircraft_id: int = Field(ge=1)
    departure_time: datetime
    arrival_time: datetime
    base_price: float = Field(ge=0)


class AdminUpdateFlightRequest(BaseModel):
    departure_time: datetime | None = None
    arrival_time: datetime | None = None
    base_price: float | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, pattern='^(Scheduled|Delayed|Cancelled|Departed)$')


class AdminMessageResponse(BaseModel):
    message: str


class ManifestEntryResponse(BaseModel):
    booking_reference: str
    passenger_name: str
    seat_number: str
    class_type: str
    booking_status: str


class DashboardSummaryResponse(BaseModel):
    total_bookings: int
    confirmed_bookings: int
    total_revenue: float
    average_occupancy_percent: float


