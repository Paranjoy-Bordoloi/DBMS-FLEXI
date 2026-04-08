package com.ars.admin.cli;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Scanner;

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

    private final Scanner scanner = new Scanner(System.in);
    private final HttpClient httpClient = HttpClient.newHttpClient();

    private final String baseUrl;
    private String token;
    private JsonObject me;

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
        }
        println("9) Logout");
        println("0) Quit");

        int max = "Admin".equalsIgnoreCase(role) ? 9 : 9;
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
            case 9 -> logout();
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
        println("Logged out.");
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

        String classType = readClassType("Class type (Economy/Business/First)");
        String seat = readOptional("Seat number (optional, e.g., 14C)");

        JsonObject payload = new JsonObject();
        payload.addProperty("passenger_id", me.get("passenger_id").getAsLong());
        payload.addProperty("user_id", me.get("user_id").getAsLong());
        payload.addProperty("flight_id", selectedFlight.get("flight_id").getAsLong());
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
