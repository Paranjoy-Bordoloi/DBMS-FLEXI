package com.ars.admin.db;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public final class Database {
    private Database() {
    }

    static {
        try {
            Class.forName("com.mysql.cj.jdbc.Driver");
        } catch (ClassNotFoundException ex) {
            throw new ExceptionInInitializerError("MySQL JDBC driver not found: " + ex.getMessage());
        }
    }

    private static String readEnv(String key, String defaultValue) {
        String value = System.getenv(key);
        return (value == null || value.isBlank()) ? defaultValue : value;
    }

    public static Connection getConnection() throws SQLException {
        String host = readEnv("DB_HOST", "localhost");
        String port = readEnv("DB_PORT", "3306");
        String dbName = readEnv("DB_NAME", "airline_reservation");
        String user = readEnv("DB_USER", "root");
        String password = readEnv("DB_PASSWORD", "");

        String jdbcUrl = String.format(
            "jdbc:mysql://%s:%s/%s?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC",
            host,
            port,
            dbName
        );

        return DriverManager.getConnection(jdbcUrl, user, password);
    }
}
