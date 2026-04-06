#!/usr/bin/env python3
"""End-to-end smoke test for Airline Reservation System APIs.

Checks:
1) Passenger API health
2) Register a new passenger user
3) Login + /auth/me
4) Airports list
5) Flight search (for provided date)
6) Booking attempt (if a future flight is available)
7) Admin summary endpoint (Java/Tomcat)

Usage (from repo root):
  .\\.venv\\Scripts\\python.exe scripts\\smoke_test.py

Optional:
  .\\.venv\\Scripts\\python.exe scripts\\smoke_test.py --travel-date 2026-12-25
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import string
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass
class StepResult:
    name: str
    ok: bool
    message: str


class HttpClient:
    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout

    def request(
        self,
        method: str,
        url: str,
        payload: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict | list | str | None]:
        data = None
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(url=url, data=data, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8") if resp.length != 0 else ""
                parsed = self._parse_json_or_text(body)
                return resp.status, parsed
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8") if exc.fp else ""
            parsed = self._parse_json_or_text(body)
            return exc.code, parsed
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Connection error for {url}: {exc.reason}") from exc

    @staticmethod
    def _parse_json_or_text(body: str) -> dict | list | str | None:
        if not body:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body


def random_suffix(length: int = 8) -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def first_bookable_flight(flights: list[dict]) -> dict | None:
    now = dt.datetime.now()
    for flight in flights:
        dep_raw = flight.get("departure_time")
        if not dep_raw:
            continue
        try:
            dep = dt.datetime.fromisoformat(str(dep_raw))
        except ValueError:
            continue
        if dep > now:
            return flight
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test for DBMS+FLEXI services")
    parser.add_argument("--passenger-base", default="http://127.0.0.1:8000", help="FastAPI base URL")
    parser.add_argument("--admin-base", default="http://localhost:8080/admin", help="Tomcat admin base URL")
    parser.add_argument(
        "--travel-date",
        default=dt.date.today().isoformat(),
        help="Date for flight search in YYYY-MM-DD (booking attempt uses this result)",
    )
    parser.add_argument("--skip-admin", action="store_true", help="Skip Java/Tomcat admin summary check")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout seconds")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = HttpClient(timeout=args.timeout)

    results: list[StepResult] = []

    suffix = random_suffix()
    email = f"smoke_{suffix}@example.com"
    password = "Smoke@Test123"
    first_name = "Smoke"
    last_name = f"User{suffix[:4]}"

    print("Running smoke test with:")
    print(f"- passenger base: {args.passenger_base}")
    print(f"- admin base: {args.admin_base}")
    print(f"- travel date: {args.travel_date}")
    print(f"- test email: {email}")
    print()

    try:
        # 1) Health
        status, body = client.request("GET", f"{args.passenger_base}/health")
        if status == 200 and isinstance(body, dict) and body.get("status") == "ok":
            results.append(StepResult("passenger_health", True, "Passenger API healthy"))
        else:
            results.append(StepResult("passenger_health", False, f"Unexpected health response: {status}, {body}"))
            return report(results)

        # 2) Register
        register_payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": f"9{random.randint(100000000, 999999999)}",
            "passport_number": f"SMK{random.randint(1000000, 9999999)}",
            "date_of_birth": "1999-01-15",
            "password": password,
            "address": "Smoke Test Lane",
        }
        status, body = client.request("POST", f"{args.passenger_base}/auth/register", register_payload)
        if status == 201:
            results.append(StepResult("register", True, "Passenger registration successful"))
        else:
            results.append(StepResult("register", False, f"Registration failed: {status}, {body}"))
            return report(results)

        # 3) Login
        status, body = client.request(
            "POST",
            f"{args.passenger_base}/auth/login",
            {"email": email, "password": password},
        )
        if status != 200 or not isinstance(body, dict) or "access_token" not in body:
            results.append(StepResult("login", False, f"Login failed: {status}, {body}"))
            return report(results)

        token = body["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}
        results.append(StepResult("login", True, "Login successful"))

        # 4) me
        status, body = client.request("GET", f"{args.passenger_base}/auth/me", headers=auth_headers)
        if status != 200 or not isinstance(body, dict) or body.get("role") != "Passenger":
            results.append(StepResult("auth_me", False, f"/auth/me failed: {status}, {body}"))
            return report(results)

        user_id = int(body.get("user_id"))
        passenger_id = int(body.get("passenger_id"))
        results.append(StepResult("auth_me", True, f"Authenticated as user_id={user_id}, passenger_id={passenger_id}"))

        # 5) airports
        status, body = client.request("GET", f"{args.passenger_base}/airports")
        if status != 200 or not isinstance(body, list) or len(body) < 2:
            results.append(StepResult("airports", False, f"Airports check failed: {status}, {body}"))
            return report(results)

        origin = str(body[0].get("airport_code", "")).upper()
        destination = str(body[1].get("airport_code", "")).upper()
        results.append(StepResult("airports", True, f"Loaded {len(body)} airports"))

        # 6) flight search
        query = urllib.parse.urlencode(
            {
                "origin_code": origin,
                "destination_code": destination,
                "travel_date": args.travel_date,
                "sort_by": "price",
                "sort_order": "asc",
            }
        )
        search_url = f"{args.passenger_base}/flights/search?{query}"
        status, body = client.request("GET", search_url, headers=auth_headers)

        if status != 200 or not isinstance(body, list):
            results.append(StepResult("flight_search", False, f"Flight search failed: {status}, {body}"))
            return report(results)

        results.append(StepResult("flight_search", True, f"Found {len(body)} flights for {origin}->{destination}"))

        # 7) booking (optional if no future flights)
        candidate = first_bookable_flight(body)
        if candidate is None:
            results.append(
                StepResult(
                    "booking",
                    True,
                    "Skipped booking: no future flight found in search result for selected date",
                )
            )
        else:
            booking_payload = {
                "passenger_id": passenger_id,
                "user_id": user_id,
                "flight_id": candidate["flight_id"],
                "seat_number": None,
                "class_type": "Economy",
                "payment_method": "UPI",
                "transaction_reference": f"SMKTXN-{random.randint(100000, 999999)}",
                "tax_amount": 120.0,
                "service_charge": 80.0,
                "random_allotment": True,
                "use_seat_lock": False,
            }
            status, body = client.request(
                "POST",
                f"{args.passenger_base}/bookings",
                booking_payload,
                headers=auth_headers,
            )
            if status == 201 and isinstance(body, dict) and body.get("booking_reference"):
                results.append(
                    StepResult(
                        "booking",
                        True,
                        f"Booking created: {body.get('booking_reference')}",
                    )
                )
            else:
                results.append(StepResult("booking", False, f"Booking failed: {status}, {body}"))

        # 8) admin summary
        if args.skip_admin:
            results.append(StepResult("admin_summary", True, "Skipped by flag --skip-admin"))
        else:
            status, body = client.request("GET", f"{args.admin_base}/dashboard/summary")
            if status == 200 and isinstance(body, dict) and "total_bookings" in body:
                results.append(StepResult("admin_summary", True, "Admin summary fetched successfully"))
            else:
                results.append(StepResult("admin_summary", False, f"Admin summary failed: {status}, {body}"))

    except Exception as exc:  # noqa: BLE001
        results.append(StepResult("runtime", False, f"Unexpected error: {exc}"))

    return report(results)


def report(results: list[StepResult]) -> int:
    print("Smoke test results")
    print("=" * 72)

    failed = 0
    for item in results:
        icon = "PASS" if item.ok else "FAIL"
        print(f"[{icon}] {item.name}: {item.message}")
        if not item.ok:
            failed += 1

    print("=" * 72)
    if failed:
        print(f"Result: FAILED ({failed} step(s) failed)")
        return 1

    print("Result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
