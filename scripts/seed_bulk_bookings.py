
"""
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import random
import string
from pathlib import Path

import pymysql
from dotenv import load_dotenv

CLASS_MULTIPLIER = {
    "Economy": 1.0,
    "Business": 1.8,
    "First": 2.35,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed synthetic bookings for many flights")
    parser.add_argument("--bookings-per-flight", type=int, default=3, help="Bookings to create per selected flight")
    parser.add_argument("--max-flights", type=int, default=120, help="Maximum number of future flights to process")
    parser.add_argument("--all-flights", action="store_true", help="Process all eligible future flights")
    parser.add_argument("--target-passenger-id", type=int, default=0, help="If set, create all bookings for this passenger")
    parser.add_argument("--auto-create-passengers", type=int, default=200, help="Create this many synthetic passengers when needed")
    parser.add_argument("--skip-passenger-creation", action="store_true", help="Do not create passengers if table is empty")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for repeatable data generation")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no inserts")
    return parser.parse_args()


def load_environment() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / "backend" / ".env")
    load_dotenv(repo_root / ".env")


def db_connect() -> pymysql.Connection:
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "airline_reservation"),
        autocommit=False,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def seat_candidates(capacity: int) -> list[str]:
    letters = ["A", "B", "C", "D", "E", "F"]
    seats: list[str] = []
    rows = (capacity + len(letters) - 1) // len(letters)
    for row in range(1, rows + 1):
        for letter in letters:
            seats.append(f"{row}{letter}")
    return seats[:capacity]


def seats_for_class(capacity: int, business_seats: int, class_type: str) -> list[str]:
    all_seats = seat_candidates(capacity)
    business_cap = max(0, min(business_seats, capacity))
    first_cap = min(8, business_cap)

    if class_type == "First":
        return all_seats[:first_cap]
    if class_type == "Business":
        return all_seats[first_cap:business_cap]
    return all_seats[business_cap:]


def random_pnr(existing: set[str]) -> str:
    while True:
        value = "BK" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if value not in existing:
            existing.add(value)
            return value


def random_txn_ref(existing: set[str]) -> str:
    while True:
        value = "TXN-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=12))
        if value not in existing:
            existing.add(value)
            return value


def ensure_passengers(cur: pymysql.cursors.DictCursor, count: int) -> None:
    now = dt.datetime.now()
    for idx in range(count):
        suffix = f"{now:%m%d%H%M}{idx:03d}"
        email = f"demo.pax.{suffix}@example.com"
        passport = f"DM{suffix}"
        phone = f"9{random.randint(100000000, 999999999)}"
        cur.execute(
            """
            INSERT INTO passenger
                (first_name, last_name, email, phone, passport_number, date_of_birth, address)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                f"Demo{idx + 1}",
                "Passenger",
                email,
                phone,
                passport,
                dt.date(1990, 1, 1),
                "Generated for demo bookings",
            ),
        )


def load_passenger_ids(cur: pymysql.cursors.DictCursor, target_passenger_id: int) -> list[int]:
    if target_passenger_id > 0:
        cur.execute("SELECT passenger_id FROM passenger WHERE passenger_id = %s", (target_passenger_id,))
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f"Passenger {target_passenger_id} was not found.")
        return [int(row["passenger_id"])]

    cur.execute("SELECT passenger_id FROM passenger ORDER BY passenger_id")
    rows = cur.fetchall()
    return [int(r["passenger_id"]) for r in rows]


def main() -> int:
    args = parse_args()
    load_environment()
    random.seed(args.seed)

    conn = db_connect()
    created_bookings = 0
    created_payments = 0
    skipped_flights = 0

    try:
        with conn.cursor() as cur:
            passenger_ids = load_passenger_ids(cur, args.target_passenger_id)
            if not passenger_ids and args.auto_create_passengers > 0 and not args.skip_passenger_creation:
                print(f"Creating {args.auto_create_passengers} synthetic passengers...")
                ensure_passengers(cur, args.auto_create_passengers)
                conn.commit()
                passenger_ids = load_passenger_ids(cur, args.target_passenger_id)

            if not passenger_ids:
                raise RuntimeError("No passengers available. Add passengers or use --auto-create-passengers.")

            if args.all_flights:
                cur.execute(
                    """
                    SELECT
                        f.flight_id,
                        f.base_price,
                        f.available_seats,
                        a.total_capacity,
                        a.business_seats
                    FROM flight f
                    JOIN aircraft a ON a.aircraft_id = f.aircraft_id
                    WHERE f.departure_time > NOW()
                      AND f.status IN ('Scheduled', 'Delayed')
                      AND f.available_seats > 0
                    ORDER BY f.departure_time ASC
                    """
                )
            else:
                cur.execute(
                    """
                    SELECT
                        f.flight_id,
                        f.base_price,
                        f.available_seats,
                        a.total_capacity,
                        a.business_seats
                    FROM flight f
                    JOIN aircraft a ON a.aircraft_id = f.aircraft_id
                    WHERE f.departure_time > NOW()
                      AND f.status IN ('Scheduled', 'Delayed')
                      AND f.available_seats > 0
                    ORDER BY f.departure_time ASC
                    LIMIT %s
                    """,
                    (args.max_flights,),
                )
            flights = cur.fetchall()

            if not flights:
                print("No eligible future flights found.")
                return 0

            flight_ids = [int(f["flight_id"]) for f in flights]
            placeholders = ",".join(["%s"] * len(flight_ids))
            cur.execute(
                f"""
                SELECT flight_id, seat_number
                FROM booking
                WHERE flight_id IN ({placeholders})
                  AND status IN ('Pending', 'Confirmed')
                """,
                tuple(flight_ids),
            )
            booked_rows = cur.fetchall()

            booked_by_flight: dict[int, set[str]] = {}
            for row in booked_rows:
                flight_id = int(row["flight_id"])
                seat = str(row["seat_number"]).upper()
                booked_by_flight.setdefault(flight_id, set()).add(seat)

            cur.execute("SELECT booking_reference FROM booking")
            pnr_existing = {str(r["booking_reference"]) for r in cur.fetchall()}
            cur.execute("SELECT transaction_reference FROM payment")
            txn_existing = {str(r["transaction_reference"]) for r in cur.fetchall()}

            passenger_cursor = 0
            payment_methods = ["UPI", "CreditCard", "DebitCard", "NetBanking", "Wallet"]

            for flight in flights:
                flight_id = int(flight["flight_id"])
                capacity = int(flight["total_capacity"])
                business_seats = int(flight["business_seats"])
                available_seats = int(flight["available_seats"])
                base_price = float(flight["base_price"])

                occupied = booked_by_flight.setdefault(flight_id, set())
                target = min(args.bookings_per_flight, max(0, available_seats), max(0, capacity - len(occupied)))
                if target <= 0:
                    skipped_flights += 1
                    continue

                for _ in range(target):
                    # Weighted towards economy, but still populate premium cabins.
                    class_draw = random.random()
                    class_type = "Economy"
                    if class_draw < 0.06:
                        class_type = "First"
                    elif class_draw < 0.24:
                        class_type = "Business"

                    class_seats = [s for s in seats_for_class(capacity, business_seats, class_type) if s not in occupied]
                    if not class_seats:
                        # Fallback to any available seat if that cabin is exhausted.
                        class_type = "Economy"
                        class_seats = [s for s in seats_for_class(capacity, business_seats, "Economy") if s not in occupied]
                    if not class_seats:
                        break

                    seat_number = random.choice(class_seats)
                    occupied.add(seat_number)

                    passenger_id = passenger_ids[passenger_cursor % len(passenger_ids)]
                    passenger_cursor += 1

                    total = round((base_price * CLASS_MULTIPLIER[class_type]) + 500.0 + 150.0, 2)
                    pnr = random_pnr(pnr_existing)

                    if args.dry_run:
                        created_bookings += 1
                        created_payments += 1
                        continue

                    cur.execute(
                        """
                        INSERT INTO booking
                            (booking_reference, passenger_id, flight_id, seat_number, class_type, status, total_amount)
                        VALUES
                            (%s, %s, %s, %s, %s, 'Confirmed', %s)
                        """,
                        (pnr, passenger_id, flight_id, seat_number, class_type, total),
                    )
                    booking_id = int(cur.lastrowid)

                    cur.execute(
                        """
                        INSERT INTO payment
                            (booking_id, amount, payment_method, transaction_reference, payment_status)
                        VALUES
                            (%s, %s, %s, %s, 'Success')
                        """,
                        (
                            booking_id,
                            total,
                            random.choice(payment_methods),
                            random_txn_ref(txn_existing),
                        ),
                    )

                    created_bookings += 1
                    created_payments += 1

            if args.dry_run:
                conn.rollback()
            else:
                conn.commit()

            print("Bulk booking seed complete")
            print(f"- flights considered: {len(flights)}")
            print(f"- flights skipped (full/none target): {skipped_flights}")
            print(f"- bookings inserted: {created_bookings}")
            print(f"- payments inserted: {created_payments}")
            print(f"- mode: {'dry-run' if args.dry_run else 'write'}")

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
