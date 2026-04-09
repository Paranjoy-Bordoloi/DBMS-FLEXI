package com.ars.admin.cli;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Scanner;

import com.ars.admin.db.Database;
import com.ars.admin.service.DashboardMetricsService;
import com.ars.admin.service.DashboardMetricsServiceImpl;
import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonSyntaxException;

/**
 * Interactive Java CLI for the Airline Reservation System APIs.
 *
 * Run:
 * mvn -f admin-java/pom.xml -DskipTests exec:java -Dexec.mainClass=com.ars.admin.cli.AirlineCliApp
 */
public final class AirlineCliApp {
    private static final Gson GSON = new Gson();

    // Private HTTP layer fields
    private final Scanner scanner = new Scanner(System.in);
    private final HttpClient httpClient = HttpClient.newHttpClient();
    private final DashboardMetricsService dashboardMetricsService = new DashboardMetricsServiceImpl();

    private final String baseUrl;
    private String token;
    private JsonObject me;

    // PUBLIC: Database connection fields (accessible to subclasses/external access)
    public Connection dbConnection;
    public boolean isDbConnected = false;

    // PROTECTED: Database configuration (for subclass usage)
    protected String dbHost = "localhost";
    protected String dbPort = "3306";
    protected String dbName = "airline_reservation";
    protected String dbUser = "root";

    public AirlineCliApp(String baseUrl) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
    }

    public static void main(String[] args) {
        String defaultBase = "http://127.0.0.1:8000";
        String selectedBase = defaultBase;

        for (int i = 0; i < args.length; i++) {
            if ("--base-url".equals(args[i]) && i + 1 < args.length) {
                selectedBase = args[i + 1];
                i++;
            }
        }

        AirlineCliApp app = new AirlineCliApp(selectedBase);
        app.run();
    }

    private void run() {
        println("\n=== Airline Reservation CLI (Java) ===");
        println("Connected base URL: " + baseUrl);

        boolean active = true;
        while (active) {
            if (token == null) {
                active = authMenu();
            } else {
                active = sessionMenu();
            }
        }

        closeDbConnection();
        println("Exiting CLI. Goodbye.");
    }

    private boolean authMenu() {
        println("\nAuth Menu");
        println("1) Login");
        println("2) Register");
        println("0) Quit");

        int choice = readIntInRange("Choose an option", 0, 2);
        return switch (choice) {
            case 1 -> {
                login();
                yield true;
            }
            case 2 -> {
                register();
                yield true;
            }
            case 0 -> false;
            default -> true;
        };
    }

    private boolean sessionMenu() {
        String role = me != null && me.has("role") ? me.get("role").getAsString() : "Passenger";
        String email = me != null && me.has("email") ? me.get("email").getAsString() : "unknown";

        println("\nSession Menu");
        println("Signed in as: " + email + " (" + role + ")");
        println("1) Search flights and book");
        println("2) List current bookings");
        println("3) Retrieve booking by PNR");
        println("4) Cancel booking");
        println("5) Change seat");
        println("6) Change flight");
        if ("Admin".equalsIgnoreCase(role)) {
            println("7) Admin booking explorer (filters)");
            println("8) Dashboard summary (JDBC)");
            println("9) Standalone DB queries (JDBC)");
            println("10) Direct SQL executor (Admin)");
            println("11) Data modifications - INSERT/UPDATE/DELETE (Admin)");
        }
        println("12) Logout");
        println("0) Quit");

        int max = 12;  // Both passenger and admin can logout; admin options checked in switch
        int choice = readIntInRange("Choose an option", 0, max);

        switch (choice) {
            case 1 -> searchAndBook();
            case 2 -> listCurrentBookings();
            case 3 -> retrieveBooking();
            case 4 -> cancelBooking();
            case 5 -> changeSeat();
            case 6 -> changeFlight();
            case 7 -> {
                if ("Admin".equalsIgnoreCase(role)) {
                    adminBookingExplorer();
                } else {
                    println("Option 7 is available only for Admin users.");
                }
            }
            case 8 -> {
                if ("Admin".equalsIgnoreCase(role)) {
                    viewDashboardSummary();
                } else {
                    println("Option 8 is available only for Admin users.");
                }
            }
            case 9 -> {
                if ("Admin".equalsIgnoreCase(role)) {
                    standaloneDbQueries();
                } else {
                    println("Option 9 is available only for Admin users.");
                }
            }
            case 10 -> {
                if ("Admin".equalsIgnoreCase(role)) {
                    executeDirectSQL();
                } else {
                    println("Option 10 is available only for Admin users.");
                }
            }
            case 11 -> {
                if ("Admin".equalsIgnoreCase(role)) {
                    dataModificationMenu();
                } else {
                    println("Option 11 is available only for Admin users.");
                }
            }
            case 12 -> logout();
            case 0 -> {
                return false;
            }
            default -> println("Unknown option selected.");
        }
        return true;
    }

    private void login() {
        String email = readEmail("Email");
        String password = readNonEmpty("Password");

        JsonObject payload = new JsonObject();
        payload.addProperty("email", email);
        payload.addProperty("password", password);

        ApiResponse response = call("POST", "/auth/login", payload, null, false);
        if (!response.success()) {
            printApiError("Login failed", response);
            return;
        }

        JsonObject body = response.asObject();
        if (body == null || !body.has("access_token")) {
            println("Login response did not include an access token. Please verify backend auth response.");
            return;
        }

        token = body.get("access_token").getAsString();

        ApiResponse meResp = call("GET", "/auth/me", null, null, true);
        if (!meResp.success()) {
            printApiError("Could not load profile after login", meResp);
            token = null;
            return;
        }

        me = meResp.asObject();
        String role = me != null && me.has("role") ? me.get("role").getAsString() : "Unknown";
        println("Login successful. Role: " + role);
    }

    private void register() {
        println("\nCreate passenger account");
        JsonObject payload = new JsonObject();
        payload.addProperty("first_name", readName("First name"));
        payload.addProperty("last_name", readName("Last name"));
        payload.addProperty("email", readEmail("Email"));
        payload.addProperty("phone", readPhone("Phone (10-15 digits)"));
        payload.addProperty("passport_number", readPassport("Passport number"));
        payload.addProperty("date_of_birth", readDate("Date of birth (YYYY-MM-DD)"));
        payload.addProperty("password", readPassword("Password (min 8 chars)"));
        payload.addProperty("address", readNonEmpty("Address"));

        ApiResponse response = call("POST", "/auth/register", payload, null, false);
        if (!response.success()) {
            printApiError("Registration failed", response);
            return;
        }
        println("Registration successful. You can login now.");
    }

    private void logout() {
        token = null;
        me = null;
        closeDbConnection();
        println("Logged out.");
    }

    private void closeDbConnection() {
        if (isDbConnected && dbConnection != null) {
            try {
                dbConnection.close();
                isDbConnected = false;
                println("✓ Database connection closed");
            } catch (SQLException ex) {
                println("Warning: Error closing database connection: " + ex.getMessage());
            }
        }
    }

    private void searchAndBook() {
        String origin = readAirportCode("Origin airport code (e.g., DEL)");
        String destination = readAirportCode("Destination airport code (e.g., BOM)");
        String travelDate = readDate("Travel date (YYYY-MM-DD)");

        Map<String, String> query = new LinkedHashMap<>();
        query.put("origin_code", origin);
        query.put("destination_code", destination);
        query.put("travel_date", travelDate);
        query.put("sort_by", "price");
        query.put("sort_order", "asc");

        ApiResponse response = call("GET", "/flights/search", null, query, true);
        if (!response.success()) {
            printApiError("Flight search failed", response);
            return;
        }

        JsonArray flights = response.asArray();
        if (flights == null || flights.isEmpty()) {
            println("No flights found for the given route/date. Try changing airport codes or date.");
            return;
        }
        println("\nAvailable flights:");

        for (int i = 0; i < flights.size(); i++) {
            JsonObject f = flights.get(i).getAsJsonObject();
            println((i + 1) + ") flight_id=" + getSafe(f, "flight_id") +
                " | " + getSafe(f, "flight_number") +
                " | " + getSafe(f, "origin_code") + "->" + getSafe(f, "destination_code") +
                " | dep=" + getSafe(f, "departure_time") +
                " | economy=" + getSafe(f, "economy_price"));
        }

        int selectedIndex = readIntInRange("Select flight number from list", 1, flights.size()) - 1;
        JsonObject selectedFlight = flights.get(selectedIndex).getAsJsonObject();
        long selectedFlightId = selectedFlight.get("flight_id").getAsLong();

        Map<String, String> classSeatRanges = fetchSeatRangeIndicators(selectedFlightId);
        printClassSeatRanges(classSeatRanges);

        String classType = readClassType("Class type (Economy/Business/First)");
        String selectedClassRange = classSeatRanges.get(classType);
        if (selectedClassRange != null) {
            println("Selected class seat range: " + selectedClassRange);
        }
        String seat = readOptional("Seat number (optional, e.g., 14C)");

        JsonObject payload = new JsonObject();
        payload.addProperty("passenger_id", me.get("passenger_id").getAsLong());
        payload.addProperty("user_id", me.get("user_id").getAsLong());
        payload.addProperty("flight_id", selectedFlightId);
        if (seat == null || seat.isBlank()) {
            payload.add("seat_number", null);
            payload.addProperty("random_allotment", true);
        } else {
            payload.addProperty("seat_number", seat.toUpperCase(Locale.ROOT));
            payload.addProperty("random_allotment", false);
        }
        payload.addProperty("class_type", classType);
        payload.addProperty("payment_method", "UPI");
        payload.addProperty("transaction_reference", "JAVA-CLI-" + System.currentTimeMillis());
        payload.addProperty("tax_amount", 120.0);
        payload.addProperty("service_charge", 80.0);
        payload.addProperty("use_seat_lock", false);

        ApiResponse bookingResp = call("POST", "/bookings", payload, null, true);
        if (!bookingResp.success()) {
            printApiError("Booking failed", bookingResp);
            return;
        }

        JsonObject body = bookingResp.asObject();
        println("Booking successful.");
        println("PNR: " + getSafe(body, "booking_reference"));
        println("Seat: " + getSafe(body, "seat_number"));
        println("Total: " + getSafe(body, "total_amount"));
    }

    private void listCurrentBookings() {
        ApiResponse response = call("GET", "/bookings/current", null, null, true);
        if (!response.success()) {
            printApiError("Could not fetch current bookings", response);
            return;
        }
        JsonArray rows = response.asArray();
        if (rows == null || rows.isEmpty()) {
            println("No current bookings found.");
            return;
        }
        println("\nCurrent bookings:");
        for (JsonElement row : rows) {
            JsonObject b = row.getAsJsonObject();
            println("PNR " + getSafe(b, "booking_reference") +
                " | " + getSafe(b, "flight_number") +
                " | seat " + getSafe(b, "seat_number") +
                " | " + getSafe(b, "class_type") +
                " | " + getSafe(b, "booking_status"));
        }
    }

    private void retrieveBooking() {
        String pnr = readPnr("PNR (e.g., PNR00000001)");
        String lastName = readName("Passenger last name");

        Map<String, String> query = new LinkedHashMap<>();
        query.put("pnr", pnr);
        query.put("last_name", lastName);

        ApiResponse response = call("GET", "/bookings/retrieve", null, query, true);
        if (!response.success()) {
            printApiError("Booking retrieval failed", response);
            return;
        }

        println(prettyJson(response.body()));
    }

    private void cancelBooking() {
        String pnr = readPnr("PNR to cancel");
        String reason = readNonEmpty("Cancellation reason");

        JsonObject payload = new JsonObject();
        payload.addProperty("reason", reason);

        ApiResponse response = call("POST", "/bookings/" + pnr + "/cancel", payload, null, true);
        if (!response.success()) {
            printApiError("Cancellation failed", response);
            return;
        }
        println("Cancellation processed: " + prettyJson(response.body()));
    }

    private void changeSeat() {
        String pnr = readPnr("PNR");
        String seat = readSeat("New seat number (e.g., 14C)");

        JsonObject payload = new JsonObject();
        payload.addProperty("new_seat_number", seat);

        ApiResponse response = call("POST", "/bookings/" + pnr + "/change-seat", payload, null, true);
        if (!response.success()) {
            printApiError("Seat change failed", response);
            return;
        }
        println("Seat changed successfully: " + prettyJson(response.body()));
    }

    private void changeFlight() {
        String pnr = readPnr("PNR");
        long flightId = readLong("New flight ID (positive integer)", 1, Long.MAX_VALUE);
        String seat = readOptional("Preferred new seat (optional)");

        JsonObject payload = new JsonObject();
        payload.addProperty("new_flight_id", flightId);
        if (seat != null && !seat.isBlank()) {
            payload.addProperty("new_seat_number", seat.toUpperCase(Locale.ROOT));
        }

        ApiResponse response = call("POST", "/bookings/" + pnr + "/change-flight", payload, null, true);
        if (!response.success()) {
            printApiError("Flight change failed", response);
            return;
        }
        println("Flight changed successfully: " + prettyJson(response.body()));
    }

    private void adminBookingExplorer() {
        String status = readOptional("Status filter (Pending/Confirmed/Cancelled, optional)");
        if (status != null && !status.isBlank() && !isAllowedStatus(status)) {
            println("Invalid status. Allowed values: Pending, Confirmed, Cancelled.");
            return;
        }

        String flightIdRaw = readOptional("Flight ID filter (positive integer, optional)");
        String passengerIdRaw = readOptional("Passenger ID filter (positive integer, optional)");
        String email = readOptional("Passenger email contains (optional)");
        long limit = readLongWithDefault("Limit (1-5000)", 1, 5000, 200);

        Map<String, String> query = new LinkedHashMap<>();
        query.put("limit", String.valueOf(limit));

        if (status != null && !status.isBlank()) {
            query.put("status", normalizeStatus(status));
        }

        Long flightId = parseOptionalLong(flightIdRaw, "Flight ID");
        if (flightIdRaw != null && flightId == null) {
            return;
        }
        if (flightId != null) {
            query.put("flight_id", String.valueOf(flightId));
        }

        Long passengerId = parseOptionalLong(passengerIdRaw, "Passenger ID");
        if (passengerIdRaw != null && passengerId == null) {
            return;
        }
        if (passengerId != null) {
            query.put("passenger_id", String.valueOf(passengerId));
        }

        if (email != null && !email.isBlank()) {
            query.put("passenger_email", email);
        }

        ApiResponse response = call("GET", "/admin/bookings", null, query, true);
        if (!response.success()) {
            printApiError("Admin booking query failed", response);
            return;
        }

        JsonArray rows = response.asArray();
        if (rows == null || rows.isEmpty()) {
            println("No bookings matched the filters.");
            return;
        }

        println("\nAdmin bookings result count: " + rows.size());
        for (JsonElement row : rows) {
            JsonObject b = row.getAsJsonObject();
            println("PNR " + getSafe(b, "booking_reference") +
                " | Flight " + getSafe(b, "flight_id") + " (" + getSafe(b, "flight_number") + ")" +
                " | " + getSafe(b, "passenger_first_name") + " " + getSafe(b, "passenger_last_name") +
                " | " + getSafe(b, "status"));
        }
    }

    private void viewDashboardSummary() {
        try (Connection conn = Database.getConnection()) {
            DashboardMetricsService.DashboardSummary summary = dashboardMetricsService.fetchSummary(conn);
            println("\nDashboard summary:");
            println("Total bookings: " + summary.totalBookings());
            println("Confirmed bookings: " + summary.confirmedBookings());
            println("Total revenue: " + formatInr(summary.totalRevenue()));
            println("Average occupancy (%): " + summary.averageOccupancyPercent());
        } catch (SQLException ex) {
            println("Could not load dashboard summary: " + ex.getMessage());
        }
    }

    private void standaloneDbQueries() {
        if (!ensureDbConnection()) return;

        println("\n=== Standalone Database Query Menu ===");
        println("1) Query bookings by flight");
        println("2) Query passenger booking history");
        println("3) Query payment records");
        println("4) Query flight occupancy");
        println("5) Query all passengers");
        println("0) Back to main menu");

        int choice = readIntInRange("Choose query type", 0, 5);
        switch (choice) {
            case 1 -> queryBookingsByFlight();
            case 2 -> queryPassengerHistory();
            case 3 -> queryPaymentRecords();
            case 4 -> queryFlightOccupancy();
            case 5 -> queryAllPassengers();
            case 0 -> {}
            default -> println("Unknown option.");
        }
    }

    private void queryBookingsByFlight() {
        try {
            long flightId = readLong("Enter flight ID", 1, Long.MAX_VALUE);
            String sql = "SELECT b.booking_reference, p.first_name, p.last_name, b.seat_number, b.class_type, b.status, b.total_amount " +
                        "FROM booking b JOIN passenger p ON b.passenger_id = p.passenger_id " +
                        "WHERE b.flight_id = " + flightId + " ORDER BY b.booking_reference";
            executeAndDisplayQuery(sql, new String[]{"PNR", "First Name", "Last Name", "Seat", "Class", "Status", "Amount"});
        } catch (Exception ex) {
            println("Error querying bookings: " + ex.getMessage());
        }
    }

    private void queryPassengerHistory() {
        try {
            long passengerId = readLong("Enter passenger ID", 1, Long.MAX_VALUE);
            String sql = "SELECT b.booking_reference, f.flight_number, f.departure_time, b.seat_number, b.class_type, b.status, b.total_amount " +
                        "FROM booking b JOIN flight f ON b.flight_id = f.flight_id " +
                        "WHERE b.passenger_id = " + passengerId + " ORDER BY f.departure_time DESC";
            executeAndDisplayQuery(sql, new String[]{"PNR", "Flight", "Departure", "Seat", "Class", "Status", "Amount"});
        } catch (Exception ex) {
            println("Error querying passenger history: " + ex.getMessage());
        }
    }

    private void queryPaymentRecords() {
        try {
            long limit = readLongWithDefault("Limit results (1-10000)", 1, 10000, 100);
            String sql = "SELECT p.payment_id, b.booking_reference, p.amount, p.payment_method, p.transaction_date, p.payment_status " +
                        "FROM payment p JOIN booking b ON p.booking_id = b.booking_id " +
                        "ORDER BY p.transaction_date DESC LIMIT " + limit;
            executeAndDisplayQuery(sql, new String[]{"ID", "PNR", "Amount", "Method", "Date", "Status"});
        } catch (Exception ex) {
            println("Error querying payments: " + ex.getMessage());
        }
    }

    private void queryFlightOccupancy() {
        try {
            String sql = "SELECT f.flight_id, f.flight_number, f.departure_time, a.total_capacity, " +
                        "COUNT(b.booking_id) as booked_seats, " +
                        "ROUND((COUNT(b.booking_id) * 100.0 / a.total_capacity), 2) as occupancy_percent " +
                        "FROM flight f JOIN aircraft a ON f.aircraft_id = a.aircraft_id " +
                        "LEFT JOIN booking b ON f.flight_id = b.flight_id AND b.status IN ('Pending', 'Confirmed') " +
                        "GROUP BY f.flight_id, f.flight_number, f.departure_time, a.total_capacity " +
                        "ORDER BY occupancy_percent DESC LIMIT 50";
            executeAndDisplayQuery(sql, new String[]{"Flight ID", "Number", "Departure", "Capacity", "Booked", "Occupancy %"});
        } catch (Exception ex) {
            println("Error querying occupancy: " + ex.getMessage());
        }
    }

    private void queryAllPassengers() {
        try {
            long limit = readLongWithDefault("Limit results (1-10000)", 1, 10000, 500);
            String sql = "SELECT p.passenger_id, p.first_name, p.last_name, p.email, p.phone, p.passport_number " +
                        "FROM passenger p ORDER BY p.passenger_id DESC LIMIT " + limit;
            executeAndDisplayQuery(sql, new String[]{"ID", "First Name", "Last Name", "Email", "Phone", "Passport"});
        } catch (Exception ex) {
            println("Error querying passengers: " + ex.getMessage());
        }
    }

    private void executeDirectSQL() {
        if (!ensureDbConnection()) return;

        String sql = readNonEmpty("Enter SQL query (SELECT only, for safety)");
        if (!sql.trim().toUpperCase().startsWith("SELECT")) {
            println("Only SELECT queries are allowed for safety.");
            return;
        }

        try {
            println("\nExecuting query...");
            Statement stmt = dbConnection.createStatement();
            ResultSet rs = stmt.executeQuery(sql);
            int columnCount = rs.getMetaData().getColumnCount();

            // Print header
            for (int i = 1; i <= columnCount; i++) {
                System.out.print(rs.getMetaData().getColumnName(i));
                if (i < columnCount) System.out.print(" | ");
            }
            println("");
            println("-".repeat(80));

            // Print rows
            int rowCount = 0;
            while (rs.next() && rowCount < 1000) {
                for (int i = 1; i <= columnCount; i++) {
                    Object value = rs.getObject(i);
                    System.out.print(value != null ? value.toString() : "NULL");
                    if (i < columnCount) System.out.print(" | ");
                }
                println("");
                rowCount++;
            }
            println("\nRows returned: " + rowCount);
            rs.close();
            stmt.close();
        } catch (SQLException ex) {
            println("Query error: " + ex.getMessage());
        }
    }

    private void dataModificationMenu() {
        if (!ensureDbConnection()) return;

        println("\n=== Data Modification Menu (INSERT/UPDATE/DELETE) ===");
        println("1) INSERT - Add new passenger (Example 1)");
        println("2) INSERT - Add new route (Example 2)");
        println("3) UPDATE - Change booking status (Example 3)");
        println("4) UPDATE - Update flight base price (Example 4)");
        println("5) DELETE - Remove expired seat locks (Example 5)");
        println("0) Back to main menu");

        int choice = readIntInRange("Choose operation type", 0, 5);
        println("\n⚠️  WARNING: This will modify the database. Ensure you understand the operation.");
        
        boolean proceed = readYesNo("Confirm operation?");
        if (!proceed) {
            println("Operation cancelled.");
            return;
        }

        switch (choice) {
            case 1 -> insertNewPassenger();
            case 2 -> insertNewRoute();
            case 3 -> updateBookingStatus();
            case 4 -> updateFlightPrice();
            case 5 -> deleteExpiredSeatLocks();
            case 0 -> {}
            default -> println("Unknown option.");
        }
    }

    private void insertNewPassenger() {
        try {
            String firstName = readName("Passenger first name");
            String lastName = readName("Passenger last name");
            String email = readEmail("Email");
            String phone = readPhone("Phone number");
            String passport = readPassport("Passport number");
            String dob = readDate("Date of birth (YYYY-MM-DD)");
            String address = readNonEmpty("Address");

            String sql = String.format(
                "INSERT INTO passenger (first_name, last_name, email, phone, passport_number, date_of_birth, address) " +
                "VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s')",
                firstName, lastName, email, phone, passport, dob, address
            );

            Statement stmt = dbConnection.createStatement();
            int rowsInserted = stmt.executeUpdate(sql);
            stmt.close();

            if (rowsInserted > 0) {
                println("\n✅ SUCCESS: Passenger inserted successfully (" + rowsInserted + " row)");
                println("SQL: " + sql);
            } else {
                println("\n❌ FAILED: No rows inserted");
            }
        } catch (SQLException ex) {
            println("Database error: " + ex.getMessage());
        }
    }

    private void insertNewRoute() {
        try {
            String originCode = readAirportCode("Origin airport code (3 letters)");
            String destCode = readAirportCode("Destination airport code (3 letters)");
            int distance = (int) readLong("Distance in km", 100, 20000);
            int duration = (int) readLong("Estimated duration in minutes", 30, 1440);

            String sql = String.format(
                "INSERT INTO route (origin_code, dest_code, distance_km, estimated_duration_minutes) " +
                "VALUES ('%s', '%s', %d, %d)",
                originCode, destCode, distance, duration
            );

            Statement stmt = dbConnection.createStatement();
            int rowsInserted = stmt.executeUpdate(sql);
            stmt.close();

            if (rowsInserted > 0) {
                println("\n✅ SUCCESS: Route inserted successfully (" + rowsInserted + " row)");
                println("SQL: " + sql);
            } else {
                println("\n❌ FAILED: No rows inserted");
            }
        } catch (SQLException ex) {
            println("Database error: " + ex.getMessage());
        }
    }

    private void updateBookingStatus() {
        try {
            String pnr = readPnr("Booking reference (PNR)");
            println("\nAvailable statuses: Pending, Confirmed, Cancelled");
            String newStatus = readNonEmpty("New booking status");

            if (!isAllowedStatus(newStatus)) {
                println("Invalid status. Allowed: Pending, Confirmed, Cancelled");
                return;
            }

            String normalizedStatus = normalizeStatus(newStatus);
            String sql = String.format(
                "UPDATE booking SET status = '%s' WHERE booking_reference = '%s'",
                normalizedStatus, pnr
            );

            Statement stmt = dbConnection.createStatement();
            int rowsUpdated = stmt.executeUpdate(sql);
            stmt.close();

            if (rowsUpdated > 0) {
                println("\n✅ SUCCESS: Booking status updated (" + rowsUpdated + " row)");
                println("SQL: " + sql);
            } else {
                println("\n❌ FAILED: No booking found with PNR: " + pnr);
            }
        } catch (SQLException ex) {
            println("Database error: " + ex.getMessage());
        }
    }

    private void updateFlightPrice() {
        try {
            long flightId = readLong("Flight ID", 1, Long.MAX_VALUE);
            double newPrice = Double.parseDouble(readNonEmpty("New base price (e.g., 5000.00)"));

            // Verify flight exists
            Statement checkStmt = dbConnection.createStatement();
            ResultSet rs = checkStmt.executeQuery("SELECT flight_id FROM flight WHERE flight_id = " + flightId);
            
            if (!rs.next()) {
                println("❌ Flight not found with ID: " + flightId);
                rs.close();
                checkStmt.close();
                return;
            }
            rs.close();
            checkStmt.close();

            String sql = String.format(
                "UPDATE flight SET base_price = %.2f WHERE flight_id = %d",
                newPrice, flightId
            );

            Statement stmt = dbConnection.createStatement();
            int rowsUpdated = stmt.executeUpdate(sql);
            stmt.close();

            if (rowsUpdated > 0) {
                println("\n✅ SUCCESS: Flight price updated (" + rowsUpdated + " row)");
                println("SQL: " + sql);
            } else {
                println("\n❌ FAILED: Could not update flight");
            }
        } catch (SQLException ex) {
            println("Database error: " + ex.getMessage());
        } catch (NumberFormatException ex) {
            println("Invalid price format. Use format: 5000.00");
        }
    }

    private void deleteExpiredSeatLocks() {
        try {
            String sql = "DELETE FROM seat_lock WHERE expires_at < NOW()";

            println("\nThis will delete all seat locks that have expired.");
            println("SQL: " + sql);

            Statement stmt = dbConnection.createStatement();
            int rowsDeleted = stmt.executeUpdate(sql);
            stmt.close();

            println("\n✅ SUCCESS: Deleted " + rowsDeleted + " expired seat lock(s)");
        } catch (SQLException ex) {
            println("Database error: " + ex.getMessage());
        }
    }

    private boolean readYesNo(String prompt) {
        while (true) {
            String response = readNonEmpty(prompt + " (yes/no)").toLowerCase(Locale.ROOT);
            if (response.startsWith("y") || response.equals("yes")) {
                return true;
            } else if (response.startsWith("n") || response.equals("no")) {
                return false;
            } else {
                println("Please enter 'yes' or 'no'.");
            }
        }
    }

    private void executeAndDisplayQuery(String sql, String[] headers) {
        try {
            if (!isDbConnected) {
                dbConnection = Database.getConnection();
                isDbConnected = true;
            }
            Statement stmt = dbConnection.createStatement();
            ResultSet rs = stmt.executeQuery(sql);

            // Print header
            for (String header : headers) {
                System.out.print(String.format("%-20s", header));
            }
            println("");
            println("-".repeat(headers.length * 20));

            // Print rows
            int rowCount = 0;
            while (rs.next() && rowCount < 500) {
                for (int i = 1; i <= headers.length; i++) {
                    Object value = rs.getObject(i);
                    String displayValue = value != null ? value.toString() : "-";
                    System.out.print(String.format("%-20s", displayValue.substring(0, Math.min(20, displayValue.length()))));
                }
                println("");
                rowCount++;
            }
            println("\nTotal rows: " + rowCount);
            rs.close();
            stmt.close();
        } catch (SQLException ex) {
            println("Database error: " + ex.getMessage());
        }
    }

    private boolean ensureDbConnection() {
        if (isDbConnected && dbConnection != null) {
            return true;
        }
        try {
            dbConnection = Database.getConnection();
            isDbConnected = true;
            println("✓ Database connected");
            return true;
        } catch (SQLException ex) {
            println("Failed to connect to database: " + ex.getMessage());
            isDbConnected = false;
            return false;
        }
    }

    private String formatInr(double amount) {
        DecimalFormatSymbols symbols = new DecimalFormatSymbols(new Locale("en", "IN"));
        DecimalFormat formatter = new DecimalFormat("##,##,##0.00", symbols);
        return "Rs. " + formatter.format(amount);
    }

    private ApiResponse call(String method, String path, JsonObject payload, Map<String, String> query, boolean auth) {
        StringBuilder url = new StringBuilder(baseUrl).append(path);
        if (query != null && !query.isEmpty()) {
            List<String> pairs = new ArrayList<>();
            for (Map.Entry<String, String> entry : query.entrySet()) {
                pairs.add(URLEncoder.encode(entry.getKey(), StandardCharsets.UTF_8) + "=" +
                    URLEncoder.encode(entry.getValue(), StandardCharsets.UTF_8));
            }
            url.append("?").append(String.join("&", pairs));
        }

        HttpRequest.Builder builder = HttpRequest.newBuilder().uri(URI.create(url.toString()));
        builder.header("Content-Type", "application/json");
        if (auth && token != null) {
            builder.header("Authorization", "Bearer " + token);
        }

        if ("GET".equalsIgnoreCase(method)) {
            builder.GET();
        } else {
            builder.method(method, HttpRequest.BodyPublishers.ofString(payload == null ? "{}" : payload.toString()));
        }

        try {
            HttpResponse<String> response = httpClient.send(builder.build(), HttpResponse.BodyHandlers.ofString());
            return new ApiResponse(response.statusCode(), response.body());
        } catch (IOException ex) {
            return new ApiResponse(0, "Network error: " + ex.getMessage());
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            return new ApiResponse(0, "Request interrupted. Please retry.");
        } catch (IllegalArgumentException ex) {
            return new ApiResponse(0, "Invalid request URL. Check base URL format.");
        }
    }

    private int readIntInRange(String label, int min, int max) {
        while (true) {
            String raw = readNonEmpty(label + " [" + min + "-" + max + "]");
            try {
                int value = Integer.parseInt(raw);
                if (value < min || value > max) {
                    println("Invalid range. Enter a number between " + min + " and " + max + ".");
                    continue;
                }
                return value;
            } catch (NumberFormatException ex) {
                println("Invalid number format. Please enter a whole number (e.g., " + min + ").");
            }
        }
    }

    private long readLong(String label, long min, long max) {
        while (true) {
            String raw = readNonEmpty(label);
            try {
                long value = Long.parseLong(raw);
                if (value < min || value > max) {
                    println("Out-of-range input. Enter a value between " + min + " and " + max + ".");
                    continue;
                }
                return value;
            } catch (NumberFormatException ex) {
                println("Type error: expected positive integer. Example input: 12");
            }
        }
    }

    private long readLongWithDefault(String label, long min, long max, long defaultValue) {
        while (true) {
            String raw = readOptional(label + " [default " + defaultValue + "]");
            if (raw == null || raw.isBlank()) {
                return defaultValue;
            }
            try {
                long value = Long.parseLong(raw);
                if (value < min || value > max) {
                    println("Out-of-range input. Enter a value between " + min + " and " + max + ".");
                    continue;
                }
                return value;
            } catch (NumberFormatException ex) {
                println("Type error: expected integer. Example: 200");
            }
        }
    }

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

    private String readOptional(String label) {
        System.out.print(label + ": ");
        String value = scanner.nextLine().trim();
        return value.isEmpty() ? null : value;
    }

    private String readEmail(String label) {
        while (true) {
            String email = readNonEmpty(label).toLowerCase(Locale.ROOT);
            if (email.matches("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")) {
                return email;
            }
            println("Invalid email format. Expected form: user@example.com (must include @ and domain with period).");
        }
    }

    private String readPhone(String label) {
        while (true) {
            String phone = readNonEmpty(label);
            if (phone.matches("^[0-9]{10,15}$")) {
                return phone;
            }
            println("Invalid phone number. Use only digits, length 10 to 15.");
        }
    }

    private String readPassport(String label) {
        while (true) {
            String passport = readNonEmpty(label).toUpperCase(Locale.ROOT);
            if (passport.matches("^[A-Z0-9]{6,20}$")) {
                return passport;
            }
            println("Invalid passport format. Use 6-20 alphanumeric characters.");
        }
    }

    private String readName(String label) {
        while (true) {
            String name = readNonEmpty(label);
            if (name.matches("^[A-Za-z][A-Za-z\\s'-]{0,49}$")) {
                return name;
            }
            println("Invalid name. Use alphabetic characters, spaces, apostrophes, or hyphens.");
        }
    }

    private String readPassword(String label) {
        while (true) {
            String password = readNonEmpty(label);
            if (password.length() >= 8) {
                return password;
            }
            println("Password too short. Minimum length is 8 characters.");
        }
    }

    private String readDate(String label) {
        while (true) {
            String value = readNonEmpty(label);
            try {
                LocalDate.parse(value);
                return value;
            } catch (DateTimeParseException ex) {
                println("Invalid date format. Use YYYY-MM-DD (example: 2026-04-20).");
            }
        }
    }

    private String readAirportCode(String label) {
        while (true) {
            String code = readNonEmpty(label).toUpperCase(Locale.ROOT);
            if (code.matches("^[A-Z]{3}$")) {
                return code;
            }
            println("Invalid airport code. Use exactly 3 letters (example: DEL, BOM).");
        }
    }

    private String readClassType(String label) {
        while (true) {
            String value = readNonEmpty(label);
            String normalized = normalizeClass(value);
            if (normalized != null) {
                return normalized;
            }
            println("Invalid class type. Allowed values: Economy, Business, First.");
        }
    }

    private String readSeat(String label) {
        while (true) {
            String seat = readNonEmpty(label).toUpperCase(Locale.ROOT);
            if (seat.matches("^[0-9]{1,2}[A-Z]$")) {
                return seat;
            }
            println("Invalid seat format. Use pattern like 14C or 2A.");
        }
    }

    private String readPnr(String label) {
        while (true) {
            String pnr = readNonEmpty(label).toUpperCase(Locale.ROOT);
            if (pnr.matches("^[A-Z0-9]{8,12}$")) {
                return pnr;
            }
            println("Invalid PNR. Use 8-12 alphanumeric characters (example: PNR00000001).");
        }
    }

    private Long parseOptionalLong(String value, String fieldName) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            long parsed = Long.parseLong(value);
            if (parsed <= 0) {
                println(fieldName + " must be a positive integer.");
                return null;
            }
            return parsed;
        } catch (NumberFormatException ex) {
            println("Type error in " + fieldName + ". Expected integer (example: 5).");
            return null;
        }
    }

    private boolean isAllowedStatus(String value) {
        String v = value.trim().toLowerCase(Locale.ROOT);
        return "pending".equals(v) || "confirmed".equals(v) || "cancelled".equals(v);
    }

    private String normalizeStatus(String value) {
        String v = value.trim().toLowerCase(Locale.ROOT);
        return switch (v) {
            case "pending" -> "Pending";
            case "confirmed" -> "Confirmed";
            case "cancelled" -> "Cancelled";
            default -> value;
        };
    }

    private String normalizeClass(String value) {
        String v = value.trim().toLowerCase(Locale.ROOT);
        return switch (v) {
            case "economy" -> "Economy";
            case "business" -> "Business";
            case "first" -> "First";
            default -> null;
        };
    }

    private Map<String, String> fetchSeatRangeIndicators(long flightId) {
        ApiResponse seatMapResponse = call("GET", "/flights/" + flightId + "/seat-map", null, null, true);
        if (!seatMapResponse.success()) {
            return Map.of();
        }

        JsonObject seatMap = seatMapResponse.asObject();
        if (seatMap == null || !seatMap.has("seats") || !seatMap.get("seats").isJsonArray()) {
            return Map.of();
        }

        JsonArray seats = seatMap.getAsJsonArray("seats");
        Map<String, Integer> minIndexByClass = new LinkedHashMap<>();
        Map<String, Integer> maxIndexByClass = new LinkedHashMap<>();
        Map<String, String> minSeatByClass = new LinkedHashMap<>();
        Map<String, String> maxSeatByClass = new LinkedHashMap<>();

        for (JsonElement seatElement : seats) {
            if (!seatElement.isJsonObject()) {
                continue;
            }

            JsonObject seatObj = seatElement.getAsJsonObject();
            String cabinClass = getSafe(seatObj, "cabin_class");
            String seatNumber = getSafe(seatObj, "seat_number");
            if ("-".equals(cabinClass) || "-".equals(seatNumber)) {
                continue;
            }

            int seatIndex = seatOrderIndex(seatNumber);
            if (seatIndex < 0) {
                continue;
            }

            Integer currentMin = minIndexByClass.get(cabinClass);
            if (currentMin == null || seatIndex < currentMin) {
                minIndexByClass.put(cabinClass, seatIndex);
                minSeatByClass.put(cabinClass, seatNumber);
            }

            Integer currentMax = maxIndexByClass.get(cabinClass);
            if (currentMax == null || seatIndex > currentMax) {
                maxIndexByClass.put(cabinClass, seatIndex);
                maxSeatByClass.put(cabinClass, seatNumber);
            }
        }

        Map<String, String> ranges = new LinkedHashMap<>();
        for (String cabinClass : List.of("First", "Business", "Economy")) {
            String minSeat = minSeatByClass.get(cabinClass);
            String maxSeat = maxSeatByClass.get(cabinClass);
            if (minSeat != null && maxSeat != null) {
                ranges.put(cabinClass, minSeat + " to " + maxSeat);
            }
        }
        return ranges;
    }

    private void printClassSeatRanges(Map<String, String> ranges) {
        if (ranges == null || ranges.isEmpty()) {
            return;
        }

        println("\nSeat range indicators for this flight:");
        for (String cabinClass : List.of("First", "Business", "Economy")) {
            String range = ranges.get(cabinClass);
            if (range == null) {
                println("- " + cabinClass + ": Not available");
            } else {
                println("- " + cabinClass + ": " + range);
            }
        }
    }

    private int seatOrderIndex(String seatNumber) {
        if (seatNumber == null) {
            return -1;
        }

        String normalized = seatNumber.trim().toUpperCase(Locale.ROOT);
        if (!normalized.matches("^[0-9]{1,3}[A-Z]$")) {
            return -1;
        }

        try {
            int row = Integer.parseInt(normalized.substring(0, normalized.length() - 1));
            int letterOffset = normalized.charAt(normalized.length() - 1) - 'A';
            if (row <= 0 || letterOffset < 0) {
                return -1;
            }
            return row * 32 + letterOffset;
        } catch (NumberFormatException ex) {
            return -1;
        }
    }

    private void printApiError(String prefix, ApiResponse response) {
        if (response.statusCode() == 0) {
            println(prefix + ": " + response.body());
            println("Tip: verify API base URL and ensure backend is running.");
            return;
        }

        String detail = extractErrorDetail(response.body());
        println(prefix + " (HTTP " + response.statusCode() + "):");
        println(detail);
    }

    private String extractErrorDetail(String body) {
        try {
            JsonElement json = JsonParser.parseString(body);
            if (json.isJsonObject()) {
                JsonObject obj = json.getAsJsonObject();
                if (obj.has("detail")) {
                    JsonElement detail = obj.get("detail");
                    if (detail.isJsonArray()) {
                        JsonArray arr = detail.getAsJsonArray();
                        if (!arr.isEmpty() && arr.get(0).isJsonObject()) {
                            JsonObject first = arr.get(0).getAsJsonObject();
                            String msg = first.has("msg") ? first.get("msg").getAsString() : "Validation error";
                            String loc = first.has("loc") ? first.get("loc").toString() : "input";
                            return msg + " at " + loc + ". Please review input format.";
                        }
                    }
                    return detail.isJsonPrimitive() ? detail.getAsString() : detail.toString();
                }
                if (obj.has("error")) {
                    return obj.get("error").getAsString();
                }
            }
        } catch (JsonSyntaxException | IllegalStateException ignored) {
            // Fall back to raw body
        }
        return body;
    }

    private String prettyJson(String body) {
        try {
            JsonElement parsed = JsonParser.parseString(body);
            return GSON.newBuilder().setPrettyPrinting().create().toJson(parsed);
        } catch (JsonSyntaxException | IllegalStateException ex) {
            return body;
        }
    }

    private String getSafe(JsonObject obj, String key) {
        if (obj == null || !obj.has(key) || obj.get(key).isJsonNull()) {
            return "-";
        }
        return obj.get(key).getAsString();
    }

    private void println(String value) {
        System.out.println(value);
    }

    private record ApiResponse(int statusCode, String body) {
        boolean success() {
            return statusCode >= 200 && statusCode < 300;
        }

        JsonObject asObject() {
            try {
                JsonElement parsed = JsonParser.parseString(body);
                return parsed.isJsonObject() ? parsed.getAsJsonObject() : null;
            } catch (JsonSyntaxException | IllegalStateException ex) {
                return null;
            }
        }

        JsonArray asArray() {
            try {
                JsonElement parsed = JsonParser.parseString(body);
                return parsed.isJsonArray() ? parsed.getAsJsonArray() : null;
            } catch (JsonSyntaxException | IllegalStateException ex) {
                return null;
            }
        }
    }
}
