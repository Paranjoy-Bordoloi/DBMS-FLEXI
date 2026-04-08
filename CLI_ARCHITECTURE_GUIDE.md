# Java CLI Architecture & Flow - Comprehensive Viva Guide

**Document Purpose:** Detailed explanation of the Java CLI implementation for the Airline Reservation System, emphasizing Java fundamentals, OOPS principles, JDBC integration, and complete project flow.

---

## Table of Contents
1. [Project Overview & Architecture](#project-overview--architecture)
2. [Java OOPS Principles in Implementation](#java-oops-principles-in-implementation)
3. [JDBC Connection Management](#jdbc-connection-management)
4. [CLI Application Architecture](#cli-application-architecture)
5. [Complete User Flow](#complete-user-flow)
6. [Advanced Features & Input Validation](#advanced-features--input-validation)
7. [Error Handling & API Integration](#error-handling--api-integration)
8. [Viva Q&A Preparation](#viva-qa-preparation)

---

## Project Overview & Architecture

### System Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                   User (Passenger/Admin)                         │
└────────┬────────────────────────────────────────────────────────┘
         │
         ├─────────────────────────────────────────────────────────┐
         │    INTERACTION MODES                                    │
         ├─────────┬─────────────────┬───────────────────────────────┤
         │         │                 │                               │
     REACT    PYTHON CLI      JAVA CLI (Focus)                        │
         │    (bash script)   (This Guide)                           │
         │                                                           │
         └─────────────────────────────────────────────────────────┘
              │
              ├────────────────────────────────────────────────────┐
              │         API COMMUNICATION LAYER                    │
              ├───────────────────────┬────────────────────────────┤
              │                       │                            │
         FastAPI Backend         Java Servlet Backend              │
         (Port 8000)            (Tomcat on Port 8080)             │
         ├─ /auth/*             ├─ /admin/*                       │
         ├─ /flights/*          ├─ /dashboard/*                   │
         ├─ /bookings/*                                           │
         └─ /airports/*                                           │
              │
              └────────────────────────────┐
                                           │
                           ┌───────────────▼────────────┐
                           │    MySQL 8.0 Database      │
                           │  (3NF Normalized Schema)   │
                           └────────────────────────────┘
```

### Three Entry Points

| Entry Point | Technology | Purpose | Use Case |
|---|---|---|---|
| **React Frontend** | React + Vite | Web UI for passengers & admin | Interactive graphical booking |
| **Python CLI** | Python + bash | Command-line passenger interface | Scripting, automation, batch imports |
| **Java CLI (Focus)** | Java 17 + Maven | Command-line admin/passenger interface | Server-side CLI, direct user interaction |

---

## Java OOPS Principles in Implementation

### 1. **Encapsulation** (Data Hiding)

#### Example 1: Private Fields & Access Control
```java
public final class AirlineCliApp {
    private static final Gson GSON = new Gson();              // Singleton GSON instance
    
    private final Scanner scanner = new Scanner(System.in);   // Encapsulated I/O
    private final HttpClient httpClient = HttpClient.newHttpClient();  // Encapsulated HTTP
    
    private final String baseUrl;    // Private config
    private String token;            // Private authentication state
    private JsonObject me;           // Private user session data
    
    // Constructor enforces immutability of baseUrl via final
    public AirlineCliApp(String baseUrl) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(...) : baseUrl;
    }
}
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 31-44

```

**Encapsulation Benefits:**
- **Data Protection:** `token` and `me` are private; external code cannot directly modify authentication state
- **Consistency:** All state changes go through controlled methods (`login()`, `logout()`)
- **Single Responsibility:** Each field manages one aspect (scanner for I/O, httpClient for networking)

#### Example 2: Method-Level Access Control
```java
// Private helper methods (not exposed to external callers)
private boolean authMenu() { ... }              // Only used internally
private ApiResponse call(...) { ... }           // Network logic hidden
private String extractErrorDetail(String) { ... } // Error parsing hidden

// Public entry point (controlled access)
public static void main(String[] args) { ... }
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 77-90 (authMenu), 456-497 (call), 648-679 (extractErrorDetail), 47-62 (main)
```

### 2. **Inheritance & Abstraction**

#### Java's Built-in Abstraction
The CLI inherits from Java's core abstractions:

| Class/Interface | Abstract Concept | Usage in CLI |
|---|---|---|
| `HttpClient` | Network communication protocol | HTTP requests without knowing socket details |
| `Scanner` | Input stream abstraction | Read user input without buffer management |
| `JsonObject` / `JsonArray` (Gson) | JSON data representation | Serialize/deserialize API responses automatically |
| `HttpRequest.Builder` | Request construction pattern | Build complex requests with fluent API |

#### Example: Builder Pattern (Abstraction)
```java
// BEFORE: Manual HTTP request construction (low-level)
// Socket socket = new Socket(host, port);
// OutputStream out = socket.getOutputStream();
// // ... manual protocol handling

// AFTER: Abstracted via HttpRequest.Builder (high-level)
HttpRequest.Builder builder = HttpRequest.newBuilder().uri(URI.create(url));
builder.header("Content-Type", "application/json");
builder.method("POST", HttpRequest.BodyPublishers.ofString(payload));
HttpResponse<String> response = httpClient.send(builder.build(), 
                                   HttpResponse.BodyHandlers.ofString());
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 456-497 (call method implementing builder pattern)
```

**Abstraction Benefit:** Developer focuses on logical request, not protocol details.

### 3. **Polymorphism**

#### Static Polymorphism (Method Overloading)

```java
// OVERLOADED: Same method name, different signatures
private String readNonEmpty(String label) { ... }
private String readOptional(String label) { ... }
private String readEmail(String label) { ... }
private String readPhone(String label) { ... }
private String readPassword(String label) { ... }
private String readDate(String label) { ... }
private String readAirportCode(String label) { ... }

// All share pattern: prompt user, validate input, return value
// But each has SPECIALIZED validation logic
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 510-572 (various validator methods)
```

Example usage:
```java
// Compiler distinguishes at COMPILE TIME which readXxx() to call
String email = readEmail("Email");        // Calls readEmail()
String phone = readPhone("Phone");        // Calls readPhone()
String password = readPassword("Password"); // Calls readPassword()
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Usage in register method (lines 176-182)
```

#### Dynamic Polymorphism (Switch Expression)

```java
// Session menu uses runtime polymorphism via switch
int choice = readIntInRange("Choose option", 0, 9);

switch (choice) {
    case 1 -> searchAndBook();        // POLYMORPHIC: Different behavior at runtime
    case 2 -> listCurrentBookings();
    case 3 -> retrieveBooking();
    case 4 -> cancelBooking();
    case 5 -> changeSeat();
    case 6 -> changeFlight();
    case 7 -> adminBookingExplorer();
    case 9 -> logout();
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 119-138 (sessionMenu method)
}
```

### 4. **Composition Over Inheritance**

The CLI uses **composition** (HAS-A) instead of inheritance (IS-A):

```java
// Composition approach (used in this project)
public final class AirlineCliApp {
    private final Scanner scanner = new Scanner(System.in);           // HAS-A Scanner
    private final HttpClient httpClient = HttpClient.newHttpClient(); // HAS-A HttpClient
    private final Gson GSON = new Gson();                             // HAS-A JSON parser
}

// NOT inheritance (NOT used)
// public class AirlineCliApp extends HttpClient { ... }
// public class AirlineCliApp extends Scanner { ... }
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 31-35
```

**Composition Benefits:**
- **Flexibility:** Can swap implementations (mock scanner for testing)
- **No tight coupling:** CLI doesn't inherit HttpClient's internals
- **Better design:** Following "favor composition over inheritance" principle

---

## JDBC Connection Management

### Understanding JDBC (Java Database Connectivity)

JDBC is Java's standard API for database access. The flow is:

```
Java Application
    ↓
JDBC Driver (mysql-connector-j)
    ↓
MySQL Protocol Handler
    ↓
MySQL Server
    ↓
Database Schema
```

### Database Class: JDBC Initialization

**File:** `admin-java/src/main/java/com/ars/admin/db/Database.java`

```java
package com.ars.admin.db;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public final class Database {
    private Database() { }  // Private constructor: prevents instantiation (utility class pattern)
    
    // Static initializer block: runs ONCE when class is first loaded
    static {
        try {
            Class.forName("com.mysql.cj.jdbc.Driver");
            // Loads MySQL JDBC driver into JVM memory
            // This makes the driver available to DriverManager
        } catch (ClassNotFoundException ex) {
            throw new ExceptionInInitializerError(
                "MySQL JDBC driver not found: " + ex.getMessage()
            );
            // Fail fast if driver not in classpath (Maven pom.xml)
        }
    }
    
    // Helper: Read environment variable with fallback
    private static String readEnv(String key, String defaultValue) {
        String value = System.getenv(key);
        return (value == null || value.isBlank()) ? defaultValue : value;
    }
    
    // Public: Get connection to database
    public static Connection getConnection() throws SQLException {
        // Read DB config from environment variables
        String host = readEnv("DB_HOST", "localhost");
        String port = readEnv("DB_PORT", "3306");
        String dbName = readEnv("DB_NAME", "airline_reservation");
        String user = readEnv("DB_USER", "root");
        String password = readEnv("DB_PASSWORD", "");
        
        // Construct JDBC URL
        String jdbcUrl = String.format(
            "jdbc:mysql://%s:%s/%s?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC",
            host,
            port,
            dbName
        );
        // Example: jdbc:mysql://localhost:3306/airline_reservation?useSSL=false&...
        
        // Get connection from DriverManager
        return DriverManager.getConnection(jdbcUrl, user, password);
    **File:** [`admin-java/src/main/java/com/ars/admin/db/Database.java`](admin-java/src/main/java/com/ars/admin/db/Database.java), Lines 1-40 (complete class)
    }
}
```

### JDBC Flow Explained

```
1. CLASS LOADING:
   Database class is loaded by ClassLoader
   ↓
2. STATIC INITIALIZER:
   Class.forName("com.mysql.cj.jdbc.Driver") executes
   - Loads MySQL JDBC driver
   - Driver registers itself with DriverManager
   ↓
3. CONNECTION REQUEST:
   Database.getConnection() called by CLI
   ↓
4. DRIVER MANAGER:
   DriverManager.getConnection(url, user, password)
   - DriverManager asks ALL registered drivers if they handle this URL
   - MySQL driver recognizes "jdbc:mysql://..." pattern
   ↓
5. HANDSHAKE:
   MySQL driver establishes TCP socket to MySQL server
   - Host: localhost
   - Port: 3306
   - Database: airline_reservation
   ↓
6. AUTHENTICATION:
   MySQL server validates username and password
   ↓
7. CONNECTION OBJECT:
   Returns java.sql.Connection object
   - Used for: Statement, PreparedStatement, CallableStatement execution
   ↓
8. QUERY EXECUTION:
   Connection.createStatement() or Connection.prepareStatement()
   Execute SQL queries
```

### Maven Dependency: JDBC Driver

**File:** `admin-java/pom.xml`

```xml
<dependency>
    <groupId>com.mysql</groupId>
    <artifactId>mysql-connector-j</artifactId>
    <version>9.3.0</version>
</dependency>
**File:** [`admin-java/pom.xml`](admin-java/pom.xml), Lines 23-27
```

**What this does:**
- Maven downloads `mysql-connector-j-9.3.0.jar` from Maven Central Repository
- JAR is added to classpath when project runs
- `Class.forName()` finds the JDBC driver in classpath

**Why JDBC is Important:**
- **Abstraction:** Database doesn't matter—PostgreSQL, Oracle, SQLite use same `java.sql.*` APIs
- **Connection Pooling:** Real applications use `HikariCP`, `C3P0` (but CLI uses simple connections)
- **Resource Management:** Try-with-resources ensures connections close properly

### Current CLI Limitation: No Direct JDBC

**Important Note:** The Java CLI shown does NOT use JDBC for direct database access. Instead, it:

```
Java CLI
    ↓
HTTP Calls (HttpClient)
    ↓
FastAPI Backend (Python)
    ↓
JDBC (at FastAPI level)
    ↓
MySQL Database
```

**Why this design?**
- **Separation of Concerns:** CLI handles UI/UX, FastAPI handles data logic
- **Scalability:** FastAPI manages connection pooling, not CLI
- **Security:** Credentials stored in backend environment, not CLI
- **Reusability:** Same APIs serve React frontend, Python CLI, Java CLI

---

## CLI Application Architecture

### Program Entry Point: `main()` Method

```java
public static void main(String[] args) {
    // 1. Parse command-line arguments
    String defaultBase = "http://127.0.0.1:8000";
    String selectedBase = defaultBase;
    
    for (int i = 0; i < args.length; i++) {
        if ("--base-url".equals(args[i]) && i + 1 < args.length) {
            selectedBase = args[i + 1];
            i++;  // Skip next argument (already consumed)
        }
    }
    
    // 2. Create application instance (single instance per run)
    AirlineCliApp app = new AirlineCliApp(selectedBase);
    
    // 3. Enter main loop (run until user quits)
    app.run();
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 47-62
}
```

**Execution Example:**
```bash
# Default base URL (localhost:8000)
mvn -q -DskipTests exec:java "-Dexec.mainClass=com.ars.admin.cli.AirlineCliApp"

# Custom base URL
mvn -q exec:java "-Dexec.mainClass=com.ars.admin.cli.AirlineCliApp" \
    "-Dexec.args=--base-url http://api.example.com:8000"
```

### Application Lifecycle

```
START → main()
    ↓
    ├─ Parse args
    ├─ Create AirlineCliApp instance
    └─ Call app.run()
        ↓
        ├─ Print welcome banner
        ├─ Initialize state:
        │  ├─ token = null (unauthenticated)
        │  └─ me = null (no user session)
        ├─ Enter authentication loop
        │  ├─ authMenu() shown
        │  ├─ User selects: Login (1), Register (2), or Quit (0)
        │  └─ Loop until: token != null (authenticated) or user quits
        │
        ├─ [If authenticated] Enter session loop
        │  ├─ sessionMenu() shown (different options based on role)
        │  ├─ User selects: Search (1), List bookings (2), Retrieve (3), etc.
        │  ├─ Execute selected operation
        │  ├─ Make API call to backend
        │  ├─ Parse response and display results
        │  └─ Loop until user logs out (9) or quits (0)
        │
        └─ Cleanup & Exit
           ├─ Close Scanner
           ├─ Close HttpClient (resources)
           └─ Print goodbye message

STOP
```

### State Management Pattern

```java
public final class AirlineCliApp {
    private String token;      // Authentication state
    private JsonObject me;     // User session data
}
```

**State Transitions:**

```
Initial State:
┌─────────────┐
│ token=null  │
│ me=null     │
│ (Guest)     │
└─────────────┘
      │
      │ User clicks Login/Register
      │
      ▼
┌────────────────────┐
│ token="JWT..."     │
│ me={...user...}    │
│ (Authenticated)    │
└────────────────────┘
      │
      │ User clicks Logout
      │
      ▼
┌─────────────┐
│ token=null  │
│ me=null     │
│ (Guest)     │
└─────────────┘
```

---

## Complete User Flow

### Flow 1: Launch & Login

```
1. LAUNCH CLI
   $ cd admin-java
   $ mvn -q -DskipTests exec:java "-Dexec.mainClass=com.ars.admin.cli.AirlineCliApp"
   
   OUTPUT:
   === Airline Reservation CLI (Java) ===
   Connected base URL: http://127.0.0.1:8000

2. AUTHENTICATION MENU SHOWN
   Auth Menu
   1) Login
   2) Register
   0) Quit
   
   Choose an option [0-2]:

3. USER SELECTS: 1 (Login)
   Email: admin@airline.com
   Password: ••••••••

4. APPLICATION LOGIC: login() Method
   
   a. Collect credentials via input methods
      ├─ readEmail(): Validates format (user@domain.ext)
      └─ readNonEmpty(): Validates non-empty string
   
   b. Build JSON payload (OOP Pattern: Builder)
      JsonObject payload = new JsonObject();
      payload.addProperty("email", "admin@airline.com");
      payload.addProperty("password", "Admin@1234");
   
   c. HTTP POST to backend
      call("POST", "/auth/login", payload, null, false)
      
      Detailed breakdown of call():
      ┌────────────────────────────────────────────────┐
      │ 1. Build URL: http://127.0.0.1:8000/auth/login│
      │ 2. Create HttpRequest.Builder                  │
      │ 3. Set headers: Content-Type: application/json │
      │ 4. Set body: stringified JSON payload          │
      │ 5. Create HttpRequest from builder             │
      │ 6. Send via HttpClient.send()                  │
      │ 7. Wait for response (blocking call)           │
      │ 8. Return ApiResponse(statusCode, body)        │
      └────────────────────────────────────────────────┘
   
   d. Parse response
      Body: {"access_token":"eyJhbGc...", "token_type":"bearer"}
      
      Extract token:
      token = response.body().get("access_token").getAsString()
   
   e. Fetch user profile (backend confirms authentication)
      call("GET", "/auth/me", null, null, true)  // true = include auth header
      
      Response body:
      {
        "user_id": 1,
        "passenger_id": 5,
        "email": "admin@airline.com",
        "role": "Admin"
      }
      
      Store in session:
      me = JsonObject from response

5. SUCCESS STATE
   token = "eyJhbGc..." (stored in memory)
   me = {"user_id": 1, "passenger_id": 5, ...}
   
   OUTPUT:
   Login successful. Role: Admin

6. NEXT LOOP ITERATION
   Since token != null, sessionMenu() is shown instead of authMenu()
```

### Flow 2: Search & Book Flight

```
1. USER SELECTS: 1 (Search flights and book)

2. INPUT COLLECTION
   readAirportCode("Origin airport code"):
   └─ Validates: 3 alphabetic characters
   └─ Uppercase conversion via Locale.ROOT
   └─ Input: "DEL"
   
   readAirportCode("Destination airport code"):
   └─ Input: "BOM"
   
   readDate("Travel date (YYYY-MM-DD)"):
   └─ Validates: DateTimeParseException handling
   └─ Input: "2026-04-15"

3. BUILD QUERY PARAMETERS
   Using LinkedHashMap (preserves insertion order):
   
   query.put("origin_code", "DEL");
   query.put("destination_code", "BOM");
   query.put("travel_date", "2026-04-15");
   query.put("sort_by", "price");
   query.put("sort_order", "asc");

4. HTTP GET REQUEST WITH QUERY STRING
   call("GET", "/flights/search", null, query, true)
   
   URL Generated:
   http://127.0.0.1:8000/flights/search?origin_code=DEL&destination_code=BOM&travel_date=2026-04-15&sort_by=price&sort_order=asc
   
   URL Encoding handled by URLEncoder.encode():
   ├─ Spaces → %20
   ├─ Special chars → %XX (hex encoding)
   └─ Parameters joined with "&"

5. RESPONSE PARSING (JsonArray)
   Response body:
   [
     {
       "flight_id": 42,
       "flight_number": "AI301",
       "origin_code": "DEL",
       "destination_code": "BOM",
       "departure_time": "2026-04-15 06:00:00",
       "economy_price": 3500.00
     },
     {
       "flight_id": 43,
       "flight_number": "AI305",
       ...
     }
   ]
   
   Parsing via Gson (JSON serialization library):
   ├─ JsonParser.parseString(body) → JsonElement
   ├─ JsonElement.getAsJsonArray() → JsonArray
   └─ Loop through array, deserialize each to JsonObject

6. DISPLAY FLIGHTS
   For loop with index-based access:
   ```
   Available flights:
   1) flight_id=42 | AI301 | DEL->BOM | dep=2026-04-15 06:00:00 | economy=3500.0
   2) flight_id=43 | AI305 | DEL->BOM | dep=2026-04-15 07:15:00 | economy=3200.0
   ```

7. USER SELECTION & SEAT PREFERENCE
   readIntInRange("Select flight number from list", 1, flights.size())
   ├─ Validates: 1 ≤ choice ≤ flights.size()
   ├─ Converts 1-based user choice to 0-based array index
   └─ Index = choice - 1

   readClassType("Class type (Economy/Business/First)"):
   └─ Normalizes via switch expression (Economy → "Economy")
   
   readOptional("Seat number (optional, e.g., 14C)"):
   └─ If blank: random_allotment = true
   └─ If provided: random_allotment = false, seat_number = input

8. BUILD BOOKING PAYLOAD (OOP: Data encapsulation)
   ```
   {
     "passenger_id": 5,
     "user_id": 1,
     "flight_id": 42,
     "seat_number": null,
     "random_allotment": true,
     "class_type": "Economy",
     "payment_method": "UPI",
     "transaction_reference": "JAVA-CLI-1712831200000",
     "tax_amount": 120.0,
     "service_charge": 80.0,
     "use_seat_lock": false
   }
   ```

9. HTTP POST for BOOKING
   call("POST", "/bookings", payload, null, true)
   
   Backend processes:
   ├─ Validates flight availability
   ├─ Checks passenger eligibility
   ├─ Allocates seat (random or specified)
   ├─ Creates booking record
   ├─ Creates payment record
   ├─ Returns booking confirmation (PNR, seat, total amount)

10. RESPONSE HANDLING
    Success response:
    {
      "booking_id": 987,
      "booking_reference": "PNR00000123",
      "seat_number": "28B",
      "class_type": "Economy",
      "total_amount": 3700.0
    }
    
    Output to user:
    Booking successful.
    PNR: PNR00000123
    Seat: 28B
    Total: 3700.0

11. RETURN TO SESSION MENU
    Loop continues, user can:[
      - List bookings
      - Retrieve booking details
      - Cancel booking
      - Change seat
      - Change flight
      - Logout
    ]
```

### Flow 3: Admin Booking Explorer

```
1. USER ROLE CHECK
   if ("Admin".equalsIgnoreCase(role)) {
       println("7) Admin booking explorer (filters)");
   }

2. USER SELECTS: 7 (Admin booking explorer)

3. FILTER INPUT COLLECTION
   Demonstrates optional input handling:
   
   readOptional("Status filter (Pending/Confirmed/Cancelled)"):
   ├─ Returns null if blank
   ├─ Validation via isAllowedStatus()
   ├─ Normalization via normalizeStatus()
   └─ Only added to query if non-null
   
   readOptional("Flight ID filter"):
   └─ parseOptionalLong() handles:
      ├─ null input
      ├─ NumberFormatException
      ├─ Range validation (> 0)
   
   readLongWithDefault("Limit", 1, 5000, 200):
   └─ Default value: 200
   └─ User can press Enter to accept default

4. QUERY BUILDING (Conditional)
   ```
   Map<String, String> query = new LinkedHashMap<>();
   query.put("limit", "200");
   
   if (status != null) {
       query.put("status", status);  // Only if provided
   }
   if (flight_id != null) {
       query.put("flight_id", flight_id);
   }
   if (passenger_id != null) {
       query.put("passenger_id", passenger_id);
   }
   if (email != null) {
       query.put("passenger_email", email);
   }
   ```
   
   Resulting URL:
   /admin/bookings?limit=200&status=Confirmed&flight_id=42

5. API CALL
   call("GET", "/admin/bookings", null, query, true)
   
   Backend applies filters via SQL WHERE:
   ```
   SELECT * FROM Booking
   WHERE status = 'Confirmed'
     AND flight_id = 42
     LIMIT 200
   ```

6. RESPONSE HANDLING
   ```
   Bookings = [
     {
       "booking_id": 100,
       "booking_reference": "PNR00000100",
       "flight_id": 42,
       "passenger_first_name": "John",
       "passenger_last_name": "Doe",
       "status": "Confirmed"
     },
     { ... more bookings ... }
   ]
   ```

7. DISPLAY RESULTS
   ```
   Admin bookings result count: 15
   PNR PNR00000100 | Flight 42 (AI301) | John Doe | Confirmed
   PNR PNR00000101 | Flight 42 (AI301) | Jane Smith | Pending
   ...
   ```

8. RETURN TO MENU
   (Continue session loop)
```

---

## Advanced Features & Input Validation

### 1. Polymorphic Input Validators

Each validator focuses on ONE specific data type, using specialized regex patterns:

#### Email Validation
```java
private String readEmail(String label) {
    while (true) {
        String email = readNonEmpty(label).toLowerCase(Locale.ROOT);
        
        // Regex breakdown:
        // ^[A-Za-z0-9+_.-]+    = username part (alphanumeric + special chars)
        // @                     = separator
        // [A-Za-z0-9.-]+        = domain name
        // \.                    = REQUIRED literal period
        // [A-Za-z]{2,}$         = TLD (.com, .org, .co.uk = minimum 2 letters)
        
        if (email.matches("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")) {
            return email;
        }
        println("Invalid email format. Expected form: user@example.com");
    **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 526-535
    }
}
```

**Regex Explanation:**

| Pattern | Meaning |
|---|---|
| `^` | Start of string (anchors regex to beginning) |
| `[A-Za-z0-9+_.-]+` | One or more: letters, digits, +, _, ., - |
| `@` | Literal @ character (required) |
| `[A-Za-z0-9.-]+` | Domain labels (alphanumeric with dots/hyphens) |
| `\.` | ESCAPED period (. is metachar in regex = "any char", \. = literal period) |
| `[A-Za-z]{2,}` | TLD: 2+ alphabetic characters |
| `$` | End of string (anchors to end) |

#### Phone Validation
```java
private String readPhone(String label) {
    while (true) {
        String phone = readNonEmpty(label);
        
        // Must be exactly 10-15 digits, nothing else
        if (phone.matches("^[0-9]{10,15}$")) {
            return phone;
        }
        println("Invalid phone number. Use only digits, length 10 to 15.");
    **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 537-547
    **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 537-547
    }
}
```

#### Passport Validation
```java
private String readPassport(String label) {
    while (true) {
        String passport = readNonEmpty(label).toUpperCase(Locale.ROOT);
        
        // 6-20 alphanumeric characters
        if (passport.matches("^[A-Z0-9]{6,20}$")) {
            return passport;
        }
        println("Invalid passport format. Use 6-20 alphanumeric characters.");
    **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 549-559
    **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 549-559
    }
}
```

#### Airport Code Validation
```java
private String readAirportCode(String label) {
    while (true) {
        String code = readNonEmpty(label).toUpperCase(Locale.ROOT);
        
        // IATA standard: exactly 3 letters (DEL, BOM, BLR)
        if (code.matches("^[A-Z]{3}$")) {
            return code;
        }
        println("Invalid airport code. Use exactly 3 letters (example: DEL, BOM).");
    **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 597-607
    **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 597-607
    }
}
```

#### Seat Number Validation
```java
private String readSeat(String label) {
    while (true) {
        String seat = readNonEmpty(label).toUpperCase(Locale.ROOT);
        
        // Pattern: 1-2 digits (1-99) + exactly 1 letter (A-Z)
        // Valid: 1A, 12B, 99Z, 5C
        // Invalid: 100A, A1, 12, 1AA
        if (seat.matches("^[0-9]{1,2}[A-Z]$")) {
            return seat;
        }
        println("Invalid seat format. Use pattern like 14C or 2A.");
    **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 609-621
    **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 609-621
    }
}
```

### 2. Numeric Input Validation with Range Checks

```java
private int readIntInRange(String label, int min, int max) {
    while (true) {
        String raw = readNonEmpty(label + " [" + min + "-" + max + "]");
        try {
            int value = Integer.parseInt(raw);
            // Range validation AFTER parsing
            if (value < min || value > max) {
                println("Invalid range. Enter a number between " + min + " and " + max + ".");
                continue;
            }
            return value;
        } catch (NumberFormatException ex) {
            // Numeric parsing failed
            println("Invalid number format. Please enter a whole number (e.g., " + min + ").");
        **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 499-517
        }
    }
}
```

**Flow:** Input → Parse → Validate Range → Return or Retry

### 3. Optional vs. Required Inputs

```java
// REQUIRED: Must not be empty
private String readNonEmpty(String label) {
    while (true) {
        System.out.print(label + ": ");
        String value = scanner.nextLine().trim();
        if (!value.isEmpty()) {
            return value;
        }
        println("Input required. This field cannot be empty.");
    }
}

// OPTIONAL: Can be empty (returns null)
private String readOptional(String label) {
    System.out.print(label + ": ");
    String value = scanner.nextLine().trim();
    return value.isEmpty() ? null : value;
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 510-524
}
```

**Pattern Usage:**
```java
// Seat is optional (random assignment)
String seat = readOptional("Seat number (optional, e.g., 14C)");
if (seat == null || seat.isBlank()) {
    payload.add("seat_number", null);
    payload.addProperty("random_allotment", true);
} else {
    payload.addProperty("seat_number", seat);
    payload.addProperty("random_allotment", false);
}
```

### 4. Normalization: Standardizing Input

```java
// Email normalization: lowercase (email addresses are case-insensitive)
String email = readNonEmpty(label).toLowerCase(Locale.ROOT);

// Airport code normalization: uppercase (IATA codes are uppercase)
String code = readNonEmpty(label).toUpperCase(Locale.ROOT);

// Status normalization for query parameters
private String normalizeStatus(String value) {
    String v = value.trim().toLowerCase(Locale.ROOT);
    return switch (v) {
        case "pending" -> "Pending";
        case "confirmed" -> "Confirmed";
        case "cancelled" -> "Cancelled";
        default -> value;
    };
}
```

**Why Normalization?**
- User types "delhi" → normalized to "DELHI" for airport code
- User types "JOHN@EXAMPLE.COM" → converted to "john@example.com" for database
- Consistency across user input, API, and database

---

## Error Handling & API Integration

### 1. Exception Handling in HTTP Communication

```java
private ApiResponse call(String method, String path, JsonObject payload, 
                        Map<String, String> query, boolean auth) {
    // Build URL...
    HttpRequest.Builder builder = ...;
    
    try {
        // Send HTTP request (blocking call)
        HttpResponse<String> response = httpClient.send(builder.build(), 
                                           HttpResponse.BodyHandlers.ofString());
        
        // Success: create ApiResponse with status code and body
        return new ApiResponse(response.statusCode(), response.body());
        
    } catch (IOException ex) {
        // Network error: timeout, connection refused, etc.
        return new ApiResponse(0, "Network error: " + ex.getMessage());
        
    } catch (InterruptedException ex) {
        // Thread interrupted (request was cancelled)
        Thread.currentThread().interrupt();  // Restore interrupt flag
        return new ApiResponse(0, "Request interrupted. Please retry.");
        
    } catch (IllegalArgumentException ex) {
        // Malformed URL
        return new ApiResponse(0, "Invalid request URL. Check base URL format.");
    **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 456-497
    }
}
```

**Exception Hierarchy:**
```
Throwable
├─ Exception
│  ├─ IOException
│  │  └─ Associated with network/IO errors
│  ├─ InterruptedException
│  │  └─ Associated with thread interruption
│  └─ IllegalArgumentException
│     └─ Associated with invalid parameters
└─ Error
   └─ Not caught (JVM-level failures)
```

### 2. ApiResponse Record: Immutable Response Wrapper

```java
private record ApiResponse(int statusCode, String body) {
    // Record: automatic equals(), hashCode(), toString()
    // Immutable: cannot change statusCode or body after creation
    
    // Convenience method: check if response successful
    boolean success() {
        return statusCode >= 200 && statusCode < 300;  // HTTP success range
    }
    
    // Parsing method: parse JSON object from body
    JsonObject asObject() {
        try {
            JsonElement parsed = JsonParser.parseString(body);
            return parsed.isJsonObject() ? parsed.getAsJsonObject() : null;
        } catch (JsonSyntaxException | IllegalStateException ex) {
            // JSON parsing failed (expected for non-JSON responses)
            return null;
        }
    }
    
    // Parsing method: parse JSON array from body
    JsonArray asArray() {
        try {
            JsonElement parsed = JsonParser.parseString(body);
            return parsed.isJsonArray() ? parsed.getAsJsonArray() : null;
        **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 800-825 (ApiResponse record definition)
        } catch (JsonSyntaxException | IllegalStateException ex) {
            return null;
        }
    }
}
```

**Generated Methods (by Record):**
```java
// Automatically generated from record declaration
public ApiResponse(int statusCode, String body) { ... }  // Constructor
public int statusCode() { ... }                          // Accessor
public String body() { ... }                             // Accessor
public boolean equals(Object obj) { ... }               // Equality
public int hashCode() { ... }                            // Hashing
public String toString() { ... }                         // String representation
```

**Usage:**
```java
ApiResponse response = call("GET", "/flights/search", null, query, true);

// Check success
if (response.success()) {                    // HTTP 200-299
    JsonArray flights = response.asArray();  // Parse as array
    for (JsonElement f : flights) {
        // Process flight
    }
} else {
    String error = extractErrorDetail(response.body());  // Extract error message
    println(error);
}
```

### 3. Error Detail Extraction: Parsing Complex JSON

```java
private String extractErrorDetail(String body) {
    try {
        JsonElement json = JsonParser.parseString(body);
        
        if (json.isJsonObject()) {
            JsonObject obj = json.getAsJsonObject();
            
            // Pattern 1: FastAPI validation errors (nested detail array)
            if (obj.has("detail")) {
                JsonElement detail = obj.get("detail");
                
                if (detail.isJsonArray()) {
                    JsonArray arr = detail.getAsJsonArray();
                    if (!arr.isEmpty() && arr.get(0).isJsonObject()) {
                        JsonObject first = arr.get(0).getAsJsonObject();
                        String msg = first.has("msg") 
                            ? first.get("msg").getAsString() 
                            : "Validation error";
                        String loc = first.has("loc") 
                            ? first.get("loc").toString() 
                            : "input";
                        return msg + " at " + loc + ". Please review input format.";
                    }
                }
                
                // Pattern 2: Simple detail string
                return detail.isJsonPrimitive() 
                    ? detail.getAsString() 
                    : detail.toString();
            }
            
            // Pattern 3: Simple error field
            if (obj.has("error")) {
                return obj.get("error").getAsString();
            }
        }
    } catch (JsonSyntaxException | IllegalStateException ignored) {
        // JSON parsing failed, fall back to raw body
    }
    
    // Fallback: return raw body
    return body;
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 648-679
}
```

**Example Error Responses:**

FastAPI validation error (Pattern 1):
```json
{
  "detail": [
    {
      "type": "value_error.email",
      "loc": ["body", "email"],
      "msg": "invalid email format",
      "input": "notanemail"
    }
  ]
}
```

Simple error (Pattern 3):
```json
{
  "error": "Flight not found"
}
```

### 4. Error Display to User

```java
private void printApiError(String prefix, ApiResponse response) {
    // Network-level error (statusCode = 0)
    if (response.statusCode() == 0) {
        println(prefix + ": " + response.body());
        println("Tip: verify API base URL and ensure backend is running.");
        return;
    }
    
    // HTTP error (4xx, 5xx)
    String detail = extractErrorDetail(response.body());
    println(prefix + " (HTTP " + response.statusCode() + "):");
    println(detail);
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 681-691
}
```

**User Experience:**
```
Login failed (HTTP 401):
Invalid email or password. Please check credentials.

Flight search failed (HTTP 500):
Internal server error at database. Please try again later.
Tip: verify API base URL and ensure backend is running.
```

---

## Viva Q&A Preparation

### Q1: **What is the main purpose of the Java CLI in this project?**

**Answer:**
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 31-45 (instance variables for state), Lines 31-62 (main method initializing state), Lines 77-105 (authenticate method updating state)
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 681-691 (printApiError method handles network errors), Lines 456-497 (call method catches IOException)
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 510-572 (all input validation methods with regex patterns)
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Validators: Lines 549-607, 499-517
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 288-295 (searchAndBook method building query parameters)
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 288-305 (searchAndBook making search request)
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 306-320 (parsing and displaying search results)
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 321-345 (flight selection and booking creation)
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 77-105 (authMenu method with input validation)
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 456-497 (call method implementing HTTP serialization)
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 31-45 (token and role stored in instance variables), Lines 77-105 (authentication logic)
**File:** [`admin-java/src/main/java/com/ars/admin/db/Database.java`](admin-java/src/main/java/com/ars/admin/db/Database.java), Lines 1-40 (complete JDBC initialization example)
**File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 800-825 (ApiResponse record)
The Java CLI provides an interactive command-line interface for passengers and admin users to interact with the Airline Reservation System without using the React web frontend. It demonstrates Java's capabilities in building robust client applications that communicate with backend APIs over HTTP. The CLI specifically showcases:

1. **User Authentication:** Login/Register via JWT tokens
2. **Flight Booking:** Search, book, cancel flights with seat management
3. **Admin Operations:** Booking explorer with advanced filtering
4. **Data Validation:** Client-side input validation before API calls
5. **API Integration:** HTTP communication using Java's modern HttpClient

**Technical Emphasis:**
- Uses OOPS principles (encapsulation, polymorphism)
- Demonstrates JDBC concepts (though indirectly via backend)
- Shows enterprise patterns (Builder, Record, etc.)

---

### Q2: **Explain the architecture layers in this project.**

**Answer:**

```
LAYER 1: PRESENTATION
├─ React Frontend (web UI)
├─ Python CLI (command-line script)
└─ Java CLI (this project)
    ↓ HTTP/REST API calls
LAYER 2: APPLICATION/BUSINESS LOGIC
├─ FastAPI Backend (Python)
├─ Java Servlet Backend (Tomcat)
    ↓ JDBC queries & ORM
LAYER 3: DATA ACCESS
├─ JDBC Driver (mysql-connector-j)
├─ Connection Pooling
├─ SQL Execution
    ↓ 
LAYER 4: DATABASE
└─ MySQL 8.0
    └─ 3NF Normalized Schema
```

**Key Points:**
- **Separation of Concerns:** Each layer has distinct responsibility
- **Scalability:** Multiple frontends share same backend APIs
- **Maintainability:** Changes in one layer don't affect others
- **Reusability:** APIs serve multiple clients

---

### Q3: **What OOPS principles are demonstrated in the Java CLI?**

**Answer:**

| Principle | Implementation | Example |
|---|---|---|
| **Encapsulation** | Private fields + controlled access | `private String token`, `private Scanner scanner` |
| **Polymorphism** | Method overloading (read* validators) | `readEmail()`, `readPhone()`, `readPassword()` |
| **Abstraction** | Using interfaces, hiding complexity | `HttpClient`, `Scanner`, Gson `JsonObject` |
| **Composition** | HAS-A relationships | `AirlineCliApp` contains `Scanner`, `HttpClient` |
| **Immutability** | Using `final`, `record` | `private final String baseUrl; record ApiResponse` |

**Detailed Example: Polymorphism**

```java
// Compile-time polymorphism (overloading)
readEmail()      → validates email format
readPhone()      → validates phone digits
readPassword()   → validates length
readAirportCode()→ validates 3-letter IATA code

// Runtime polymorphism (switch expression)
switch (userChoice) {
    case 1 -> searchAndBook();      // Different method at runtime
    **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Validators: Lines 510-607, Switch: Lines 119-138
    case 2 -> listCurrentBookings();
    case 3 -> retrieveBooking();
}
```

---

### Q4: **Explain JDBC concepts in this project context.**

**Answer:**

Although the Java CLI doesn't directly use JDBC (it uses HTTP API calls), JDBC concepts apply at the backend layer:

**JDBC Flow (at Backend Level):**

```
1. DRIVER LOADING
   Class.forName("com.mysql.cj.jdbc.Driver")
   └─ Loads MySQL JDBC driver into memory
   └─ Driver registers with DriverManager

2. CONNECTION ESTABLISHMENT
   DriverManager.getConnection(url, user, password)
   └─ DriverManager finds appropriate driver
   └─ MySQL driver with mysql-connector-j
   └─ Establishes TCP socket to MySQL server

3. STATEMENT EXECUTION
   Connection.createStatement() or prepareStatement()
   └─ Execute SQL queries
   └─ PreparedStatement for parameterized queries (prevents SQL injection)

4. RESULT PROCESSING
   ResultSet → iterate rows
   └─ Process bookings: loop through ResultSet rows
   └─ Extract column values by name or position

5. RESOURCE CLEANUP
   Close ResultSet, Statement, Connection
   └─ Try-with-resources ensures proper closure
```

**In This CLI:**
The CLI communicates via HTTP, which means:
- Backend performs JDBC operations
- CLI receives JSON responses
- CLI doesn't manage JDBC directly

**Connection String Example:**
```
jdbc:mysql://localhost:3306/airline_reservation?useSSL=false&serverTimezone=UTC
```

**Environment Variables (pom.xml):**
```xml
<dependency>
    <groupId>com.mysql</groupId>
    <artifactId>mysql-connector-j</artifactId>
    <version>9.3.0</version>
</dependency>
```

---

### Q5: **Walk through a complete user interaction: User registers, logs in, books a flight.**

**Answer:**

**Step 1: Registration**
```
User Input:
  First name: John
  Last name: Doe
  Email: john@example.com
  Phone: 9876543210
  Passport: ABC123XYZ
  DOB: 1990-05-15
  Password: SecurePass123
  Address: 123 Main St

Validation (Client-side):
  ✓ Name format: [A-Za-z][A-Za-z\s'-]*
  ✓ Email format: user@domain.ext
  ✓ Phone: 10-15 digits
  ✓ Passport: 6-20 alphanumeric
  ✓ Date: YYYY-MM-DD format
  ✓ Password: min 8 chars

Build Payload (OOP: JSON encapsulation):
  {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "9876543210",
    "passport_number": "ABC123XYZ",
    "date_of_birth": "1990-05-15",
    "password": "SecurePass123",
    "address": "123 Main St"
  }

HTTP POST → /auth/register:
  Backend validation → Database insert → Return success

Output: "Registration successful. You can login now."
```

**Step 2: Login**
```
User Input:
  Email: john@example.com
  Password: SecurePass123

Validation (Client-side):
  ✓ Email format check (@ and . required)
  ✓ Non-empty password

Build Payload:
  {
    "email": "john@example.com",
    "password": "SecurePass123"
  }

HTTP POST → /auth/login:
  Backend validation → JWT token generation → Return token

Response:
  {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  }

Client State Update:
  token = "eyJhbGciOiJIUzI1NiIs..." (stored in memory)

Fetch User Profile:
  HTTP GET → /auth/me (with Authorization header)
  
Response:
  {
    "user_id": 123,
    "passenger_id": 45,
    "first_name": "John",
    "email": "john@example.com",
    "role": "Passenger"
  }

Client State:
  me = JsonObject (stored in memory)

Output: "Login successful. Role: Passenger"
```

**Step 3: Search & Book Flight**
```
User Input:
  Origin: DEL
  Destination: BOM
  Travel Date: 2026-04-15
  Preferred Class: Economy

Validation → Normalization:
  DEL → DEL (already uppercase)
  BOM → BOM
  2026-04-15 → DateTimeFormat valid

Build Query Parameters:
  origin_code=DEL
  destination_code=BOM
  travel_date=2026-04-15
  sort_by=price
  sort_order=asc

HTTP GET → /flights/search?...
  Backend SQL: SELECT * FROM Flight WHERE origin_code='DEL' AND ...

Response (JsonArray):
  [
    {
      "flight_id": 101,
      "flight_number": "AI301",
      "departure_time": "2026-04-15 06:00:00",
      "economy_price": 3500.00
    },
    { ... more flights ... }
  ]

Display & Selection:
  1) AI301 @ 6:00 AM - ₹3500
  2) AI305 @ 7:15 AM - ₹3200
  
  User selects: 1
  Selected flight_id: 101

Seat Preference:
  User input: [blank = random allocation]
  random_allotment = true

Build Booking Payload:
  {
    "passenger_id": 45,
    "user_id": 123,
    "flight_id": 101,
    "class_type": "Economy",
    "seat_number": null,
    "random_allotment": true,
    "payment_method": "UPI",
    "transaction_reference": "JAVA-CLI-1712831200000",
    "tax_amount": 120.0,
    "service_charge": 80.0,
    "use_seat_lock": false
  }

HTTP POST → /bookings:
  Backend:
    - Validate flight capacity
    - Allocate random seat (e.g., 28B)
    - Create booking record
    - Create payment record
    - Trigger runs to validate constraints
    
  Response:
  {
    "booking_id": 501,
    "booking_reference": "PNR00000501",
    "seat_number": "28B",
    "total_amount": 3700.0
  }

Output:
  Booking successful.
  PNR: PNR00000501
  Seat: 28B
  Total: ₹3700
```

---

### Q6: **Explain the input validation strategy in the CLI.**

**Answer:**

The CLI uses a **multi-layer validation strategy** combining regex patterns, type checking, and range validation:

| Layer | Responsibility | Example |
|---|---|---|
| **Syntax Validation** | Verify format matches pattern | Email: user@domain.ext |
| **Type Validation** | Ensure correct data type | Integer: all digits |
| **Range Validation** | Verify value within bounds | Menu choice 1-9 |
| **Semantic Validation** | Backend domain validation | Flight exists, seats available |

**Implementation Example: Email**

```java
private String readEmail(String label) {
    while (true) {
        // 1. Get non-empty input
        String email = readNonEmpty(label)
            .toLowerCase(Locale.ROOT);  // 2. Normalize
        
        // 3. Validate format (regex)
        if (email.matches("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")) {
            return email;  // 4. Return if valid
        }
        
        // 5. Re-prompt if invalid
        println("Invalid email format. Expected form: user@example.com");
    }
}
```

**Validation Flow:**
```
Input (Raw)
  ↓
Non-empty check (readNonEmpty)
  ↓
Normalization (toLowerCase)
  ↓
Format validation (regex)
  ↓
Range validation (if numeric)
  ↓
Return to caller OR re-prompt
```

**Regex Patterns Summary:**
| Data | Pattern | Example |
|---|---|---|
| Email | `^[...]+@[...]+\.[A-Za-z]{2,}$` | john@example.com |
| Phone | `^[0-9]{10,15}$` | 9876543210 |
| Airport | `^[A-Z]{3}$` | DEL, BOM, BLR |
| Seat | `^[0-9]{1,2}[A-Z]$` | 14C, 2A, 29Z |
| Passport | `^[A-Z0-9]{6,20}$` | ABC123XYZ |
| Name | `^[A-Za-z][A-Za-z\s'-]*$` | John O'Neill-Doe |

---

### Q7: **What design patterns are used in this CLI?**

**Answer:**

| Pattern | Location | Purpose |
|---|---|---|
| **Singleton Pattern** | `GSON`, `httpClient` | Single instance for entire application |
| **Builder Pattern** | `HttpRequest.Builder` | Construct complex objects step-by-step |
| **Record Pattern** | `ApiResponse` | Immutable data carrier (Java 16+) |
| **State Pattern** | `token`, `me` | Model authentication state transitions |
| **Strategy Pattern** | Input validators | Different validation strategies per type |
| **Data Mapper** | JSON parsing | Map JSON responses to Java objects |
| **Template Method** | `call()` method | Template for all HTTP interactions |

**Example: Builder Pattern**

```java
HttpRequest.Builder builder = HttpRequest.newBuilder()
    **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 456-497 (call method featuring builder usage)
    .uri(URI.create(url))           // Step 1: Set URI
    .header("Content-Type", "application/json")  // Step 2: Add header
    .method("POST", HttpRequest.BodyPublishers.ofString(payload))  // Step 3: Set method
    
HttpRequest request = builder.build();  // Step 4: Build final request
HttpResponse<String> response = httpClient.send(request, ...);  // Step 5: Send request
```

**Benefit:** Fluent API, optional parameters, readable code construction

---

### Q8: **Explain how authentication works in this system.**

**Answer:**

**Authentication Flow: JWT (JSON Web Token)**

```
1. USER PROVIDES CREDENTIALS
   Email: admin@airline.com
   Password: Admin@1234

2. CLIENT SENDS to /auth/login
   POST /auth/login HTTP/1.1
   Content-Type: application/json
   
   {
     "email": "admin@airline.com",
     "password": "Admin@1234"
   }

3. BACKEND VERIFICATION
   a. Query database: SELECT * FROM AppUser WHERE email = 'admin@airline.com'
   b. Hash provided password: bcrypt("Admin@1234")
   c. Compare with stored hash
   d. If match: continue; if not: return 401 Unauthorized

4. TOKEN GENERATION
   Backend creates JWT:
   Header: { "alg": "HS256", "typ": "JWT" }
   Payload: { "user_id": 1, "email": "admin@airline.com", "exp": 1712920000 }
   Signature: HMAC-SHA256(Header.Payload, secret)
   
   Result: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lk...

5. BACKEND RESPONSE
   HTTP/1.1 200 OK
   {
     "access_token": "eyJhbGciOiJIUzI1NiIs...",
     "token_type": "bearer"
   }

6. CLIENT STORES TOKEN
   Java CLI: private String token = "eyJhbGciOiJIUzI1NiIs..."
   (stored in memory for session duration)

7. SUBSEQUENT REQUESTS
   GET /auth/me
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
   
   Backend decodes JWT:
   a. Extract header/payload/signature
   b. Verify signature using secret key
   c. Check expiration time
   d. Extract user_id from payload
   e. Return user data or 401 if invalid

8. CLIENT LOGOUT
   token = null
   me = null
   State returns to unauthenticated
```

**Why JWT?**
- **Stateless:** No server-side session storage needed
- **Scalable:** Multiple backend instances can verify same token
- **Secure:** Signature prevents tampering
- **Expiration:** Tokens expire, old tokens become invalid

---

### Q9: **How does the CLI handle errors and exceptions?**

**Answer:**

**Three-Level Error Handling:**

```
LEVEL 1: INPUT VALIDATION (Prevent errors)
  └─ Regex validation
  └─ Type checking
  └─ Range validation
  └─ Non-empty checks
  
LEVEL 2: API COMMUNICATION (Handle network errors)
  └─ try-catch IOException
  └─ try-catch InterruptedException
  └─ try-catch IllegalArgumentException
  └─ Return ApiResponse with statusCode 0 on error
  
LEVEL 3: RESPONSE PARSING (Handle malformed responses)
  └─ try-catch JsonSyntaxException
  └─ try-catch IllegalStateException
  └─ Graceful fallback to raw body
```

**Implementation:**

```java
private ApiResponse call(String method, String path, ...) {
    try {
        // Execute HTTP request
        HttpResponse<String> response = 
            httpClient.send(builder.build(), 
                           HttpResponse.BodyHandlers.ofString());
        // Success: return response with actual status code
        return new ApiResponse(response.statusCode(), response.body());
        
    } catch (IOException ex) {
        // Network error (timeout, connection refused, etc.)
        return new ApiResponse(0, "Network error: " + ex.getMessage());
        
    } catch (InterruptedException ex) {
        // Thread was interrupted
        Thread.currentThread().interrupt();
        return new ApiResponse(0, "Request interrupted. Please retry.");
        
    } catch (IllegalArgumentException ex) {
        // Malformed URL
        return new ApiResponse(0, "Invalid request URL. Check base URL format.");
    }
}
```

**Error Display to User:**

```java
ApiResponse response = call(...);
if (!response.success()) {
    **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 648-679 (extractErrorDetail parses API validation errors)
    **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 88-105 (authentication method checks response status)
    **File:** [`admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java`](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java), Lines 681-691 (printApiError displays HTTP status code)
    printApiError("Operation failed", response);
}

// Output examples:
// "Login failed (HTTP 401): Invalid email or password."
// "Flight search failed (HTTP 500): Internal server error at database."
// "Network error: Connection refused at localhost:8000"
```

---

### Q10: **Describe how the CLI manages user sessions.**

**Answer:**

**Session Management Model:**

```
STATE:
  private String token        // JWT access token
  private JsonObject me       // Authenticated user object

TRANSITIONS:

Initial:
  token = null, me = null → UNAUTHENTICATED

After Login:
  token = "eyJ...", me = {...user...} → AUTHENTICATED

During Usage:
  token included in Authorization header for all requests
  me checked for role-based features (admin-only options)

After Logout:
  token = null, me = null → UNAUTHENTICATED (return to auth menu)
```

**Session Flow:**

```java
private boolean run() {
    boolean active = true;
    while (active) {
        // Conditional menu based on authentication state
        if (token == null) {
            // UNAUTHENTICATED: show auth menu
            active = authMenu();  // Login, Register, Quit
        } else {
            // AUTHENTICATED: show session menu
            active = sessionMenu();  // Booking operations, Logout
        }
    }
}
```

**Token Usage in Requests:**

```java
private ApiResponse call(String method, String path, ..., boolean auth) {
    HttpRequest.Builder builder = ...;
    
    // Conditionally add token to Authorization header
    if (auth && token != null) {
        builder.header("Authorization", "Bearer " + token);
    }
    
    // Send request with token so backend can verify authenticity
    return ...; // Response indicates if token valid
}
```

**Session Timeout Handling:**
- Tokens expire after configured duration (e.g., 60 minutes)
- Backend returns 401 Unauthorized if expired
- CLI displays error, prompts user to login again
- No explicit client-side timeout logic (relies on backend)

---

### Q11: **What is the role of JSON/Gson in this CLI?**

**Answer:**

**Gson: JSON Serialization Library**

```
Dependency: com.google.code.gson:gson:2.13.1
Purpose: Convert between JSON strings and Java objects
```

**Usage Patterns:**

| Operation | Method | Example |
|---|---|---|
| **Create JSON** | `new JsonObject()` | Building request payloads |
| **Parse JSON** | `JsonParser.parseString()` | Parsing API responses |
| **Add Fields** | `object.addProperty(key, value)` | Building request body |
| **Read Fields** | `object.get(key).getAsString()` | Extracting response data |
| **Pretty Print** | `GSON.newBuilder().setPrettyPrinting()` | Displaying results |

**Example 1: Building Request Payload**

```java
// Create JSON object for booking request
JsonObject payload = new JsonObject();
payload.addProperty("passenger_id", 45L);
payload.addProperty("flight_id", 101L);
payload.addProperty("class_type", "Economy");
payload.addProperty("random_allotment", true);
payload.addProperty("tax_amount", 120.0);

// Converts to JSON string:
// {
//   "passenger_id": 45,
//   "flight_id": 101,
//   "class_type": "Economy",
//   "random_allotment": true,
//   "tax_amount": 120.0
// }

// Send as HTTP request body
HttpRequest.BodyPublishers.ofString(payload.toString())
```

**Example 2: Parsing Response Array**

```java
// API response body (string)
String body = "[{\"flight_id\":101,...},{\"flight_id\":102,...}]";

// Parse to JsonElement
JsonElement parsed = JsonParser.parseString(body);

// Check type and cast
if (parsed.isJsonArray()) {
    JsonArray flights = parsed.getAsJsonArray();
    
    // Iterate through flights
    for (JsonElement element : flights) {
        JsonObject flight = element.getAsJsonObject();
        
        // Extract fields
        long flightId = flight.get("flight_id").getAsLong();
        String number = flight.get("flight_number").getAsString();
        
        println("Flight " + number + " (ID: " + flightId + ")");
    }
}
```

**Why Gson?**
- **Simplicity:** Easy JSON manipulation without manual parsing
- **Flexibility:** Handles both serialization (Java → JSON) and deserialization (JSON → Java)
- **Type Safety:** Provides `getAsString()`, `getAsLong()`, etc. with automatic casting
- **Null Safety:** Includes `isJsonNull()`, `has()` checks

---

### Q12: **Describe the Admin Booking Explorer feature and its implementation.**

**Answer:**

**Purpose:** Allow admin users to query all bookings with multiple filter options

**Filter Options:**

| Filter | Type | Values | Example |
|---|---|---|---|
| `status` | String | Pending, Confirmed, Cancelled | "Confirmed" |
| `flight_id` | Long | Positive integer | 42 |
| `passenger_id` | Long | Positive integer | 15 |
| `passenger_email` | String | Email substring | "john" |
| `limit` | Long | 1-5000 | 200 (default) |

**Implementation Flow:**

```java
private void adminBookingExplorer() {
    // 1. COLLECT FILTER INPUTS
    // All filters are optional
    String status = readOptional("Status filter");
    String flightIdRaw = readOptional("Flight ID filter");
    String passengerIdRaw = readOptional("Passenger ID filter");
    String email = readOptional("Passenger email contains");
    long limit = readLongWithDefault("Limit", 1, 5000, 200);
    
    // 2. BUILD QUERY MAP (conditional)
    Map<String, String> query = new LinkedHashMap<>();
    query.put("limit", String.valueOf(limit));
    
    // Only add filter if provided (non-null, non-blank)
    if (status != null && !status.isBlank()) {
        query.put("status", normalizeStatus(status));
    }
    
    Long flightId = parseOptionalLong(flightIdRaw, "Flight ID");
    if (flightId != null) {
        query.put("flight_id", String.valueOf(flightId));
    }
    
    // Similar for other filters...
    
    // 3. MAKE API CALL
    ApiResponse response = call("GET", "/admin/bookings", null, query, true);
    
    // 4. PARSE RESPONSE
    JsonArray rows = response.asArray();
    
    // 5. DISPLAY RESULTS
    for (JsonElement row : rows) {
        JsonObject booking = row.getAsJsonObject();
        println("PNR " + getSafe(booking, "booking_reference") +
                " | Flight " + getSafe(booking, "flight_id") +
                " | " + getSafe(booking, "passenger_first_name") + " " +
                getSafe(booking, "passenger_last_name") +
                " | " + getSafe(booking, "status"));
    }
}
```

**Generated API Request:**

```
Query parameters provided:
  - Status: Confirmed
  - Limit: 200

Generated URL:
  /admin/bookings?limit=200&status=Confirmed

Backend SQL (approximate):
  SELECT booking_id, booking_reference, flight_id, passenger_first_name,
         passenger_last_name, status
  FROM Booking
  WHERE status = 'Confirmed'
  LIMIT 200
```

**Key Feature: Optional Parameters**

```java
// parseOptionalLong() handles:
// 1. Null input → returns null
// 2. Blank input → returns null
// 3. Non-numeric input → error message, return null
// 4. Negative number → error message, return null
// 5. Valid positive number → returns Long value

private Long parseOptionalLong(String value, String fieldName) {
    if (value == null || value.isBlank()) {
        return null;  // Optional: not provided
    }
    try {
        long parsed = Long.parseLong(value);
        if (parsed <= 0) {
            println(fieldName + " must be a positive integer.");
            return null;
        }
        return parsed;
    } catch (NumberFormatException ex) {
        println("Type error in " + fieldName + ". Expected integer.");
        return null;
    }
}
```

**Conditional Query Building:**

```java
if (value != null) {
    query.put(key, value);  // Only add if provided
}
```

This ensures backend only processes provided filters, leaving others as optional.

---

## Summary: Key Takeaways for Viva

### Core Concepts
1. **OOPS in Action:** Encapsulation (private fields), Polymorphism (method overloading), Composition (has-a relationships)
2. **Java Modern Features:** Records (immutable data), switch expressions, var inference
3. **HTTP Communication:** HttpClient, URL building, request/response handling
4. **Input Validation:** Regex patterns, type checking, range validation
5. **Error Handling:** Try-catch, exception propagation, user-friendly error messages
6. **JSON Processing:** Gson library for serialization/deserialization
7. **State Management:** Authentication state, session tokens, conditional UI
8. **Design Patterns:** Builder, Singleton, Strategy, State

### JDBC Context (Though Indirect)
While the CLI doesn't directly use JDBC, understand:
- JDBC driver loading (`Class.forName()`)
- Connection strings (`jdbc:mysql://...`)
- SQL prepared statements (backend concept)
- Connection pooling (backend responsibility)

### Architecture Layers
- **Presentation:** CLI (this project)
- **Application Logic:** FastAPI backend
- **Data Access:** JDBC at backend
- **Database:** MySQL 3NF schema

### Authentication
- JWT tokens for stateless authentication
- Token stored in memory during session
- Included in Authorization header for subsequent requests

---

## Additional Resources for Study

### Files to Review
- [AirlineCliApp.java](admin-java/src/main/java/com/ars/admin/cli/AirlineCliApp.java) - Main CLI implementation
- [Database.java](admin-java/src/main/java/com/ars/admin/db/Database.java) - JDBC connection setup
- [pom.xml](admin-java/pom.xml) - Maven dependencies
- [README.md](README.md) - Project overview

### Execution Commands
```bash
# Build project
cd admin-java
mvn clean package

# Run CLI (default localhost:8000)
mvn -q -DskipTests exec:java "-Dexec.mainClass=com.ars.admin.cli.AirlineCliApp"

# Run CLI (custom backend URL)
mvn -q exec:java "-Dexec.mainClass=com.ars.admin.cli.AirlineCliApp" \
    "-Dexec.args=--base-url http://api.example.com:8000"
```

### Concepts to Practice
- Explain authentication flow from user perspective to backend verification
- Walk through booking flow end-to-end with HTTP requests
- Describe how each validator works and its regex pattern
- Discuss why each OOPS principle is applied where it is
- Explain error handling at each layer

---

**Document Complete.** This guide provides comprehensive coverage of the Java CLI for viva preparation, with emphasis on Java fundamentals, JDBC concepts, OOPS implementation, and complete project flow explanation.

