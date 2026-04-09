package com.ars.admin.db;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.Map;

public final class Database {
    private static final Map<String, String> DOTENV_VALUES = loadDotenv();

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
        if (value != null && !value.isBlank()) {
            return value;
        }

        String fromDotenv = DOTENV_VALUES.get(key);
        if (fromDotenv != null && !fromDotenv.isBlank()) {
            return fromDotenv;
        }

        return defaultValue;
    }

    private static Map<String, String> loadDotenv() {
        Path dotenvPath = Paths.get("..", "backend", ".env").normalize();
        if (!Files.exists(dotenvPath)) {
            return Map.of();
        }

        Map<String, String> values = new HashMap<>();
        try (BufferedReader reader = Files.newBufferedReader(dotenvPath, StandardCharsets.UTF_8)) {
            String line;
            while ((line = reader.readLine()) != null) {
                String trimmed = line.trim();
                if (trimmed.isEmpty() || trimmed.startsWith("#")) {
                    continue;
                }

                int separator = trimmed.indexOf('=');
                if (separator <= 0) {
                    continue;
                }

                String key = trimmed.substring(0, separator).trim();
                String rawValue = trimmed.substring(separator + 1).trim();
                if (rawValue.length() >= 2 && rawValue.startsWith("\"") && rawValue.endsWith("\"")) {
                    rawValue = rawValue.substring(1, rawValue.length() - 1);
                }
                values.put(key, rawValue);
            }
        } catch (IOException ignored) {
            return Map.of();
        }

        return values;
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
