package com.ars.admin.service;

import java.sql.Connection;
import java.sql.SQLException;

public interface DashboardMetricsService {
    DashboardSummary fetchSummary(Connection conn) throws SQLException;

    record DashboardSummary(
        long totalBookings,
        long confirmedBookings,
        double totalRevenue,
        double averageOccupancyPercent
    ) {}
}
