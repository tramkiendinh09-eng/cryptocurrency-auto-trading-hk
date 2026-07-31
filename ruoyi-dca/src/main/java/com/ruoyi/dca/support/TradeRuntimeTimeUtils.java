package com.ruoyi.dca.support;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeFormatterBuilder;
import java.time.format.DateTimeParseException;
import java.time.temporal.ChronoField;

public final class TradeRuntimeTimeUtils {
    public static final ZoneId DATABASE_ZONE = ZoneId.of("Asia/Shanghai");
    public static final DateTimeFormatter SQL_DATETIME_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private static final DateTimeFormatter SQL_DATETIME_WITH_OPTIONAL_FRACTION = new DateTimeFormatterBuilder()
        .appendPattern("yyyy-MM-dd HH:mm:ss")
        .optionalStart()
        .appendFraction(ChronoField.NANO_OF_SECOND, 1, 9, true)
        .optionalEnd()
        .toFormatter();

    private TradeRuntimeTimeUtils() {
    }

    public static LocalDateTime nowDatabaseLocalDateTime() {
        return LocalDateTime.now(DATABASE_ZONE);
    }

    public static String nowSqlDateTime() {
        return formatSqlDateTime(nowDatabaseLocalDateTime());
    }

    public static String formatSqlDateTime(LocalDateTime dateTime) {
        return dateTime == null ? null : dateTime.withNano(0).format(SQL_DATETIME_FORMATTER);
    }

    public static String normalizeToDatabaseDateTime(String value) {
        String normalized = value == null ? null : value.trim();
        if (normalized == null || normalized.isEmpty()) {
            return value;
        }
        if (normalized.matches("^-?\\d+$")) {
            return normalized;
        }
        String offsetCandidate = normalized.replace(" ", "T");
        try {
            return formatSqlDateTime(OffsetDateTime.parse(offsetCandidate).atZoneSameInstant(DATABASE_ZONE).toLocalDateTime());
        } catch (DateTimeParseException ignored) {
        }
        try {
            return formatSqlDateTime(Instant.parse(offsetCandidate).atZone(DATABASE_ZONE).toLocalDateTime());
        } catch (DateTimeParseException ignored) {
        }
        try {
            return formatSqlDateTime(LocalDateTime.parse(normalized, SQL_DATETIME_WITH_OPTIONAL_FRACTION));
        } catch (DateTimeParseException ignored) {
        }
        try {
            return formatSqlDateTime(LocalDateTime.parse(offsetCandidate));
        } catch (DateTimeParseException ignored) {
            return value;
        }
    }

    public static LocalDateTime parseDatabaseDateTime(String value) {
        String normalized = normalizeToDatabaseDateTime(value);
        if (normalized == null || normalized.trim().isEmpty() || normalized.matches("^-?\\d+$")) {
            return null;
        }
        try {
            return LocalDateTime.parse(normalized.trim(), SQL_DATETIME_FORMATTER);
        } catch (DateTimeParseException ignored) {
            return null;
        }
    }
}
