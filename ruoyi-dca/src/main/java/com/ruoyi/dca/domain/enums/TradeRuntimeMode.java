package com.ruoyi.dca.domain.enums;

import com.fasterxml.jackson.annotation.JsonCreator;

import java.util.Locale;

public enum TradeRuntimeMode {
    PAPER,
    SHADOW,
    LIVE;

    @JsonCreator
    public static TradeRuntimeMode fromCode(String code) {
        if (code == null) {
            throw new IllegalArgumentException("trade runtime mode code must not be null");
        }
        String normalized = code.trim();
        if (normalized.isEmpty()) {
            throw new IllegalArgumentException("trade runtime mode code must not be blank");
        }
        return TradeRuntimeMode.valueOf(normalized.toUpperCase(Locale.ROOT));
    }
}
