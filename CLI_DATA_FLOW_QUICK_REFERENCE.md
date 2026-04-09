# CLI Data Flow - Quick Reference

## Menu Operations Summary

| Option | Method | HTTP Calls | JDBC | Input | Output |
|--------|--------|-----------|------|-------|--------|
| **Auth: Login** | `login()` | 2 | - | email, password | token, me (user profile) |
| **Auth: Register** | `register()` | 1 | - | 8 fields | "success" message |
| **1: Search & Book** | `searchAndBook()` | 3 | - | origin, dest, date, seat, class | PNR, seat, total |
| **2: List Bookings** | `listCurrentBookings()` | 1 | - | (token only) | Array of bookings |
| **3: Retrieve by PNR** | `retrieveBooking()` | 1 | - | PNR, last_name | Full booking JSON |
| **4: Cancel** | `cancelBooking()` | 1 | - | PNR, reason | Cancellation confirmation |
| **5: Change Seat** | `changeSeat()` | 1 | - | PNR, new_seat | Confirmation |
| **6: Change Flight** | `changeFlight()` | 1 | - | PNR, new_flight, seat | Confirmation |
| **7: Admin Explorer** | `adminBookingExplorer()` | 1 | - | filters (optional) | Filtered booking list |
| **8: Dashboard** | `viewDashboardSummary()` | - | 4 queries | (admin only) | 4 metrics + formatting |
| **9: Logout** | `logout()` | - | - | - | Clear state, return to auth |

---

## API Endpoints Called

### Authentication
```
POST /auth/login
  - Headers: Content-Type: application/json
  - Body: {email, password}
  - Returns: {access_token, user}

GET /auth/me
  - Headers: Authorization: Bearer {token}, Content-Type: application/json
  - Returns: {user_id, passenger_id, email, role}

POST /auth/register
  - Body: {email, first_name, last_name, phone, passport_number, dob, password, address}
  - Returns: {status: "ok"}
```

### Flight Operations
```
GET /flights/search?origin_code=X&destination_code=Y&travel_date=Z&sort_by=price&sort_order=asc
  - Headers: Authorization: Bearer {token}
  - Returns: [{flight_id, flight_number, origin_code, destination_code, departure_time, prices}...]

GET /flights/{flightId}/seat-map
  - Headers: Authorization: Bearer {token}
  - Returns: {seats: [{seat_number, cabin_class, status}...]}
```

### Booking Operations
```
GET /bookings/current
  - Headers: Authorization: Bearer {token}
  - Returns: [{booking_reference, flight_number, seat_number, class_type, booking_status}...]

GET /bookings/retrieve?pnr=X&last_name=Y
  - Headers: Authorization: Bearer {token}
  - Returns: {booking_id, booking_reference, passenger_id, flight_id, seat_number, ...}

POST /bookings
  - Headers: Authorization: Bearer {token}
  - Body: {passenger_id, user_id, flight_id, seat_number, random_allotment, class_type, payment_method, ...}
  - Returns: {booking_reference, booking_id, seat_number, status, total_amount}

POST /bookings/{pnr}/cancel
  - Headers: Authorization: Bearer {token}
  - Body: {reason}
  - Returns: {booking_reference, status: "Cancelled", cancellation_date, refund_amount}

POST /bookings/{pnr}/change-seat
  - Headers: Authorization: Bearer {token}
  - Body: {new_seat_number}
  - Returns: {booking_reference, new_seat_number, previous_seat_number, status}

POST /bookings/{pnr}/change-flight
  - Headers: Authorization: Bearer {token}
  - Body: {new_flight_id, new_seat_number (optional)}
  - Returns: {booking_reference, new_flight_id, new_seat_number, status}
```

### Admin Operations
```
GET /admin/bookings?status=X&flight_id=Y&passenger_id=Z&passenger_email=E&limit=L
  - Headers: Authorization: Bearer {token}
  - Returns: [{booking_reference, flight_id, flight_number, passenger_first_name, passenger_last_name, passenger_email, status}...]
```

---

## Data Structures

### Key Enums/Constants

```java
// Class types (normalized by normalizeClass())
"Economy", "Business", "First"

// Status values (normalized by normalizeStatus())
"Pending", "Confirmed", "Cancelled"

// Payment methods
"UPI"

// User roles in me object
"Admin", "Passenger"
```

### Core Models (Java Records/Classes)

```java
record ApiResponse(int statusCode, String body) {
    boolean success() { return 200 <= statusCode < 300; }
    JsonObject asObject() { /* parse & return */ }
    JsonArray asArray() { /* parse & return */ }
}

record DashboardSummary(
    long totalBookings,
    long confirmedBookings,
    double totalRevenue,
    double averageOccupancyPercent
)

class AirlineCliApp {
    String token                           // JWT from login
    JsonObject me                          // User {user_id, passenger_id, email, role}
    String baseUrl                         // Base URL of API
    HttpClient httpClient                  // Reused HTTP client
    DashboardMetricsService...(Impl)      // JDBC service
}
```

### Input Validation Patterns

```
Email:        ^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$
Airport Code: ^[A-Z]{3}$
Seat Number:  ^[0-9]{1,2}[A-Z]$
Passport:     ^[A-Z0-9]{6,20}$
Phone:        ^[0-9]{10,15}$
Name:         ^[A-Za-z][A-Za-z\s'-]{0,49}$
PNR:          ^[A-Z0-9]{8,12}$
Date:         YYYY-MM-DD (parsed via LocalDate.parse())
```

---

## State Flow Diagram

```
┌─────────────────────────┐
│   Initial State         │
│ token = null            │
│ me = null               │
│ Show: AuthMenu          │
└────────────┬────────────┘
             │
      ┌──────┴───────┐
      │              │
      ▼              ▼
   [Login]      [Register]
      │              │
      └──────┬───────┘
             │
      ▼──────▼─────────────────────┐
┌──────────────────────────────────┴──────┐
│  Authenticated State                    │
│  token = "JWT_STRING"                   │
│  me = {user_id, role, email, ...}       │
│  Show: SessionMenu (with role-based)    │
└─────────────────────────────────────────┘
             │
             │ User selects option 1-8
             │
      ┌──────┴──────────────────────┐
      │                             │
    [Op 1-8]                   [Op 9: Logout]
      │                             │
      ▼                             ▼
   (Execute)                 ┌──────────────┐
      │                      │ token = null │
      │                      │ me = null    │
      │                      │ AuthMenu     │
      │                      └──────────────┘
      │                             ▲
      │                             │
      └─────────────────────────────┘


Multiple bookings per session:
   Each operation finds flights/bookings
     → Caches response in local variables
     → Displays to user
     → Variables discarded after operation
     → Session persists (token/me unchanged)
```

---

## Key Transformation Examples

### 1. Seat Number Transformation
```
User input:        "14c"
readSeat() method: .toUpperCase(Locale.ROOT) → "14C"
Validation:        Regex match "^[0-9]{1,2}[A-Z]$" ✓
Payload:           "seat_number": "14C"
Response:          "seat_number": "14C"
CLI display:       "Seat: 14C"
```

### 2. Airport Code Transformation
```
User input:        "bom"
readAirportCode(): .toUpperCase(Locale.ROOT) → "BOM"
Validation:        Regex match "^[A-Z]{3}$" ✓
Query param:       destination_code=BOM
Display:           "DEL -> BOM"
```

### 3. Class Type Transformation
```
User input:        "economy"
readClassType():   normalizeClass() → "Economy"
Validation:        Switch match on normalized ✓
Payload:           "class_type": "Economy"
Response:          "class_type": "Economy"
Display:           "Economy"
```

### 4. Currency Formatting
```
Backend response:  totalRevenue: 5234567.89
formatInr():       DecimalFormatSymbols("en", "IN")
                   Pattern: "##,##,##0.00"
                   Format: 5,234,567.89 (groups right-to-left)
                   Prepend: "Rs. "
Display:           "Rs. 52,34,567.89"
                   (Indian numbering: pairs)
```

---

## Error Handling Paths

### HTTP/Network Errors
```
Network unreachable
  → IOException caught
  → return ApiResponse(0, "Network error: message")
  → printApiError() displays with helpful message
  → "Tip: verify API base URL and ensure backend is running."

Invalid URL format
  → IllegalArgumentException caught
  → return ApiResponse(0, "Invalid request URL...")

Request interrupted
  → InterruptedException caught
  → Thread.currentThread().interrupt()
  → return ApiResponse(0, "Request interrupted...")
```

### HTTP Status Errors
```
400 (Bad Request)
  → response.body() contains validation error detail
  → extractErrorDetail() parses Pydantic ValidationError
  → Displays: "{msg} at {location}. Please review input format."

401 (Unauthorized)
  → Token expired or invalid
  → App still has token, backend rejects
  → printApiError() shows status

404 (Not Found)
  → Resource doesn't exist (e.g., booking by PNR)
  → Backend returns 404
  → App displays status message

500 (Server Error)
  → Backend exception occurred
  → Response contains error message
  → App displays to user
```

### JDBC Errors
```
Connection failed
  → SQLException caught
  → println("Could not load dashboard summary: {message}")
  → Return to menu, session continues

SQL execution error
  → SQLException caught during query
  → Same handler as connection failure
```

### Input Validation Errors
```
Invalid email format
  → Regex doesn't match
  → Loop: "Invalid email format... Please try again:"
  → Blocking: user must fix input

Out of range number
  → readIntInRange() validates min/max
  → Loop: "Invalid range. Enter between {min} and {max}."

Invalid date format
  → LocalDate.parse() throws DateTimeParseException
  → Loop: "Invalid date format. Use YYYY-MM-DD"
```

---

## Concurrency Model

**Single-threaded, Synchronous, Blocking:**

```
Thread Timeline:
────────────────────────────────────────────────────────
│ readNonEmpty() │ [WAIT FOR USER INPUT]
│ Build HTTP    │ Build request
│ httpClient.send()
│ [BLOCKED WAITING FOR RESPONSE]
│ Receive response (100ms-2s later)
│ Parse JSON   │ Parsing (< 10ms)
│ Display      │ Print to console
│ readInt()     │ [WAIT FOR USER INPUT]
────────────────────────────────────────────────────────
```

**No features:**
- No async/await (CompletableFuture not used)
- No thread pool (single HttpClient)
- No background operations
- No timeouts on requests (blocking indefinitely)
- No concurrent API calls
- No connection pooling (JDBC connection per call)

---

## Configuration & Defaults

### HTTP Configuration
```
Default base URL:  http://127.0.0.1:8000
Can be overridden: java ... --base-url http://custom:8000
URL normalization: Remove trailing "/" if present
Content-Type:      application/json (always)
Charset:           UTF-8 (for URL encoding)
```

### Database Configuration (JDBC)
```
Loaded from:       backend/.env (relative path: ../../backend/.env)
Cascade order:
  1. System environment variables (System.getenv())
  2. Dotenv file values (DOTENV_VALUES map)
  3. Java defaults

Default values if not found:
  DB_HOST:     "localhost"
  DB_PORT:     "3306"
  DB_NAME:     "airline_reservation"
  DB_USER:     "root"
  DB_PASSWORD: ""

JDBC URL pattern:
  jdbc:mysql://HOST:PORT/DB_NAME?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC

Driver:            com.mysql.cj.jdbc.Driver
Connector version: MySQL Connector/J 9.3.0
```

### Locale & Formatting
```
CLI input:     Default system Locale (English recommended)
Output text:   English
Currency:      Indian Rupee (INR) with Locale("en", "IN")
Number pattern: ##,##,##0.00 (two decimal places, comma separators)
Date format:   YYYY-MM-DD (ISO 8601)
```

---

## Performance Characteristics

### Time Complexity
```
Flight search:     O(flights_returned)  - iterate once for display
Seat range calc:   O(seats_per_flight)  - iterate to find min/max
Booking creation:  O(1)                 - single API call
Admin filter:      O(results_returned)  - iterate for display
```

### Space Complexity
```
User session:      O(1)  - token + me object
Flight cache:      O(n)  - n flights from search response
Seats cache:       O(n)  - n seats from seat-map response
```

### Network Latency
```
Per API call:      50-500ms typical internet
Search & Book:     3 calls × 100ms avg = ~300ms minimum
Dashboard:         No network, pure JDBC: ~50ms
```

---

## Common Usage Flows

### Happy Path: Book a Flight
```
1. CLI Start
2. Login → get token
3. Select Option 1 (Search & Book)
4. Enter origin (DEL), dest (BOM), date (2026-04-20)
5. View flights list (3 calls to API hidden)
6. Select flight 1
7. View seat ranges (part of step 6)
8. Select class (Economy), seat (14C)
9. Confirm booking
10. Display PNR + seat + total
11. Return to menu
```

### Admin Workflow: View Dashboard
```
1. CLI Start
2. Login as Admin → get token with role="Admin"
3. Select Option 8 (Dashboard)
4. (No user input needed)
5. Display 4 metrics with INR formatting
6. Return to menu
```

### Error Recovery: Retry After Network Error
```
1. User attempts booking
2. Network error occurs
3. CLI displays: "Network error... Tip: verify base URL"
4. Return to menu automatically
5. User can retry immediately or try different operation
6. Session persists (token/me unchanged)
```

---

## Testing Considerations

### What to Test
- [ ] Input validation (all readXxx methods)
- [ ] URL encoding with special characters
- [ ] JSON parsing with null values
- [ ] Error message extraction from 400s
- [ ] Seat range computation edge cases (gaps, single seat)
- [ ] INR formatting precision (decimals)
- [ ] JDBC .env loading with missing file
- [ ] Token expiration handling

### Sample Test Data
```
Valid Email:     "test@example.com", "user.name+tag@example.co.uk"
Invalid Email:   "test@", "@example.com", "test.example.com"

Valid Seat:      "1A", "14C", "99Z"
Invalid Seat:    "14", "A", "100A", "c14"

Valid Airport:   "DEL", "BOM", "NYC"
Invalid Airport: "DE", "DELHI", "de1"

Valid PNR:       "PNR00001234", "ABC123XYZ"
Invalid PNR:     "PNR", "12345678", "pnr00001234" (lowercase)
```
