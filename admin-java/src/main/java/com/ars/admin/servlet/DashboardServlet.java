package com.ars.admin.servlet;

import java.io.IOException;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

import com.ars.admin.db.Database;
import com.google.gson.JsonObject;

import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

@WebServlet(name = "DashboardServlet", urlPatterns = "/dashboard/summary")
public class DashboardServlet extends HttpServlet {
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
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        // Basic CORS for local frontend during development.
        resp.setHeader("Access-Control-Allow-Origin", "http://localhost:5173");
        resp.setHeader("Access-Control-Allow-Credentials", "true");

        resp.setContentType("application/json");
        resp.setCharacterEncoding("UTF-8");

        JsonObject body = new JsonObject();

        try (Connection conn = Database.getConnection()) {
            body.addProperty("total_bookings", countValue(conn, TOTAL_BOOKINGS_SQL));
            body.addProperty("confirmed_bookings", countValue(conn, CONFIRMED_BOOKINGS_SQL));
            body.addProperty("total_revenue", decimalValue(conn, TOTAL_REVENUE_SQL));
            body.addProperty("average_occupancy_percent", decimalValue(conn, OCCUPANCY_SQL));

            resp.setStatus(HttpServletResponse.SC_OK);
            resp.getWriter().write(body.toString());
        } catch (SQLException ex) {
            body.addProperty("detail", "Failed to fetch dashboard summary");
            body.addProperty("error", ex.getMessage());
            resp.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
            resp.getWriter().write(body.toString());
        }
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
