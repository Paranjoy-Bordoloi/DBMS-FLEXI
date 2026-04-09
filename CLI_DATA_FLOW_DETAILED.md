# CLI Data Flow - Detailed Architecture

## Overview
The CLI follows a multi-layered data flow architecture with two primary channels:
1. **HTTP Channel**: Communicates with FastAPI backend via REST API using HttpClient
2. **JDBC Channel**: Direct database connection for dashboard metrics

---

## 1. STARTUP & INITIALIZATION

```
main(String[] args)
    ↓
Parse --base-url flag (default: http://127.0.0.1:8000)
    ↓
Initialize AirlineCliApp(baseUrl)
    ├─ Create Gson instance (GSON)
    ├─ Create HttpClient
    ├─ Create DashboardMetricsService instance
    └─ Create Scanner for user input
    ↓
run() loop
    ├─ If no token → authMenu()
    └─ If token exists → sessionMenu()
```

**State Variables Maintained:**
- `baseUrl: String` - FastAPI server URL
- `token: String` - JWT token from authentication
- `me: JsonObject` - Current user profile (passenger_id, user_id, role, email)

---

## 2. AUTHENTICATION FLOW

### 2a. Login Path

```
User selects Option 1 (Login)
    ↓
readEmail() → Validate email format
readNonEmpty("Password")
    ↓
Build payload: {"email", "password"}
    ↓
call("POST", "/auth/login", payload, null, false)
    ├─ URL: http://127.0.0.1:8000/auth/login
    ├─ No auth header (false = no bearer token needed)
    └─ Content-Type: application/json
    ↓
HttpResponse<String> received
    ├─ Status Code: 200-299 (success)
    └─ Body: {"access_token": "JWT...", "user": {...}}
    ↓
Extract token from response
    → token = body.get("access_token").getAsString()
    ↓
call("GET", "/auth/me", null, null, true)
    ├─ Authorization: Bearer {token}
    └─ Fetch current user profile
    ↓
Parse response → me = JsonObject with:
{
    "user_id": 123,
    "passenger_id": 456,
    "email": "user@example.com",
    "role": "Admin" or "Passenger"
}
    ↓
sessionMenu() becomes available
```

### 2b. Registration Path

```
User selects Option 2 (Register)
    ↓
Input Fields (with validation):
    ├─ readEmail() → Regex: ^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$
    ├─ readName() → Regex: ^[A-Za-z][A-Za-z\s'-]{0,49}$
    ├─ readPhone() → Regex: ^[0-9]{10,15}$
    ├─ readPassport() → Regex: ^[A-Z0-9]{6,20}$
    ├─ readDate() → Parse YYYY-MM-DD
    ├─ readPassword() → Min 8 chars
    └─ readNonEmpty("Address")
    ↓
Build payload: {email, first_name, last_name, phone, passport_number, dob, password, address}
    ↓
call("POST", "/auth/register", payload, null, false)
    ↓
HttpResponse: 201 Created
    ↓
Display: "Registration successful. You can login now."
    ↓
Return to authMenu()
```

---

## 3. SEARCH & BOOK FLOW (Option 1)

This is the most complex data flow with multiple API calls and transformations:

```
searchAndBook()
│
├─ Step 1: COLLECT SEARCH CRITERIA
│   ├─ readAirportCode("Origin") → Regex: ^[A-Z]{3}$  (e.g., DEL)
│   ├─ readAirportCode("Destination") → Regex: ^[A-Z]{3}$ (e.g., BOM)
│   └─ readDate("Travel date") → YYYY-MM-DD format
│
├─ Step 2: BUILD QUERY PARAMETERS
│   └─ Map<String, String> query = {
│       "origin_code": "DEL",
│       "destination_code": "BOM",
│       "travel_date": "2026-04-20",
│       "sort_by": "price",
│       "sort_order": "asc"
│   }
│
├─ Step 3: API CALL - SEARCH FLIGHTS
│   ├─ call("GET", "/flights/search", null, query, true)
│   ├─ URL encoding: /flights/search?origin_code=DEL&destination_code=BOM&travel_date=2026-04-20&sort_by=price&sort_order=asc
│   ├─ Header: Authorization: Bearer {token}
│   └─ HttpResponse: 200 OK
│       Body: [
│           {
│               "flight_id": 101,
│               "flight_number": "AI101",
│               "origin_code": "DEL",
│               "destination_code": "BOM",
│               "departure_time": "2026-04-20T08:00:00",
│               "economy_price": 5000,
│               "business_price": 9000,
│               "first_price": 15000
│           },
│           ...
│       ]
│
├─ Step 4: PARSE FLIGHTS & DISPLAY
│   ├─ JsonArray flights = response.asArray()
│   ├─ For i=0 to flights.size()-1:
│   │   Print: "1) flight_id={id} | {flight_number} | {origin}->{dest} | dep={time} | economy={price}"
│   └─ Extract field: flight_id = 101
│
├─ Step 5: USER SELECTS FLIGHT
│   ├─ readIntInRange("Select flight number", 1, flights.size())
│   └─ JsonObject selectedFlight = flights.get(selectedIndex).getAsJsonObject()
│
├─ Step 6: FETCH SEAT MAP (NEW API CALL)
│   ├─ call("GET", "/flights/{flightId}/seat-map", null, null, true)
│   ├─ URL: /flights/101/seat-map
│   └─ HttpResponse: 200 OK
│       Body: {
│           "seats": [
│               {"seat_number": "1A", "cabin_class": "First", "status": "available"},
│               {"seat_number": "1B", "cabin_class": "First", "status": "available"},
│               {"seat_number": "3A", "cabin_class": "Business", "status": "occupied"},
│               {"seat_number": "7A", "cabin_class": "Economy", "status": "available"},
│               ...
│           ]
│       }
│
├─ Step 7: COMPUTE SEAT RANGES (CLIENT-SIDE PROCESSING)
│   ├─ fetchSeatRangeIndicators(101)
│   │   ├─ Parse JsonArray seats
│   │   ├─ For each seat:
│   │   │   ├─ Extract: cabin_class, seat_number
│   │   │   ├─ Convert seat to numeric index: seatOrderIndex("2C") = 64 + 2 = row*32 + col
│   │   │   └─ Track min/max index per class
│   │   └─ Return Map: {
│   │       "First": "1A to 2F",
│   │       "Business": "3A to 6C",
│   │       "Economy": "7A to 30F"
│   │   }
│   │
│   └─ printClassSeatRanges(ranges)
│       └─ Display:
│           Seat range indicators for this flight:
│           - First: 1A to 2F
│           - Business: 3A to 6C
│           - Economy: 7A to 30F
│
├─ Step 8: READ CLASS & SEAT
│   ├─ readClassType("Class type (Economy/Business/First)")
│   │   └─ Normalize input: "economy" → "Economy"
│   └─ readOptional("Seat number (optional, e.g., 14C)")
│       └─ If blank → random_allotment = true, seat_number = null
│       └─ If provided → validate Regex: ^[0-9]{1,2}[A-Z]$
│
├─ Step 9: BUILD BOOKING PAYLOAD
│   └─ JsonObject payload = {
│       "passenger_id": 456,
│       "user_id": 123,
│       "flight_id": 101,
│       "seat_number": "14C" or null,
│       "random_allotment": false or true,
│       "class_type": "Economy",
│       "payment_method": "UPI",
│       "transaction_reference": "JAVA-CLI-1712519344821",
│       "tax_amount": 120.0,
│       "service_charge": 80.0,
│       "use_seat_lock": false
│   }
│
├─ Step 10: API CALL - CREATE BOOKING
│   ├─ call("POST", "/bookings", payload, null, true)
│   ├─ URL: /bookings
│   ├─ Body: JSON payload
│   ├─ Header: Authorization: Bearer {token}
│   └─ HttpResponse: 201 Created
│       Body: {
│           "booking_reference": "PNR00001234",
│           "booking_id": 5678,
│           "seat_number": "14C",
│           "status": "Confirmed",
│           "total_amount": 5200.0
│       }
│
└─ Step 11: PARSE & DISPLAY CONFIRMATION
    ├─ Extract response fields
    ├─ Display:
    │   Booking successful.
    │   PNR: PNR00001234
    │   Seat: 14C
    │   Total: 5200.0
    └─ Return to sessionMenu()
```

**Data Transformations:**
1. CLI Input → Validated String
2. String → Query Parameter Map → URL Encoded String in URI
3. API Response JSON String → Gson JsonArray → Individual JsonObjects
4. JsonArray (seats) → Map<String, String> (seat ranges) → Display
5. Response JSON → JsonObject → Extract fields → Display

---

## 4. LIST CURRENT BOOKINGS (Option 2)

```
listCurrentBookings()
    ↓
call("GET", "/bookings/current", null, null, true)
    ├─ No query params
    ├─ Auth: Bearer {token}
    └─ Response: [
        {
            "booking_reference": "PNR00001234",
            "flight_number": "AI101",
            "seat_number": "14C",
            "class_type": "Economy",
            "booking_status": "Confirmed"
        },
        ...
    ]
    ↓
JsonArray rows = response.asArray()
    ↓
For each row:
    ├─ Extract fields: booking_reference, flight_number, seat_number, class_type, booking_status
    └─ Print: "PNR {pnr} | {flight} | seat {seat} | {class} | {status}"
    ↓
Return to sessionMenu()
```

---

## 5. RETRIEVE BOOKING BY PNR (Option 3)

```
retrieveBooking()
    ↓
readPnr() → Regex: ^[A-Z0-9]{8,12}$ (e.g., PNR00001234)
readName() → Passenger last name
    ↓
Build query: {"pnr": "PNR00001234", "last_name": "Sharma"}
    ↓
call("GET", "/bookings/retrieve", null, query, true)
    ├─ URL: /bookings/retrieve?pnr=PNR00001234&last_name=Sharma
    └─ Response: {
        "booking_id": 5678,
        "booking_reference": "PNR00001234",
        "passenger_id": 456,
        "flight_id": 101,
        "seat_number": "14C",
        "class_type": "Economy",
        "status": "Confirmed",
        "booking_date": "2026-04-10",
        "total_amount": 5200.0
    }
    ↓
prettyJson() → Pretty-print with indentation
    ↓
Display full JSON response
```

---

## 6. CANCEL BOOKING (Option 4)

```
cancelBooking()
    ↓
readPnr("PNR to cancel")
readNonEmpty("Cancellation reason")
    ↓
Build payload: {"reason": "Personal reasons"}
    ↓
call("POST", "/bookings/{pnr}/cancel", payload, null, true)
    ├─ URL: /bookings/PNR00001234/cancel
    ├─ Method: POST
    └─ Response: {
        "booking_reference": "PNR00001234",
        "status": "Cancelled",
        "cancellation_date": "2026-04-10T14:30:00",
        "refund_amount": 5000.0
    }
    ↓
Display confirmation with refund details
```

---

## 7. CHANGE SEAT (Option 5)

```
changeSeat()
    ↓
readPnr("PNR")
readSeat("New seat number (e.g., 14C)")
    ├─ Regex: ^[0-9]{1,2}[A-Z]$
    └─ Uppercase conversion: "14c" → "14C"
    ↓
Build payload: {"new_seat_number": "14C"}
    ↓
call("POST", "/bookings/{pnr}/change-seat", payload, null, true)
    ├─ URL: /bookings/PNR00001234/change-seat
    └─ Response: {
        "booking_reference": "PNR00001234",
        "new_seat_number": "14C",
        "previous_seat_number": "12A",
        "status": "Confirmed"
    }
    ↓
Display success confirmation
```

---

## 8. CHANGE FLIGHT (Option 6)

```
changeFlight()
    ↓
readPnr("PNR")
readLong("New flight ID", 1, Long.MAX_VALUE)
readOptional("Preferred new seat (optional)")
    ↓
Build payload: {
    "new_flight_id": 102,
    "new_seat_number": "15C" (optional)
}
    ↓
call("POST", "/bookings/{pnr}/change-flight", payload, null, true)
    ├─ URL: /bookings/PNR00001234/change-flight
    └─ Response: {
        "booking_reference": "PNR00001234",
        "new_flight_id": 102,
        "new_seat_number": "15C",
        "status": "Confirmed"
    }
    ↓
Display success confirmation
```

---

## 9. ADMIN BOOKING EXPLORER (Option 7 - Admin Only)

```
adminBookingExplorer()
    ↓
COLLECT FILTER CRITERIA (all optional):
    ├─ readOptional("Status filter (Pending/Confirmed/Cancelled, optional)")
    │   └─ Validate: isAllowedStatus() → normalizeStatus()
    ├─ readOptional("Flight ID filter (positive integer, optional)")
    │   └─ Validate: parseOptionalLong() → Must be > 0
    ├─ readOptional("Passenger ID filter (positive integer, optional)")
    │   └─ Validate: parseOptionalLong() → Must be > 0
    ├─ readOptional("Passenger email contains (optional)")
    └─ readLongWithDefault("Limit (1-5000)", default=200)
    ↓
BUILD QUERY MAP (selective based on input):
    └─ Map<String, String> query = {
        "status": "Confirmed",          // if provided
        "flight_id": "101",             // if provided
        "passenger_id": "456",          // if provided
        "passenger_email": "@gmail",    // if provided
        "limit": "200"                  // always included
    }
    ↓
URL CONSTRUCTION & ENCODING:
    ├─ Base: /admin/bookings
    ├─ Query params URL-encoded: ?status=Confirmed&flight_id=101&limit=200
    └─ Final URL: /admin/bookings?status=Confirmed&flight_id=101&limit=200
    ↓
call("GET", "/admin/bookings", null, query, true)
    ├─ URL-encoded query params build automatically
    ├─ Auth: Bearer {token}
    └─ Response: [
        {
            "booking_reference": "PNR00001234",
            "flight_id": 101,
            "flight_number": "AI101",
            "passenger_first_name": "Raj",
            "passenger_last_name": "Sharma",
            "passenger_email": "raj@example.com",
            "status": "Confirmed"
        },
        ...
    ]
    ↓
PARSE & DISPLAY:
    ├─ JsonArray rows = response.asArray()
    ├─ Print: "Admin bookings result count: {rows.size()}"
    └─ For each row:
        └─ Print: "PNR {pnr} | Flight {fid} ({fnum}) | {fname} {lname} | {status}"
    ↓
Return to sessionMenu()
```

**Query Parameter Construction Details:**
```java
// Internal URL building process:
StringBuilder url = new StringBuilder(baseUrl).append("/admin/bookings");

Map<String, String> query = {"status": "Confirmed", "flight_id": "101"};

// URL encoding step (per parameter):
List<String> pairs = new ArrayList<>();
for each entry in query:
    pairs.add(URLEncoder.encode(key, UTF-8) + "=" + URLEncoder.encode(value, UTF-8))

// Final: ?status=Confirmed&flight_id=101
url.append("?").append(String.join("&", pairs));
```

---

## 10. DASHBOARD SUMMARY (Option 8 - Admin Only & JDBC Channel)

This is the ONLY flow that uses JDBC instead of HTTP:

```
viewDashboardSummary()
    ↓
Step 1: JDBC CONNECTION SETUP
    ├─ Database.getConnection()
    │   ├─ Call static loadDotenv()
    │   │   ├─ Read file: ../../backend/.env
    │   │   ├─ Parse lines: DB_HOST=localhost, DB_PORT=3306, etc.
    │   │   └─ Build Map<String, String> DOTENV_VALUES
    │   ├─ readEnv("DB_HOST", "localhost")
    │   │   └─ Cascade: System.getenv() → DOTENV_VALUES → default
    │   ├─ readEnv("DB_PORT", "3306")
    │   ├─ readEnv("DB_NAME", "airline_reservation")
    │   ├─ readEnv("DB_USER", "root")
    │   └─ readEnv("DB_PASSWORD", "")
    │
    ├─ Build JDBC URL:
    │   "jdbc:mysql://localhost:3306/airline_reservation?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC"
    │
    ├─ DriverManager.getConnection(url, username, password)
    │   └─ Opens MySQL Connection object
    │
    └─ try (Connection conn = ...) { ... }  // Auto-close on exit
    ↓
Step 2: DASHBOARD SERVICE CALL
    ├─ dashboardMetricsService.fetchSummary(conn)
    │   ├─ Service Interface: DashboardMetricsService
    │   ├─ Implementation: DashboardMetricsServiceImpl
    │   └─ Executes SQL queries via JDBC:
    │       ├─ SELECT COUNT(*) FROM bookings → totalBookings: 1250
    │       ├─ SELECT COUNT(*) FROM bookings WHERE status='Confirmed' → confirmedBookings: 980
    │       ├─ SELECT SUM(total_fare + tax_amount) FROM bookings → totalRevenue: 5234567.89
    │       └─ SELECT AVG(occupancy_percent) FROM flights WHERE status='Active' → avgOccupancy: 74.5
    │
    └─ Returns DashboardSummary record:
        {
            totalBookings: 1250,
            confirmedBookings: 980,
            totalRevenue: 5234567.89,
            averageOccupancyPercent: 74.5
        }
    ↓
Step 3: FORMAT OUTPUT
    ├─ formatInr(summary.totalRevenue())
    │   ├─ DecimalFormatSymbols symbols = new Locale("en", "IN")
    │   ├─ DecimalFormat formatter = new DecimalFormat("##,##,##0.00", symbols)
    │   ├─ formatter.format(5234567.89)
    │   └─ Returns: "52,34,567.89"  (Indian spacing: pairs from right)
    │
    └─ Prepend: "Rs. " + formatted = "Rs. 52,34,567.89"
    ↓
Step 4: DISPLAY
    └─ println("Dashboard summary:");
        println("Total bookings: 1250");
        println("Confirmed bookings: 980");
        println("Total revenue: Rs. 52,34,567.89");
        println("Average occupancy (%): 74.5");
    ↓
Step 5: CLEANUP
    └─ Connection auto-closes (try-with-resources)
    ↓
Handle SQLException
    └─ catch (SQLException ex): println("Could not load dashboard summary: " + ex.getMessage())
    ↓
Return to sessionMenu()
```

**JDBC Data Flow Diagram:**
```
.env file content:
    DB_HOST=localhost
    DB_PORT=3306
    DB_NAME=airline_reservation
    DB_USER=root
    DB_PASSWORD=password123
            ↓
    Database.loadDotenv()
            ↓
    Map<String, String> DOTENV_VALUES = {
        "DB_HOST" → "localhost",
        "DB_PORT" → "3306",
        "DB_NAME" → "airline_reservation",
        "DB_USER" → "root",
        "DB_PASSWORD" → "password123"
    }
            ↓
    readEnv(key, default):
        Check System.getenv(key) first
        ↓ if null/blank
        Check DOTENV_VALUES.get(key)
        ↓ if null/blank
        Use default value
            ↓
    DriverManager.getConnection(
        "jdbc:mysql://localhost:3306/airline_reservation?...",
        "root",
        "password123"
    )
            ↓
    Connection conn (open)
            ↓
    PreparedStatement + ResultSet (via JDBC)
            ↓
    SQL: SELECT COUNT(*) FROM bookings → Row → Extract count value
            ↓
    DashboardSummary object (populated from ResultSets)
            ↓
    Returned to CLI
            ↓
    formatInr() applied
            ↓
    Display to user
            ↓
    conn.close() (automatic)
```

---

## 11. HTTP REQUEST LAYER DETAILS

```
call(String method, String path, JsonObject payload, Map<String, String> query, boolean auth)
    ↓
Step 1: BUILD URL
    ├─ Start: baseUrl + path
    │   Example: "http://127.0.0.1:8000" + "/flights/search"
    │
    ├─ If query params exist:
    │   ├─ For each (key, value) in query:
    │   │   URLEncoder.encode(key) + "=" + URLEncoder.encode(value)
    │   ├─ Join with "&"
    │   └─ Append to URL with "?"
    │   Result: "http://127.0.0.1:8000/flights/search?origin_code=DEL&destination_code=BOM&travel_date=2026-04-20"
    │
    └─ Create URI from final URL string
    ↓
Step 2: BUILD HTTP REQUEST
    ├─ HttpRequest.Builder builder = HttpRequest.newBuilder()
    ├─ builder.uri(URI)
    ├─ builder.header("Content-Type", "application/json")
    │
    ├─ If auth = true && token exists:
    │   └─ builder.header("Authorization", "Bearer " + token)
    │
    ├─ If method = "GET":
    │   └─ builder.GET()
    └─ Else (POST, PUT, DELETE):
        └─ builder.method(method, BodyPublishers.ofString(payload.toString()))
    ↓
Step 3: SEND REQUEST
    ├─ HttpResponse<String> response = httpClient.send(
    │       builder.build(),
    │       HttpResponse.BodyHandlers.ofString()
    │   )
    ├─ Blocks until response received (synchronous)
    └─ Captures: status code + response body (as String)
    ↓
Step 4: ERROR HANDLING
    ├─ catch IOException → return ApiResponse(0, "Network error: " + msg)
    ├─ catch InterruptedException → return ApiResponse(0, "Request interrupted")
    └─ catch IllegalArgumentException → return ApiResponse(0, "Invalid request URL")
    ↓
Step 5: RETURN RESPONSE
    └─ new ApiResponse(response.statusCode(), response.body())
        ├─ status codes: 0 (error), 200-299 (success), 400+ (client/server error)
        └─ body: unparsed JSON string (parsed by caller)
```

**ApiResponse Record:**
```java
record ApiResponse(int statusCode, String body) {
    boolean success() {
        return statusCode >= 200 && statusCode < 300;
    }
    
    JsonObject asObject() {
        // Parse body as single JSON object
        // Return null if not object or parse error
    }
    
    JsonArray asArray() {
        // Parse body as JSON array
        // Return null if not array or parse error
    }
}
```

---

## 12. JSON PARSING & DATA EXTRACTION

```
Raw Response: "{\"flight_id\": 101, \"flight_number\": \"AI101\", \"origin_code\": \"DEL\"}"
    ↓
call() returns: ApiResponse(200, jsonString)
    ↓
response.asObject()
    ├─ JsonParser.parseString(body) → JsonElement
    ├─ Check if JsonObject: parsed.isJsonObject()
    ├─ Convert: parsed.getAsJsonObject()
    └─ Returns: JsonObject
    ↓
For each field extraction:
    ├─ Check existence: obj.has("flight_id")
    ├─ Check + Extract: obj.get("flight_id").getAsLong()
    ├─ Handle null: obj.get("field").isJsonNull()
    └─ Fallback: getSafe() method returns "-" if field missing
    ↓
Extracted values stored in local variables:
    ├─ String flightNumber = getSafe(obj, "flight_number")
    ├─ Long flightId = obj.get("flight_id").getAsLong()
    └─ etc.
    ↓
Display/Use extracted values
```

**getSafe() Helper:**
```java
private String getSafe(JsonObject obj, String key) {
    if (obj == null || !obj.has(key) || obj.get(key).isJsonNull()) {
        return "-";  // Return dash if missing/null
    }
    return obj.get(key).getAsString();  // Extract string value
}
```

---

## 13. INPUT VALIDATION PATTERNS

```
User Input → readXxx() method → Validation → Return cleaned value

Examples:

readEmail():
    Input: "USER@EXAMPLE.COM"
    Match: Regex ^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$
    Return: Lowercase "user@example.com"

readSeat():
    Input: "14c"
    Match: Regex ^[0-9]{1,2}[A-Z]$
    Transform: Uppercase "14c" → "14C"
    Return: "14C"

readAirportCode():
    Input: "del"
    Match: Regex ^[A-Z]{3}$
    Transform: Uppercase "del" → "DEL"
    Return: "DEL"

readIntInRange():
    Input: "5" for range [1-10]
    Parse: Integer.parseInt("5") → 5
    Validate: 5 >= 1 && 5 <= 10 ✓
    Return: 5

readOptional():
    Input: "" (empty)
    Return: null
    Input: "  optional value  "
    Trim & Return: "optional value"
```

---

## 14. ERROR HANDLING & USER FEEDBACK

```
API Call Result
    ├─ Network Error (IOException)
    │   └─ ApiResponse(0, "Network error: ...")
    │       └─ Display: "Login failed (HTTP 0): Network error... Tip: verify API base URL..."
    │
    ├─ HTTP 4xx Error (Client error)
    │   └─ ApiResponse(400, "{\"detail\": [{\"msg\": \"Invalid email\", \"loc\": [\"body\", \"email\"]}]}")
    │       └─ extractErrorDetail() parses detail array
    │       └─ Display: "Login failed (HTTP 400): Invalid email at [\"body\", \"email\"]. Please review input format."
    │
    ├─ HTTP 5xx Error (Server error)
    │   └─ ApiResponse(500, "{\"error\": \"Internal server error\"}")
    │       └─ Display: "Login failed (HTTP 500): Internal server error"
    │
    └─ Success (HTTP 200-299)
        └─ ApiResponse(200, "{\"access_token\": \"...\"}")
            └─ Process response normally

Input Validation Error
    ├─ Invalid email format
    │   └─ Loop: "Invalid email format. Expected form: user@example.com... Please try again."
    │
    ├─ Invalid seat format
    │   └─ Loop: "Invalid seat format. Use pattern like 14C or 2A."
    │
    └─ Number out of range
        └─ Loop: "Invalid range. Enter a number between {min} and {max}."

JDBC Error
    └─ catch SQLException: println("Could not load dashboard summary: " + ex.getMessage())
```

---

## 15. STATE TRANSITIONS

```
Initial State:
    token = null
    me = null
    State: authMenu()

After Successful Login:
    token = "eyJhbG..."
    me = {user_id, passenger_id, email, role}
    State: sessionMenu()

During Session:
    Current state: sessionMenu()
    User selects option:
        ├─ 1-8 → Execute corresponding operation
        ├─ 9 (Logout) → Clear token & me → authMenu()
        └─ 0 (Quit) → Exit run() loop → End program

Between API Calls:
    Same token maintained (unless expired)
    Bearer {token} sent in every authenticated request
```

---

## 16. CONCURRENCY MODEL

```
HTTP Calls: SYNCHRONOUS & BLOCKING
    ├─ httpClient.send() blocks until response received
    ├─ No async/CompletableFuture used
    ├─ User must wait for API response to continue
    └─ One request at a time per menu action

JDBC Calls: SYNCHRONOUS & BLOCKING
    ├─ Connection.createStatement() blocks
    ├─ ResultSet iteration blocks
    ├─ No connection pooling (single connection per call)
    └─ One query at a time

Scanner Input: BLOCKING
    ├─ scanner.nextLine() blocks until user input received
    ├─ Holds entire CLI in waiting state
    └─ No timeout or async input handling
```

---

## 17. DATA TRANSFORMATION PIPELINE

```
Example: Search & Book Flow

┌─────────────────────────────────────────────────────────┐
│ CLI Layer: User Input                                    │
│ ├─ Origin: "del" → readAirportCode() → "DEL"           │
│ ├─ Dest: "bom" → readAirportCode() → "BOM"             │
│ └─ Date: "2026-04-20" → readDate() → "2026-04-20"      │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ HTTP Layer: Query Construction                          │
│ ├─ Build query Map                                      │
│ ├─ URL encode: URLEncoder.encode()                      │
│ └─ Final: /flights/search?origin_code=DEL&...          │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ Network Layer: HTTP Request/Response                    │
│ ├─ Send: HttpRequest to backend                         │
│ ├─ Receive: HttpResponse (String body)                  │
│ └─ Body: "[{\"flight_id\": 101, ...}, ...]"            │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ JSON Parsing Layer: Gson Deserialization                │
│ ├─ JsonParser.parseString() → JsonElement              │
│ ├─ .asJsonArray() → JsonArray                          │
│ └─ Array[0].getAsJsonObject() → Single flight JsonObject
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ Business Logic Layer: Flight Selection                  │
│ ├─ Filter flights (user selects index)                 │
│ ├─ Extract fields: flight_id, flight_number, etc.      │
│ └─ Result: selectedFlight JsonObject                    │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ Secondary HTTP: Seat Map Fetch                          │
│ ├─ GET /flights/101/seat-map                           │
│ ├─ Response: JsonArray with seats                       │
│ └─ Parse: Extract cabin_class + seat_number            │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ Seat Processing Layer: Range Computation                │
│ ├─ Loop seats: Find min/max per cabin class            │
│ ├─ Convert seat "14C" → numeric index (row*32+col)     │
│ └─ Result: Map<String, String> {First→"1A to 2F",...} │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ Presentation Layer: Display & Further Input             │
│ ├─ Print seat ranges to user                           │
│ ├─ Read: class type → normalized                       │
│ ├─ Read: seat number → validated/uppercase             │
│ └─ User provides: "economy", "14C"                      │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ Business Logic: Booking Payload Construction            │
│ ├─ Combine all data: passenger_id, flight_id, seat, ... │
│ ├─ Add metadata: tax, service charge, transaction id   │
│ └─ Result: JsonObject payload                           │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ HTTP Layer: Booking Request                             │
│ ├─ Serialize JsonObject to JSON string                 │
│ ├─ POST /bookings with Auth Bearer token               │
│ ├─ Receive: HttpResponse (booking confirmation)        │
│ └─ Body: "{\"booking_reference\": \"PNR00001234\",...}"│
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ Final Layer: Response Parsing & Display                 │
│ ├─ Parse JSON → JsonObject                             │
│ ├─ Extract: booking_reference, seat_number, total      │
│ └─ Print confirmation to user                          │
└─────────────────────────────────────────────────────────┘
```

---

## 18. Key Data Dependencies & Flow Rules

### Request → Response Mapping:

| Operation | Input | Request | Response | Output |
|-----------|-------|---------|----------|--------|
| Login | email, pass | POST /auth/login | {access_token, user} | token stored |
| Search Flights | origin, dest, date | GET /flights/search?... | [{flight_id, prices, ...}] | flights displayed |
| Book | flight_id, seat, class | POST /bookings | {booking_reference, seat_number} | PNR displayed |
| Get Bookings | (token only) | GET /bookings/current | [{booking_reference, seat, ...}] | bookings listed |
| Admin Filter | filters... | GET /admin/bookings?filters | [{pnr, flight, names, ...}] | results filtered |
| Dashboard | (JDBC direct) | SELECT ... | ResultSet → counts/sums | formatted display |

### Field Preservation Across Layers:

```
User enters: "economy" (lowercase user input)
    ↓
normalizeClass("economy") → "Economy" (camelCase for API)
    ↓
Sent in payload: "class_type": "Economy"
    ↓
Backend receives & stores as: class_type="Economy"
    ↓
Response includes: "class_type": "Economy"
    ↓
CLI extracts: getSafe(obj, "class_type") → "Economy"
    ↓
Display: "class | Economy"
```

---

## Summary

**Two Primary Data Channels:**
1. **REST/HTTP Channel** (default): All user-facing operations communicate via FastAPI endpoints
2. **JDBC Channel** (dashboard only): Direct database query execution for metrics

**Key Characteristics:**
- **Synchronous & Blocking**: All operations wait for completion
- **State-based Authentication**: JWT token cached throughout session
- **Validation at Entry**: User input validated before sending to backend
- **Error Resilience**: Null-safe field extraction + detailed error messages
- **Multi-layer Transformation**: User input → CLI validation → API request → Response parsing → Display

**Data Flow Complexity by Operation:**
- Simple: Login (1 HTTP call) → List Bookings (1 HTTP call)
- Complex: Search & Book (3 HTTP calls + local processing) → Admin Explorer (1 HTTP call + filtering)
- Unique: Dashboard (0 HTTP, 4 JDBC queries + formatting)
