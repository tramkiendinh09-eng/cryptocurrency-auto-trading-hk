package com.ruoyi.dca.support;

public final class TradeExecutionStatusNormalizer {

    private TradeExecutionStatusNormalizer() {
    }

    public static StatusPair normalize(String executionStatus, String orderStatus) {
        return normalize("", executionStatus, orderStatus);
    }

    public static StatusPair normalize(String businessStatus, String executionStatus, String orderStatus) {
        String normalizedExecutionStatus = normalizeBusinessStatus(businessStatus);
        if (normalizedExecutionStatus.isEmpty()) {
            normalizedExecutionStatus = normalizeBusinessStatus(executionStatus);
        }
        String normalizedOrderStatus = normalizeOrderStatus(orderStatus);
        if (normalizedExecutionStatus.isEmpty() && !normalizedOrderStatus.isEmpty()) {
            normalizedExecutionStatus = businessStatusFromOrderStatus(normalizedOrderStatus);
        }
        if (normalizedExecutionStatus.isEmpty()) {
            normalizedExecutionStatus = "pending";
        }
        if (normalizedOrderStatus.isEmpty()) {
            normalizedOrderStatus = orderStatusFromBusinessStatus(normalizedExecutionStatus);
        }
        return new StatusPair(normalizedExecutionStatus, normalizedOrderStatus);
    }

    public static String normalizeBusinessStatus(String executionStatus) {
        if (executionStatus == null || executionStatus.trim().isEmpty()) {
            return "";
        }
        return executionStatus.trim().toLowerCase();
    }

    public static String normalizeOrderStatus(String orderStatus) {
        if (orderStatus == null || orderStatus.trim().isEmpty()) {
            return "";
        }
        return orderStatus.trim().toUpperCase();
    }

    public static String businessStatusFromOrderStatus(String orderStatus) {
        String normalized = normalizeOrderStatus(orderStatus);
        return switch (normalized) {
            case "FILLED" -> "filled";
            case "PARTIALLY_FILLED" -> "partial";
            case "CANCELED" -> "canceled";
            case "EXPIRED" -> "expired";
            case "REJECTED" -> "failed";
            case "BLOCKED" -> "blocked";
            case "SKIPPED" -> "skipped";
            case "SUBMITTED" -> "submitted";
            default -> normalized.isEmpty() ? "" : "pending";
        };
    }

    public static String orderStatusFromBusinessStatus(String executionStatus) {
        String normalized = normalizeBusinessStatus(executionStatus);
        return switch (normalized) {
            case "filled" -> "FILLED";
            case "partial" -> "PARTIALLY_FILLED";
            case "canceled" -> "CANCELED";
            case "expired" -> "EXPIRED";
            case "failed" -> "REJECTED";
            case "blocked" -> "BLOCKED";
            case "skipped" -> "SKIPPED";
            case "submitted" -> "SUBMITTED";
            default -> "PENDING";
        };
    }

    public record StatusPair(String executionStatus, String orderStatus) {
    }
}
