#!/usr/bin/env python3
"""Import live flight schedules from AeroDataBox (RapidAPI) into MySQL.

Usage:
    ./.venv/Scripts/python.exe scripts/import_live_flights.py --airports DEL,BOM,BLR

Required env vars:
  RAPIDAPI_KEY

Optional env vars:
  RAPIDAPI_HOST (default: aerodatabox.p.rapidapi.com)
  DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pymysql
from dotenv import load_dotenv


MAJOR_INDIAN_AIRPORTS = [
    ("DEL", "Indira Gandhi International Airport", "Delhi"),
    ("BOM", "Chhatrapati Shivaji Maharaj International Airport", "Mumbai"),
    ("BLR", "Kempegowda International Airport", "Bengaluru"),
    ("HYD", "Rajiv Gandhi International Airport", "Hyderabad"),
    ("MAA", "Chennai International Airport", "Chennai"),
    ("CCU", "Netaji Subhas Chandra Bose International Airport", "Kolkata"),
    ("PNQ", "Pune Airport", "Pune"),
    ("GOI", "Goa International Airport", "Goa"),
    ("AMD", "Sardar Vallabhbhai Patel International Airport", "Ahmedabad"),
    ("ATQ", "Sri Guru Ram Dass Jee International Airport", "Amritsar"),
    ("COK", "Cochin International Airport", "Kochi"),
    ("JAI", "Jaipur International Airport", "Jaipur"),
    ("LKO", "Chaudhary Charan Singh International Airport", "Lucknow"),
    ("NAG", "Dr. Babasaheb Ambedkar International Airport", "Nagpur"),
    ("PAT", "Jay Prakash Narayan International Airport", "Patna"),
    ("TRV", "Trivandrum International Airport", "Thiruvananthapuram"),
    ("VNS", "Lal Bahadur Shastri International Airport", "Varanasi"),
    ("IXB", "Bagdogra Airport", "Siliguri"),
    ("IXC", "Shaheed Bhagat Singh International Airport", "Chandigarh"),
    ("IXR", "Birsa Munda Airport", "Ranchi"),
    ("UDR", "Maharana Pratap Airport", "Udaipur"),
    ("BHO", "Raja Bhoj Airport", "Bhopal"),
    ("TIR", "Tirupati Airport", "Tirupati"),
    ("SXR", "Sheikh ul-Alam International Airport", "Srinagar"),
    ("RPR", "Swami Vivekananda Airport", "Raipur"),
]


# Approximate airport coordinates for better synthetic distance estimation.
AIRPORT_COORDS = {
    "DEL": (28.5562, 77.1000),
    "BOM": (19.0896, 72.8656),
    "BLR": (13.1986, 77.7066),
    "HYD": (17.2403, 78.4294),
    "MAA": (12.9900, 80.1693),
    "CCU": (22.6547, 88.4467),
    "PNQ": (18.5822, 73.9197),
    "GOI": (15.3808, 73.8314),
    "AMD": (23.0772, 72.6347),
    "ATQ": (31.7096, 74.7973),
    "COK": (10.1520, 76.3910),
    "JAI": (26.8242, 75.8122),
    "LKO": (26.7606, 80.8893),
    "NAG": (21.0922, 79.0472),
    "PAT": (25.5913, 85.0870),
    "TRV": (8.4821, 76.9201),
    "VNS": (25.4524, 82.8593),
    "IXB": (26.6812, 88.3286),
    "IXC": (30.6735, 76.7885),
    "IXR": (23.3143, 85.3217),
    "UDR": (24.6177, 73.8961),
    "BHO": (23.2875, 77.3374),
    "TIR": (13.6325, 79.5433),
    "SXR": (33.9871, 74.7742),
    "RPR": (21.1804, 81.7398),
    "GAU": (26.1061, 91.5859),
    "IDR": (22.7218, 75.8011),
    "IXM": (9.8345, 78.0934),
    "BBI": (20.2444, 85.8178),
    "CJB": (11.0310, 77.0434),
    "VTZ": (17.7212, 83.2245),
}

BUSY_AIRPORTS = {"DEL", "BOM", "BLR", "HYD", "MAA", "CCU"}
LOW_COST_CARRIERS = {"6E", "SG", "G8", "I5", "QP", "AK"}
FULL_SERVICE_CARRIERS = {"AI", "UK", "IX"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import flights from AeroDataBox into local schema")
    parser.add_argument(
        "--country",
        default="IN",
        help="Country code/name to import airports for (default: IN). Ignored if --airports is provided.",
    )
    parser.add_argument(
        "--airports",
        default="",
        help="Comma-separated IATA airport codes to fetch departures for",
    )
    parser.add_argument(
        "--hours-ahead",
        type=int,
        default=24,
        help="Time window (hours) from now for departure schedules",
    )
    parser.add_argument(
        "--default-base-price",
        type=float,
        default=5200.0,
        help="Fallback base price when provider does not include fare",
    )
    parser.add_argument(
        "--max-per-airport",
        type=int,
        default=60,
        help="Max flights ingested per airport in one run",
    )
    parser.add_argument(
        "--reprice-existing-future",
        action="store_true",
        help="Recalculate fares for all future flights using the current pricing model",
    )
    parser.add_argument(
        "--sleep-ms",
        type=int,
        default=1500,
        help="Delay between API calls to reduce rate-limit issues",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Retries per airport when API returns 429",
    )
    parser.add_argument(
        "--retry-backoff-seconds",
        type=float,
        default=2.0,
        help="Base backoff seconds for 429 retry (exponential)",
    )
    return parser.parse_args()


def load_environment() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / "backend" / ".env")
    load_dotenv(repo_root / ".env")


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def deep_get(data: dict, path: list[str], default=None):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def parse_local_datetime(raw: str | None) -> dt.datetime | None:
    if not raw:
        return None

    cleaned = raw.strip().replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(cleaned)
    except ValueError:
        return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def normalize_status(raw: str | None) -> str:
    value = (raw or "").lower()
    if "cancel" in value:
        return "Cancelled"
    if "delay" in value:
        return "Delayed"
    if "depart" in value or "airborne" in value:
        return "Departed"
    return "Scheduled"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def estimate_distance_km(origin: str, dest: str) -> int:
    origin_coords = AIRPORT_COORDS.get(origin)
    dest_coords = AIRPORT_COORDS.get(dest)
    if origin_coords and dest_coords:
        distance = haversine_km(origin_coords[0], origin_coords[1], dest_coords[0], dest_coords[1])
        # Route flown is typically longer than great-circle due to airways/vectoring.
        return int(round(max(120.0, distance * 1.10)))

    # Deterministic fallback for unknown airport pairs.
    route_seed = f"{origin}:{dest}"
    digest = hashlib.sha256(route_seed.encode("utf-8")).hexdigest()
    scaled = int(digest[:8], 16) / 0xFFFFFFFF
    return int(round(300 + (scaled * 2100)))


def estimate_duration_minutes(distance_km: int) -> int:
    # Approximate gate-to-gate time: cruise + taxi/holding buffers.
    cruise_speed_kmph = 760.0
    cruise_minutes = (max(distance_km, 120) / cruise_speed_kmph) * 60.0
    duration = 28.0 + cruise_minutes + 12.0
    return int(round(max(50.0, min(duration, 360.0))))


def carrier_code_from_flight_number(flight_number: str) -> str:
    return "".join(ch for ch in str(flight_number).upper() if ch.isalpha())[:2]


def estimate_base_price(
    distance_km: int,
    route_duration_minutes: int,
    scheduled_duration_minutes: int,
    departure_time: dt.datetime,
    flight_number: str,
    origin_iata: str,
    dest_iata: str,
    fallback_floor: float,
) -> float:
    effective_distance = max(distance_km, 120)
    block_minutes = max(scheduled_duration_minutes or route_duration_minutes, 45)

    # Base fare model for Indian domestic economy segment.
    base = 900.0 + (effective_distance * 3.95) + (block_minutes * 9.2)

    # Time-of-day demand multiplier.
    hour = departure_time.hour
    time_multiplier = 1.0
    if 6 <= hour < 10 or 17 <= hour < 22:
        time_multiplier = 1.14
    elif 10 <= hour < 16:
        time_multiplier = 1.04
    elif 0 <= hour < 5:
        time_multiplier = 0.88

    # Weekend tends to have slightly higher fares.
    weekend_multiplier = 1.06 if departure_time.weekday() >= 5 else 1.0

    # Dynamic pricing by days remaining to departure.
    now = dt.datetime.now()
    days_to_departure = max((departure_time.date() - now.date()).days, 0)
    if days_to_departure <= 2:
        advance_multiplier = 1.32
    elif days_to_departure <= 7:
        advance_multiplier = 1.20
    elif days_to_departure <= 14:
        advance_multiplier = 1.12
    elif days_to_departure <= 30:
        advance_multiplier = 1.05
    elif days_to_departure >= 60:
        advance_multiplier = 0.93
    else:
        advance_multiplier = 1.0

    # High-demand metro routes have stronger pricing power.
    route_demand_multiplier = 1.0
    if origin_iata in BUSY_AIRPORTS and dest_iata in BUSY_AIRPORTS:
        route_demand_multiplier = 1.08
    elif origin_iata in BUSY_AIRPORTS or dest_iata in BUSY_AIRPORTS:
        route_demand_multiplier = 1.04

    # Airline positioning (LCC vs full-service) influences median fare.
    carrier_code = carrier_code_from_flight_number(flight_number)
    carrier_multiplier = 1.0
    if carrier_code in LOW_COST_CARRIERS:
        carrier_multiplier = 0.90
    elif carrier_code in FULL_SERVICE_CARRIERS:
        carrier_multiplier = 1.06

    # Stable pseudo-random route/flight variance so prices are not uniform.
    seed = f"{flight_number}|{departure_time.date().isoformat()}|{origin_iata}|{dest_iata}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    scaled = int(digest[:8], 16) / 0xFFFFFFFF
    variance_multiplier = 0.95 + (scaled * 0.12)  # 0.95 to 1.07

    estimated = (
        base
        * time_multiplier
        * weekend_multiplier
        * advance_multiplier
        * route_demand_multiplier
        * carrier_multiplier
        * variance_multiplier
    )

    # If route metrics are missing, use fallback as a neutral anchor.
    if distance_km <= 0 and route_duration_minutes <= 0 and scheduled_duration_minutes <= 0:
        estimated = float(fallback_floor)

    estimated = max(estimated, 1500.0)
    estimated = min(estimated, 22000.0)
    return round(estimated, 2)


class ApiHttpError(RuntimeError):
    def __init__(self, status: int, body: str, retry_after: float | None = None) -> None:
        self.status = status
        self.body = body
        self.retry_after = retry_after
        super().__init__(f"HTTP {status}: {body[:200]}")


def fetch_departures(
    rapid_key: str,
    rapid_host: str,
    iata_code: str,
    from_iso: str,
    to_iso: str,
) -> list[dict]:
    # Endpoint reference (RapidAPI AeroDataBox):
    # /flights/airports/iata/{code}/{fromLocal}/{toLocal}
    path = f"/flights/airports/iata/{iata_code}/{from_iso}/{to_iso}"
    query = urllib.parse.urlencode(
        {
            "withLeg": "true",
            "direction": "Departure",
            "withCancelled": "false",
            "withCargo": "false",
            "withPrivate": "false",
        }
    )
    url = f"https://{rapid_host}{path}?{query}"
    req = urllib.request.Request(
        url,
        headers={
            "X-RapidAPI-Key": rapid_key,
            "X-RapidAPI-Host": rapid_host,
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = resp.read().decode("utf-8")
            try:
                payload = json.loads(body)
            except json.JSONDecodeError as exc:
                raise ApiHttpError(502, body) from exc
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        retry_after = None
        if exc.headers:
            raw_retry_after = exc.headers.get("Retry-After")
            if raw_retry_after:
                try:
                    retry_after = float(raw_retry_after)
                except ValueError:
                    retry_after = None
        raise ApiHttpError(exc.code, error_body, retry_after) from exc

    departures = payload.get("departures", [])
    return departures if isinstance(departures, list) else []


def connect_db() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "airline_reservation"),
        port=int(os.getenv("DB_PORT", "3306")),
        charset="utf8mb4",
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )


def resolve_airports(cur, airport_arg: str, country_arg: str) -> list[str]:
    if airport_arg.strip():
        return [code.strip().upper() for code in airport_arg.split(",") if code.strip()]

    country_norm = (country_arg or "IN").strip().upper()
    country_aliases = {
        "IN": "India",
        "IND": "India",
        "INDIA": "India",
    }
    country_lookup = country_aliases.get(country_norm, country_arg.strip())

    cur.execute(
        "SELECT airport_code FROM airport WHERE UPPER(country) = UPPER(%s) ORDER BY airport_code",
        (country_lookup,),
    )
    rows = cur.fetchall() or []
    return [str(row["airport_code"]).upper() for row in rows]


def ensure_major_indian_airports(cur) -> None:
    for code, name, city in MAJOR_INDIAN_AIRPORTS:
        cur.execute("SELECT airport_code FROM airport WHERE airport_code = %s", (code,))
        if cur.fetchone():
            continue

        cur.execute(
            "INSERT INTO airport (airport_code, name, city, country, timezone) VALUES (%s, %s, %s, %s, %s)",
            (code, name, city, "India", "Asia/Kolkata"),
        )


def get_or_create_airline(cur, code: str | None, name: str | None) -> int:
    code_norm = (code or "UNK").upper()[:3] or "UNK"
    name_norm = (name or f"Airline {code_norm}")[:100]

    cur.execute("SELECT airline_id FROM airline WHERE code = %s", (code_norm,))
    row = cur.fetchone()
    if row:
        return int(row["airline_id"])

    cur.execute("INSERT INTO airline (name, code) VALUES (%s, %s)", (name_norm, code_norm))
    return int(cur.lastrowid)


def get_or_create_airport(cur, code: str, name: str | None, city: str | None, country: str | None) -> None:
    code_norm = code.upper()[:3]
    if len(code_norm) != 3:
        raise ValueError("Invalid airport code")

    cur.execute("SELECT airport_code FROM airport WHERE airport_code = %s", (code_norm,))
    if cur.fetchone():
        return

    cur.execute(
        "INSERT INTO airport (airport_code, name, city, country, timezone) VALUES (%s, %s, %s, %s, %s)",
        (
            code_norm,
            (name or f"Airport {code_norm}")[:100],
            (city or code_norm)[:50],
            (country or "India")[:50],
            "Asia/Kolkata",
        ),
    )


def get_or_create_route(cur, origin: str, dest: str) -> tuple[int, int, int]:
    cur.execute(
        "SELECT route_id, distance_km, estimated_duration_minutes FROM route WHERE origin_code = %s AND dest_code = %s",
        (origin, dest),
    )
    row = cur.fetchone()
    if row:
        return int(row["route_id"]), int(row["distance_km"]), int(row["estimated_duration_minutes"])

    distance = estimate_distance_km(origin, dest)
    duration = estimate_duration_minutes(distance)
    cur.execute(
        "INSERT INTO route (origin_code, dest_code, distance_km, estimated_duration_minutes) VALUES (%s, %s, %s, %s)",
        (origin, dest, distance, duration),
    )
    return int(cur.lastrowid), distance, duration


def pick_aircraft_for_airline(cur, airline_id: int) -> tuple[int, int]:
    cur.execute(
        "SELECT aircraft_id, total_capacity FROM aircraft WHERE airline_id = %s ORDER BY aircraft_id LIMIT 1",
        (airline_id,),
    )
    row = cur.fetchone()
    if row:
        return int(row["aircraft_id"]), int(row["total_capacity"])

    cur.execute("SELECT aircraft_id, total_capacity FROM aircraft ORDER BY aircraft_id LIMIT 1")
    fallback = cur.fetchone()
    if not fallback:
        raise RuntimeError("No aircraft available in DB. Seed aircraft data first.")
    return int(fallback["aircraft_id"]), int(fallback["total_capacity"])


def get_or_create_import_aircraft(cur, airline_id: int, flight_number: str) -> tuple[int, int]:
    code = "".join(ch for ch in flight_number.upper() if ch.isalnum())[:10] or "GEN"
    registration = f"IM{airline_id}{code}"[:20]

    cur.execute(
        "SELECT aircraft_id, total_capacity FROM aircraft WHERE registration_number = %s",
        (registration,),
    )
    row = cur.fetchone()
    if row:
        return int(row["aircraft_id"]), int(row["total_capacity"])

    capacity = 180
    business = 20
    economy = 160
    cur.execute(
        """
        INSERT INTO aircraft (registration_number, model, manufacturer, total_capacity, business_seats, economy_seats, airline_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (registration, "A320neo", "Airbus", capacity, business, economy, airline_id),
    )
    return int(cur.lastrowid), capacity


def upsert_flight(
    cur,
    flight_number: str,
    route_id: int,
    aircraft_id: int,
    departure_time: dt.datetime,
    arrival_time: dt.datetime,
    base_price: float,
    status: str,
    available_seats: int,
) -> str:
    cur.execute(
        "SELECT flight_id FROM flight WHERE flight_number = %s AND departure_time = %s LIMIT 1",
        (flight_number, departure_time),
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            """
            UPDATE flight
            SET route_id = %s,
                aircraft_id = %s,
                arrival_time = %s,
                base_price = %s,
                status = %s,
                available_seats = %s
            WHERE flight_id = %s
            """,
            (route_id, aircraft_id, arrival_time, base_price, status, available_seats, int(row["flight_id"])),
        )
        return "updated"

    cur.execute(
        """
        INSERT INTO flight
            (flight_number, route_id, aircraft_id, departure_time, arrival_time, base_price, status, available_seats)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (flight_number, route_id, aircraft_id, departure_time, arrival_time, base_price, status, available_seats),
    )
    return "inserted"


def reprice_existing_future_flights(cur, fallback_floor: float) -> int:
    cur.execute(
        """
        SELECT f.flight_id,
               f.flight_number,
               f.departure_time,
               f.arrival_time,
               r.distance_km,
               r.estimated_duration_minutes,
               r.origin_code,
               r.dest_code
        FROM flight f
        JOIN route r ON r.route_id = f.route_id
        WHERE f.departure_time >= NOW()
        """
    )
    rows = cur.fetchall() or []
    updated_count = 0

    for row in rows:
        dep_time = row["departure_time"]
        arr_time = row["arrival_time"]
        scheduled_duration = 0
        if dep_time and arr_time and arr_time > dep_time:
            scheduled_duration = int((arr_time - dep_time).total_seconds() // 60)

        new_price = estimate_base_price(
            int(row["distance_km"]),
            int(row["estimated_duration_minutes"]),
            scheduled_duration,
            dep_time,
            str(row["flight_number"]),
            str(row["origin_code"]),
            str(row["dest_code"]),
            fallback_floor,
        )
        cur.execute("UPDATE flight SET base_price = %s WHERE flight_id = %s", (new_price, int(row["flight_id"])))
        updated_count += 1

    return updated_count


def main() -> int:
    load_environment()
    args = parse_args()

    rapid_key = require_env("RAPIDAPI_KEY")
    rapid_host = os.getenv("RAPIDAPI_HOST", "aerodatabox.p.rapidapi.com").strip() or "aerodatabox.p.rapidapi.com"

    start = dt.datetime.now().replace(minute=0, second=0, microsecond=0)
    end = start + dt.timedelta(hours=args.hours_ahead)
    from_iso = start.strftime("%Y-%m-%dT%H:%M")
    to_iso = end.strftime("%Y-%m-%dT%H:%M")

    print("AeroDataBox import starting...")
    print(f"Window: {from_iso} -> {to_iso}")
    if args.airports.strip():
        print(f"Airports: {args.airports}")
    else:
        print(f"Country: {args.country}")

    conn = connect_db()
    inserted = 0
    updated = 0
    skipped = 0

    try:
        with conn.cursor() as cur:
            if (args.country or "").strip().upper() in {"IN", "IND", "INDIA"} and not args.airports.strip():
                ensure_major_indian_airports(cur)

            airports = resolve_airports(cur, args.airports, args.country)
            if not airports:
                raise RuntimeError(
                    f"No airports found for country={args.country!r}. Seed airport data first or pass --airports explicitly."
                )

            print(f"Resolved airports: {', '.join(airports)}")

            for airport_code in airports:
                flights: list[dict] | None = None
                for attempt in range(1, max(args.max_retries, 1) + 1):
                    try:
                        flights = fetch_departures(rapid_key, rapid_host, airport_code, from_iso, to_iso)
                        break
                    except ApiHttpError as exc:
                        if exc.status == 429 and attempt < max(args.max_retries, 1):
                            wait_seconds = exc.retry_after if exc.retry_after is not None else args.retry_backoff_seconds * (2 ** (attempt - 1))
                            print(f"[WARN] {airport_code}: HTTP 429 rate-limited, retrying in {wait_seconds:.1f}s (attempt {attempt}/{args.max_retries})")
                            time.sleep(max(wait_seconds, 0.5))
                            continue

                        body_snippet = (exc.body or "").strip().replace("\n", " ")[:240]
                        if exc.status == 403:
                            print(
                                f"[WARN] API error for {airport_code}: HTTP 403. "
                                "Likely invalid key, missing RapidAPI subscription, or endpoint not included in your plan."
                            )
                        else:
                            print(f"[WARN] API error for {airport_code}: HTTP {exc.status}")

                        if body_snippet:
                            print(f"       response: {body_snippet}")

                        skipped += 1
                        break
                    except Exception as exc:  # noqa: BLE001
                        print(f"[WARN] API error for {airport_code}: {exc}")
                        skipped += 1
                        break

                if flights is None:
                    time.sleep(max(args.sleep_ms, 0) / 1000.0)
                    continue

                count = 0
                for rec in flights:
                    if count >= args.max_per_airport:
                        break

                    flight_number = rec.get("number") or rec.get("callSign")
                    if not flight_number:
                        skipped += 1
                        continue

                    dep_time = parse_local_datetime(
                        deep_get(rec, ["departure", "scheduledTime", "local"]) or deep_get(rec, ["departure", "scheduledTime", "utc"])
                    )
                    arr_time = parse_local_datetime(
                        deep_get(rec, ["arrival", "scheduledTime", "local"]) or deep_get(rec, ["arrival", "scheduledTime", "utc"])
                    )

                    if not dep_time or not arr_time or arr_time <= dep_time:
                        skipped += 1
                        continue

                    origin_iata = (deep_get(rec, ["departure", "airport", "iata"]) or airport_code).upper()
                    dest_iata = (deep_get(rec, ["arrival", "airport", "iata"]) or "").upper()
                    if len(origin_iata) != 3 or len(dest_iata) != 3 or origin_iata == dest_iata:
                        skipped += 1
                        continue

                    airline_iata = deep_get(rec, ["airline", "iata"])
                    airline_name = deep_get(rec, ["airline", "name"])

                    try:
                        get_or_create_airport(
                            cur,
                            origin_iata,
                            deep_get(rec, ["departure", "airport", "name"]),
                            deep_get(rec, ["departure", "airport", "municipalityName"]),
                            deep_get(rec, ["departure", "airport", "countryCode"]),
                        )
                        get_or_create_airport(
                            cur,
                            dest_iata,
                            deep_get(rec, ["arrival", "airport", "name"]),
                            deep_get(rec, ["arrival", "airport", "municipalityName"]),
                            deep_get(rec, ["arrival", "airport", "countryCode"]),
                        )

                        airline_id = get_or_create_airline(cur, airline_iata, airline_name)
                        route_id, route_distance, route_duration = get_or_create_route(cur, origin_iata, dest_iata)
                        aircraft_id, capacity = get_or_create_import_aircraft(cur, airline_id, str(flight_number))

                        flight_status = normalize_status(rec.get("status"))
                        scheduled_duration = int((arr_time - dep_time).total_seconds() // 60)
                        base_price = estimate_base_price(
                            route_distance,
                            route_duration,
                            scheduled_duration,
                            dep_time,
                            str(flight_number),
                            origin_iata,
                            dest_iata,
                            args.default_base_price,
                        )

                        result = upsert_flight(
                            cur,
                            str(flight_number)[:10],
                            route_id,
                            aircraft_id,
                            dep_time,
                            arr_time,
                            base_price,
                            flight_status,
                            capacity,
                        )
                        if result == "inserted":
                            inserted += 1
                        else:
                            updated += 1
                        count += 1
                    except Exception as exc:  # noqa: BLE001
                        skipped += 1
                        print(f"[WARN] skipped {flight_number}: {exc}")

                time.sleep(max(args.sleep_ms, 0) / 1000.0)

            if args.reprice_existing_future:
                repriced = reprice_existing_future_flights(cur, args.default_base_price)
                print(f"Repriced future flights: {repriced}")

            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print("Import complete")
    print(f"- inserted: {inserted}")
    print(f"- updated: {updated}")
    print(f"- skipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
