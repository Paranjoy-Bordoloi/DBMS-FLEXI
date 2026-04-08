package com.ars.admin.service;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

public class DashboardMetricsServiceImpl implements DashboardMetricsService {
    private static final String TOTAL_BOOKINGS_SQL = "SELECT COUNT(*) FROM booking";
    private static final String CONFIRMED_BOOKINGS_SQL = "SELECT COUNT(*) FROM booking WHERE status='Confirmed'";
    private static final String TOTAL_REVENUE_SQL = "SELECT COALESCE(SUM(amount), 0) FROM payment WHERE payment_status='Success'";

    private static final String OCCUPANCY_SQL =
        "SELECT AVG(occ.percent_value) " +
        "FROM (" +
        "  SELECT (COUNT(b.booking_id) / NULLIF(a.total_capacity, 0)) * 100 AS percent_value " +
        "  FROM flight f " +
        "  JOIN aircraft a ON a.aircraft_id = f.aircraft_id " +
        "  LEFT JOIN booking b ON b.flight_id = f.flight_id AND b.status IN ('Pending', 'Confirmed') " +
        "  GROUP BY f.flight_id, a.total_capacity" +
        ") occ";

    @Override
    public DashboardSummary fetchSummary(Connection conn) throws SQLException {
        long totalBookings = countValue(conn, TOTAL_BOOKINGS_SQL);
        long confirmedBookings = countValue(conn, CONFIRMED_BOOKINGS_SQL);
        double totalRevenue = decimalValue(conn, TOTAL_REVENUE_SQL);
        double averageOccupancyPercent = decimalValue(conn, OCCUPANCY_SQL);

        return new DashboardSummary(
            totalBookings,
            confirmedBookings,
            totalRevenue,
            averageOccupancyPercent
        );
    }

    private long countValue(Connection conn, String sql) throws SQLException {
        try (PreparedStatement stmt = conn.prepareStatement(sql);
             ResultSet rs = stmt.executeQuery()) {
            if (rs.next()) {
                return rs.getLong(1);
            }
            return 0;
        }
    }

    private double decimalValue(Connection conn, String sql) throws SQLException {
        try (PreparedStatement stmt = conn.prepareStatement(sql);
             ResultSet rs = stmt.executeQuery()) {
            if (rs.next()) {
                return Math.round(rs.getDouble(1) * 100.0) / 100.0;
            }
            return 0.0;
        }
    }
}
