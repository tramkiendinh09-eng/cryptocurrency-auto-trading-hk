package com.ruoyi.dca.trade;

import com.ruoyi.dca.domain.enums.TradeRuntimeMode;
import org.junit.jupiter.api.Test;

import java.util.Locale;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class TradeRuntimeModeTest {

    @Test
    void fromCodeSupportsPaperShadowAndLive() {
        assertEquals(TradeRuntimeMode.PAPER, TradeRuntimeMode.fromCode("paper"));
        assertEquals(TradeRuntimeMode.SHADOW, TradeRuntimeMode.fromCode("shadow"));
        assertEquals(TradeRuntimeMode.LIVE, TradeRuntimeMode.fromCode("live"));
        assertEquals(TradeRuntimeMode.PAPER, TradeRuntimeMode.fromCode(" PaPeR "));
        assertThrows(IllegalArgumentException.class, () -> TradeRuntimeMode.fromCode("dca"));
    }

    @Test
    void fromCodeRejectsNullAndBlank() {
        assertThrows(IllegalArgumentException.class, () -> TradeRuntimeMode.fromCode(null));
        assertThrows(IllegalArgumentException.class, () -> TradeRuntimeMode.fromCode(""));
        assertThrows(IllegalArgumentException.class, () -> TradeRuntimeMode.fromCode("   "));
    }

    @Test
    void fromCodeUsesLocaleIndependentNormalization() {
        Locale original = Locale.getDefault();
        try {
            Locale.setDefault(new Locale("tr", "TR"));
            assertEquals(TradeRuntimeMode.LIVE, TradeRuntimeMode.fromCode("live"));
        } finally {
            Locale.setDefault(original);
        }
    }
}