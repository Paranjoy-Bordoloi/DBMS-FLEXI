# Quick Reference: Using Data Modification Operations

## Navigation
```
Session Menu → Option 11 → Data Modification Menu → Choose 1-5
```

## 5 Operations at a Glance

| # | Operation | SQL Action | Use Case | Required Fields |
|---|-----------|-----------|----------|-----------------|
| 1 | Insert Passenger | `INSERT INTO passenger` | Add new customer profile | first_name, last_name, email, phone, passport, dob, address |
| 2 | Insert Route | `INSERT INTO route` | Create new flight route | origin_code, dest_code, distance_km, duration_minutes |
| 3 | Update Booking Status | `UPDATE booking SET status` | Change booking state | PNR, new_status (Pending/Confirmed/Cancelled) |
| 4 | Update Flight Price | `UPDATE flight SET base_price` | Adjust flight pricing | flight_id, new_price |
| 5 | Delete Seat Locks | `DELETE FROM seat_lock WHERE expires_at < NOW()` | Clean expired locks | (none - automatic) |

---

## Step-by-Step Examples

### Operation 1: Add New Passenger
```
Option 11 → 1 [Confirm] → Enter:
  First name: Priya
  Last name: Singh
  Email: priya@example.com
  Phone: 9123456789
  Passport: IN1234567
  DOB: 1992-03-20
  Address: 456 Park Ave, Mumbai

Result: ✅ New passenger_id created in database
```

### Operation 2: Add New Route
```
Option 11 → 2 [Confirm] → Enter:
  Origin code: BLR
  Destination code: DXB
  Distance km: 2200
  Duration minutes: 240

Result: ✅ New route_id created in database
```

### Operation 3: Update Booking Status
```
Option 11 → 3 [Confirm] → Enter:
  PNR: PNR00001234
  New status: Confirmed

Result: ✅ Booking changed from Pending → Confirmed
```

### Operation 4: Update Flight Price
```
Option 11 → 4 [Confirm] → Enter:
  Flight ID: 5
  New price: 6500.00

Result: ✅ Base price changed from 5000.00 → 6500.00
        All new bookings use new price
```

### Operation 5: Delete Expired Locks
```
Option 11 → 5 [Confirm]

Result: ✅ Deleted 42 expired seat lock(s)
        Those 42 seats now available for booking
```

---

## Input Validation Rules

### Names (Passenger First/Last Name)
✓ Allowed: A-Z, a-z, spaces, hyphens, apostrophes
✗ Not allowed: numbers, special chars (except -, ')
✗ Examples: 
  - ✓ "Jean-Pierre" 
  - ✓ "Mary O'Brien"
  - ✗ "Mary123"

### Email
✓ Format: `user@domain.com`
✓ Must be unique (not already in use)
✗ Examples:
  - ✓ "john@example.com"
  - ✗ "john@example" (missing domain)

### Phone Number
✓ Length: 10-15 digits
✓ Only digits, no formatting
✗ Examples:
  - ✓ "9876543210"
  - ✗ "+91-98765-43210" (special chars)

### Airport Codes
✓ Length: exactly 3 letters
✓ Must be uppercase
✓ Must exist in airport table
✗ Examples:
  - ✓ "DEL", "BOM", "BLR"
  - ✗ "del" (must be uppercase)
  - ✗ "DL" (must be 3 letters)

### Passport Number
✓ Length: 6-20 characters
✓ Alphanumeric (letters + digits) uppercase
✓ Must be unique
✗ Examples:
  - ✓ "AB1234567"
  - ✓ "IN9876543210"
  - ✗ "ab123" (too short, lowercase)

### Date of Birth
✓ Format: YYYY-MM-DD
✓ Must be valid date
✓ Person should be 18+ years old typically
✗ Examples:
  - ✓ "1990-05-15"
  - ✗ "05-15-1990" (wrong format)

### Booking Status
✓ Values: "Pending", "Confirmed", "Cancelled"
✓ Case-insensitive (converts to proper case internally)
✗ Examples:
  - ✓ "pending" → normalizes to "Pending"
  - ✓ "CONFIRMED" → normalizes to "Confirmed"
  - ✗ "On Hold" (not a valid status)

### Flight Price
✓ Format: decimal number with 2 decimal places
✓ Positive value
✓ Examples: 5000.00, 5000.50, 99999.99
✗ Examples:
  - ✓ "5000.00"
  - ✓ "6500" (auto-converts to 6500.00)
  - ✗ "5000" (missing decimals - may error)

### Distance & Duration
✓ Distance km: 100-20000
✓ Duration minutes: 30-1440 (half hour to 24 hours)
✗ Examples:
  - ✓ Distance: 1437, 12000, 150
  - ✓ Duration: 30, 180, 600
  - ✗ Distance: 50 (too short, 100+ required)

---

## Error Messages & Fixes

### "Email already exists"
**Cause:** Email is already used by another passenger
**Fix:** Use a different email address

### "Passport already exists"
**Cause:** Passport number is already in database
**Fix:** Use a different passport number

### "Invalid email format"
**Cause:** Email doesn't match standard format
**Fix:** Use format: `user@domain.com`

### "Phone must be 10-15 digits"
**Cause:** Phone number too short/long or has non-digit chars
**Fix:** Enter 10-15 digits only, no spaces or symbols

### "Date must be YYYY-MM-DD format"
**Cause:** Incorrect date format
**Fix:** Use format: `1990-05-15` not `05-15-1990`

### "Only Pending, Confirmed, or Cancelled are valid statuses"
**Cause:** Entered invalid booking status
**Fix:** Use one of: Pending, Confirmed, Cancelled

### "Flight not found with ID: 5"
**Cause:** Flight ID doesn't exist
**Fix:** Enter a valid flight ID that exists in database

### "No booking found with PNR: PNR00001234"
**Cause:** PNR/booking reference not in database
**Fix:** Verify PNR is correct (check Option 2)

### "Database error: [specific SQL error]"
**Cause:** SQL execution failed
**Fix:** Check input validation, ensure database is running, verify airport codes exist

---

## Database Impact & Reversibility

| Operation | Impact | Reversibility | Notes |
|-----------|--------|----------------|-------|
| INSERT Passenger | Creates new passenger record | ❌ Not reversible from CLI | Must be deleted via database admin |
| INSERT Route | Creates new route | ❌ Not reversible from CLI | Must be deleted via database admin |
| UPDATE Booking Status | Changes booking state | ✅ Reversible (use Option 3 again) | Can change back to previous status |
| UPDATE Flight Price | Changes pricing for NEW bookings | ✅ Partially reversible | Existing bookings keep old price, new bookings use new price |
| DELETE Seat Locks | Removes expired locks permanently | ❌ Irreversible | Only deletes already-expired locks (safe operation) |

---

## Safety Checklist

Before using these operations, verify:

- [ ] You are logged in as Admin
- [ ] You understand the operation (read the 5 examples)
- [ ] You have correct input values ready
- [ ] Database is running (test with Option 9: Queries first)
- [ ] You are NOT in a critical business period (use off-hours)
- [ ] You will respond "yes" to confirmation prompt intentionally

---

## Audit Trail

All operations are executed through JDBC with timestamps tracked in the database. To view recent modifications:

```java
// Option 9: Standalone DB Queries
// Select query type: Check payment records, booking status changes, etc.
// Look for recent entries with your operation timestamp
```

---

## Support & Troubleshooting

**Problem:** "Operation cancelled" appears
**Solution:** You answered "no" to confirmation prompt. Re-run operation and answer "yes" to confirm.

**Problem:** Data doesn't appear after INSERT
**Solution:** 
1. Check for error messages in console
2. Verify all required fields were entered correctly
3. Use Option 9 queries to confirm data in database

**Problem:** UPDATE shows "0 rows affected"
**Solution:**
1. Record doesn't exist (verify ID/PNR is correct)
2. Entered invalid input value (check validation rules)
3. Use Option 10 to run custom SELECT query to verify

**Problem:** DELETE shows "0 deleted"
**Solution:** No expired seat locks exist (only deletes locks with expires_at < NOW)

---

## Common Use Cases

### Scenario 1: Register Walk-in Passenger + Book
1. Option 11 → 1: Insert new passenger (walk-in at counter)
2. Return to main menu
3. Option 1: Search and book (for the new passenger)

### Scenario 2: Manage Flight Pricing
1. Option 11 → 4: Update base price for Event Flight
2. Check bookings at Option 2
3. New bookings use new price, existing keep old price

### Scenario 3: Status Management
1. Option 2: List bookings (see status)
2. Option 11 → 3: Update status to "Confirmed" after payment
3. Repeat for multiple bookings

### Scenario 4: Route Expansion
1. Option 11 → 2: Insert new route
2. Backend admin creates aircraft assignment
3. Flights appear for booking via Option 1

### Scenario 5: Nightly Cleanup
1. Option 11 → 5: Delete expired seat locks (automatic)
2. Frees up seats abandoned during browsing
3. No manual user review needed
