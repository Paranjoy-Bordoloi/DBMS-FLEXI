#!/usr/bin/env python3
"""Interactive CLI console for DBMS+FLEXI APIs.

Features:
- Login/register
- Search flights and book selected flight
- Manage bookings (list, retrieve, cancel, change seat/flight)
- Admin booking explorer with filters

Usage:
  .\\.venv\\Scripts\\python.exe scripts\\cli_console.py
  .\\.venv\\Scripts\\python.exe scripts\\cli_console.py --base-url http://127.0.0.1:8000
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


def input_default(prompt: str, default: str) -> str:
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def input_optional(prompt: str) -> str | None:
    value = input(f"{prompt} (optional): ").strip()
    return value or None


def parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def random_txn_ref(prefix: str = "CLI-TXN") -> str:
    suffix = "".join(random.choice(string.digits) for _ in range(8))
    return f"{prefix}-{suffix}"


def today_str() -> str:
    return dt.date.today().isoformat()


class HttpClient:
    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout

    def request(
        self,
        method: str,
        url: str,
        payload: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict | list | str | None]:
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)

        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(url=url, data=data, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, self._parse(body)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8") if exc.fp else ""
            return exc.code, self._parse(body)
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Connection failed for {url}: {exc.reason}") from exc

    @staticmethod
    def _parse(body: str) -> dict | list | str | None:
        if not body:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body


class CLIConsole:
    def __init__(self, base_url: str, timeout: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = HttpClient(timeout=timeout)
        self.token: str | None = None
        self.me: dict | None = None

    def _auth_headers(self) -> dict[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def _call(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        query: dict[str, str | int] | None = None,
        auth: bool = False,
    ) -> tuple[int, dict | list | str | None]:
        query_string = ""
        if query:
            query_string = "?" + urllib.parse.urlencode(query)
        url = f"{self.base_url}{path}{query_string}"
        headers = self._auth_headers() if auth else None
        return self.http.request(method, url, payload=payload, headers=headers)

    def run(self) -> int:
        print("DBMS+FLEXI Interactive CLI")
        print("=" * 36)

        while True:
            if not self.token:
                if not self._auth_menu():
                    return 0
            else:
                if not self._session_menu():
                    return 0

    def _auth_menu(self) -> bool:
        print("\n1) Login")
        print("2) Register")
        print("3) Quit")
        choice = input("Select option: ").strip()

        if choice == "1":
            self.login()
            return True
        if choice == "2":
            self.register()
            return True
        if choice == "3":
            return False

        print("Invalid option.")
        return True

    def _session_menu(self) -> bool:
        role = (self.me or {}).get("role", "Passenger")
        print(f"\nLogged in as {self.me.get('email')} ({role})")
        print("1) Search and book flight")
        print("2) List current bookings")
        print("3) Retrieve booking by PNR")
        print("4) Cancel booking")
        print("5) Change seat")
        print("6) Change flight")
        if role == "Admin":
            print("7) Admin booking explorer")
        print("9) Logout")
        print("0) Quit")
        choice = input("Select option: ").strip()

        if choice == "1":
            self.search_and_book()
        elif choice == "2":
            self.list_current_bookings()
        elif choice == "3":
            self.retrieve_booking()
        elif choice == "4":
            self.cancel_booking()
        elif choice == "5":
            self.change_seat()
        elif choice == "6":
            self.change_flight()
        elif choice == "7" and role == "Admin":
            self.admin_booking_explorer()
        elif choice == "9":
            self.logout()
        elif choice == "0":
            return False
        else:
            print("Invalid option.")

        return True

    def login(self) -> None:
        email = input("Email: ").strip()
        password = input("Password: ").strip()

        status, body = self._call("POST", "/auth/login", {"email": email, "password": password})
        if status != 200 or not isinstance(body, dict) or "access_token" not in body:
            print(f"Login failed: {status} {body}")
            return

        self.token = str(body["access_token"])
        me_status, me_body = self._call("GET", "/auth/me", auth=True)
        if me_status != 200 or not isinstance(me_body, dict):
            print(f"Could not load profile: {me_status} {me_body}")
            self.token = None
            return

        self.me = me_body
        print(f"Login successful: {self.me.get('email')} ({self.me.get('role')})")

    def register(self) -> None:
        print("Create passenger account")
        payload = {
            "first_name": input("First name: ").strip(),
            "last_name": input("Last name: ").strip(),
            "email": input("Email: ").strip(),
            "phone": input("Phone (10 digits): ").strip(),
            "passport_number": input("Passport number: ").strip(),
            "date_of_birth": input_default("Date of birth YYYY-MM-DD", "1999-01-01"),
            "password": input("Password: ").strip(),
            "address": input_default("Address", "CLI User Address"),
        }
        status, body = self._call("POST", "/auth/register", payload)
        if status == 201:
            print("Registration successful. You can now login.")
        else:
            print(f"Registration failed: {status} {body}")

    def logout(self) -> None:
        self.token = None
        self.me = None
        print("Logged out.")

    def search_and_book(self) -> None:
        if not self.me:
            print("Please login first.")
            return

        origin = input("Origin airport code (e.g., DEL): ").strip().upper()
        destination = input("Destination airport code (e.g., BOM): ").strip().upper()
        travel_date = input_default("Travel date YYYY-MM-DD", today_str())

        query = {
            "origin_code": origin,
            "destination_code": destination,
            "travel_date": travel_date,
            "sort_by": "price",
            "sort_order": "asc",
        }
        status, body = self._call("GET", "/flights/search", query=query, auth=True)
        if status != 200 or not isinstance(body, list):
            print(f"Search failed: {status} {body}")
            return

        if not body:
            print("No flights found.")
            return

        print("\nFlights")
        print("-" * 80)
        for idx, flight in enumerate(body, start=1):
            print(
                f"{idx}. flight_id={flight.get('flight_id')} | {flight.get('flight_number')} | "
                f"{flight.get('origin_code')}->{flight.get('destination_code')} | "
                f"dep={flight.get('departure_time')} | econ={flight.get('economy_price')}"
            )
        print("-" * 80)

        pick = parse_int(input_optional("Select flight number from list"))
        if pick is None or pick < 1 or pick > len(body):
            print("Invalid selection.")
            return

        chosen = body[pick - 1]
        class_type = input_default("Class (Economy/Business/First)", "Economy")
        seat = input_optional("Seat number")

        payload = {
            "passenger_id": int(self.me["passenger_id"]),
            "user_id": int(self.me["user_id"]),
            "flight_id": int(chosen["flight_id"]),
            "seat_number": seat,
            "class_type": class_type,
            "payment_method": "UPI",
            "transaction_reference": random_txn_ref(),
            "tax_amount": 120.0,
            "service_charge": 80.0,
            "random_allotment": seat is None,
            "use_seat_lock": False,
        }

        status, body = self._call("POST", "/bookings", payload=payload, auth=True)
        if status == 201 and isinstance(body, dict):
            print("Booking created successfully")
            print(f"PNR: {body.get('booking_reference')}")
            print(f"Seat: {body.get('seat_number')}")
            print(f"Amount: {body.get('total_amount')}")
        else:
            print(f"Booking failed: {status} {body}")

    def list_current_bookings(self) -> None:
        status, body = self._call("GET", "/bookings/current", auth=True)
        if status != 200 or not isinstance(body, list):
            print(f"Failed: {status} {body}")
            return

        if not body:
            print("No current bookings.")
            return

        print("\nCurrent bookings")
        print("-" * 80)
        for row in body:
            print(
                f"PNR {row.get('booking_reference')} | {row.get('flight_number')} | "
                f"seat {row.get('seat_number')} | {row.get('class_type')} | {row.get('booking_status')}"
            )
        print("-" * 80)

    def retrieve_booking(self) -> None:
        pnr = input("PNR: ").strip().upper()
        last_name = input("Last name: ").strip()
        status, body = self._call("GET", "/bookings/retrieve", query={"pnr": pnr, "last_name": last_name}, auth=True)
        if status != 200 or not isinstance(body, dict):
            print(f"Retrieve failed: {status} {body}")
            return

        print(json.dumps(body, indent=2, default=str))

    def cancel_booking(self) -> None:
        pnr = input("PNR to cancel: ").strip().upper()
        reason = input_default("Reason", "Change of plan")
        status, body = self._call("POST", f"/bookings/{pnr}/cancel", payload={"reason": reason}, auth=True)
        if status != 200:
            print(f"Cancel failed: {status} {body}")
            return
        print(f"Cancelled: {body}")

    def change_seat(self) -> None:
        pnr = input("PNR: ").strip().upper()
        new_seat = input("New seat number (e.g., 14C): ").strip().upper()
        status, body = self._call(
            "POST",
            f"/bookings/{pnr}/change-seat",
            payload={"new_seat_number": new_seat},
            auth=True,
        )
        if status != 200:
            print(f"Change seat failed: {status} {body}")
            return
        print(f"Seat updated: {body}")

    def change_flight(self) -> None:
        pnr = input("PNR: ").strip().upper()
        new_flight_id = parse_int(input("New flight ID: ").strip())
        if new_flight_id is None:
            print("Invalid flight ID")
            return

        new_seat = input_optional("Preferred seat")
        payload: dict[str, int | str] = {"new_flight_id": new_flight_id}
        if new_seat:
            payload["new_seat_number"] = new_seat.upper()

        status, body = self._call("POST", f"/bookings/{pnr}/change-flight", payload=payload, auth=True)
        if status != 200:
            print(f"Change flight failed: {status} {body}")
            return
        print(f"Flight updated: {body}")

    def admin_booking_explorer(self) -> None:
        if (self.me or {}).get("role") != "Admin":
            print("Admin only.")
            return

        status_filter = input_optional("Status (Pending/Confirmed/Cancelled)")
        flight_id = parse_int(input_optional("Flight ID"))
        passenger_id = parse_int(input_optional("Passenger ID"))
        passenger_email = input_optional("Passenger email contains")
        limit = parse_int(input_default("Limit", "200")) or 200

        query: dict[str, str | int] = {"limit": limit}
        if status_filter:
            query["status"] = status_filter
        if flight_id is not None:
            query["flight_id"] = flight_id
        if passenger_id is not None:
            query["passenger_id"] = passenger_id
        if passenger_email:
            query["passenger_email"] = passenger_email

        status, body = self._call("GET", "/admin/bookings", query=query, auth=True)
        if status != 200 or not isinstance(body, list):
            print(f"Admin booking query failed: {status} {body}")
            return

        if not body:
            print("No rows found for given filters.")
            return

        print(f"\nFound {len(body)} row(s)")
        print("-" * 110)
        for row in body:
            print(
                f"PNR {row.get('booking_reference')} | flight_id={row.get('flight_id')} {row.get('flight_number')} | "
                f"{row.get('passenger_first_name')} {row.get('passenger_last_name')} | "
                f"{row.get('passenger_email')} | {row.get('status')}"
            )
        print("-" * 110)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive CLI for DBMS+FLEXI APIs")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="FastAPI base URL")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cli = CLIConsole(base_url=args.base_url, timeout=args.timeout)
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
