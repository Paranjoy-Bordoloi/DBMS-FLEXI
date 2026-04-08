package com.ars.admin.servlet;

import java.io.IOException;
import java.sql.Connection;
import java.sql.SQLException;

import com.ars.admin.db.Database;
import com.ars.admin.service.DashboardMetricsService;
import com.ars.admin.service.DashboardMetricsServiceImpl;
import com.google.gson.JsonObject;

import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

@WebServlet(name = "DashboardServlet", urlPatterns = "/dashboard/summary")
public class DashboardServlet extends HttpServlet {
    private static final String FRONTEND_ORIGIN_LOCALHOST = "http://localhost:5173";
    private static final String FRONTEND_ORIGIN_LOOPBACK = "http://127.0.0.1:5173";

    private final DashboardMetricsService metricsService = new DashboardMetricsServiceImpl();

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        applyCorsHeaders(req, resp);

        resp.setContentType("application/json");
        resp.setCharacterEncoding("UTF-8");

        JsonObject body = new JsonObject();

        try (Connection conn = Database.getConnection()) {
            DashboardMetricsService.DashboardSummary summary = metricsService.fetchSummary(conn);
            body.addProperty("total_bookings", summary.totalBookings());
            body.addProperty("confirmed_bookings", summary.confirmedBookings());
            body.addProperty("total_revenue", summary.totalRevenue());
            body.addProperty("average_occupancy_percent", summary.averageOccupancyPercent());

            resp.setStatus(HttpServletResponse.SC_OK);
            resp.getWriter().write(body.toString());
        } catch (SQLException ex) {
            body.addProperty("detail", "Failed to fetch dashboard summary");
            body.addProperty("error", ex.getMessage());
            resp.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
            resp.getWriter().write(body.toString());
        }
    }

    @Override
    protected void doOptions(HttpServletRequest req, HttpServletResponse resp) {
        applyCorsHeaders(req, resp);
        resp.setStatus(HttpServletResponse.SC_NO_CONTENT);
    }

    private void applyCorsHeaders(HttpServletRequest req, HttpServletResponse resp) {
        String origin = req.getHeader("Origin");
        if (FRONTEND_ORIGIN_LOCALHOST.equals(origin) || FRONTEND_ORIGIN_LOOPBACK.equals(origin)) {
            resp.setHeader("Access-Control-Allow-Origin", origin);
            resp.setHeader("Vary", "Origin");
        }

        resp.setHeader("Access-Control-Allow-Credentials", "true");
        resp.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
        resp.setHeader("Access-Control-Allow-Headers", "Authorization, Content-Type");
        resp.setHeader("Access-Control-Max-Age", "3600");
    }
}
