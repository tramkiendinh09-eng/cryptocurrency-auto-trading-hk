package com.ruoyi.dca.service.trade.impl;

import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.constants.TradeConstants;
import com.ruoyi.dca.domain.trade.TradePositionGuard;
import com.ruoyi.dca.mapper.trade.TradePositionGuardCrudMapper;
import com.ruoyi.dca.mapper.trade.TradeStrategyMapper;
import com.ruoyi.dca.service.trade.ITradePositionGuardService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;
import java.util.Locale;
import java.util.Set;

@Service
public class TradePositionGuardServiceImpl implements ITradePositionGuardService {

    private static final Set<String> ALLOWED_SCOPE_TYPES = Set.of("GLOBAL", "STRATEGY", "SYMBOL");

    @Autowired
    private TradePositionGuardCrudMapper tradePositionGuardMapper;

    @Autowired
    private TradeStrategyMapper tradeStrategyMapper;

    @Override
    public List<TradePositionGuard> selectTradePositionGuardList(TradePositionGuard query) {
        normalizeQuery(query);
        return tradePositionGuardMapper.selectTradePositionGuardList(query);
    }

    @Override
    public int insertTradePositionGuard(TradePositionGuard tradePositionGuard) {
        normalizeAndValidate(tradePositionGuard);
        validateDuplicateGuard(tradePositionGuard);
        return tradePositionGuardMapper.insertTradePositionGuard(tradePositionGuard);
    }

    @Override
    public int updateTradePositionGuard(TradePositionGuard tradePositionGuard) {
        if (tradePositionGuard == null || tradePositionGuard.getId() == null) {
            throw new ServiceException("Position guard id is required");
        }
        TradePositionGuard existing = tradePositionGuardMapper.selectTradePositionGuardById(tradePositionGuard.getId());
        if (existing == null) {
            throw new ServiceException("Position guard does not exist");
        }
        TradePositionGuard merged = mergeWithExisting(existing, tradePositionGuard);
        normalizeAndValidate(merged);
        validateDuplicateGuard(merged);
        return tradePositionGuardMapper.updateTradePositionGuard(merged);
    }

    @Override
    public int deleteTradePositionGuardByIds(Long[] ids) {
        if (ids == null || ids.length == 0) {
            return 0;
        }
        return tradePositionGuardMapper.deleteTradePositionGuardByIds(ids);
    }

    private void normalizeQuery(TradePositionGuard query) {
        if (query == null) {
            return;
        }
        query.setGuardName(trimToNull(query.getGuardName()));
        query.setScopeType(normalizeUpperOrNull(query.getScopeType()));
        query.setSymbol(normalizeUpperOrNull(query.getSymbol()));
        query.setExchangeCode(normalizeUpperOrNull(query.getExchangeCode()));
    }

    private void normalizeAndValidate(TradePositionGuard tradePositionGuard) {
        if (tradePositionGuard == null) {
            throw new ServiceException("Position guard payload is required");
        }
        tradePositionGuard.setGuardName(trimToEmpty(tradePositionGuard.getGuardName()));
        tradePositionGuard.setScopeType(normalizeUpper(tradePositionGuard.getScopeType()));
        tradePositionGuard.setSymbol(normalizeUpperOrNull(tradePositionGuard.getSymbol()));
        tradePositionGuard.setExchangeCode(normalizeUpperOrNull(tradePositionGuard.getExchangeCode()));
        tradePositionGuard.setRemark(trimToNull(tradePositionGuard.getRemark()));
        if (tradePositionGuard.getEnabled() == null) {
            tradePositionGuard.setEnabled(Boolean.TRUE);
        }
        if (tradePositionGuard.getPriority() == null) {
            tradePositionGuard.setPriority(0);
        }

        if (tradePositionGuard.getGuardName().isEmpty()) {
            throw new ServiceException("Position guard name is required");
        }
        if (!ALLOWED_SCOPE_TYPES.contains(tradePositionGuard.getScopeType())) {
            throw new ServiceException("Unsupported position guard scope: " + tradePositionGuard.getScopeType());
        }

        normalizeByScope(tradePositionGuard);
        validateThresholds(tradePositionGuard);
    }

    private void normalizeByScope(TradePositionGuard tradePositionGuard) {
        switch (tradePositionGuard.getScopeType()) {
            case "GLOBAL" -> {
                tradePositionGuard.setStrategyId(null);
                tradePositionGuard.setSymbol(null);
                tradePositionGuard.setExchangeCode(null);
            }
            case "STRATEGY" -> {
                if (tradePositionGuard.getStrategyId() == null) {
                    throw new ServiceException("Strategy-scoped position guard requires strategy");
                }
                validateStrategyExists(tradePositionGuard.getStrategyId());
                tradePositionGuard.setSymbol(null);
                tradePositionGuard.setExchangeCode(null);
            }
            case "SYMBOL" -> {
                if (tradePositionGuard.getSymbol() == null) {
                    throw new ServiceException("Symbol-scoped position guard requires symbol");
                }
                if (tradePositionGuard.getExchangeCode() == null) {
                    throw new ServiceException("Symbol-scoped position guard requires exchange");
                }
                if (!TradeConstants.V1_ALLOWED_SYMBOLS.contains(tradePositionGuard.getSymbol())) {
                    throw new ServiceException("Unsupported position guard symbol: " + tradePositionGuard.getSymbol());
                }
                if (!TradeConstants.V1_ALLOWED_EXCHANGES.contains(tradePositionGuard.getExchangeCode())) {
                    throw new ServiceException("Unsupported position guard exchange: " + tradePositionGuard.getExchangeCode());
                }
                if (tradePositionGuard.getStrategyId() != null) {
                    validateStrategyExists(tradePositionGuard.getStrategyId());
                }
            }
            default -> throw new ServiceException("Unsupported position guard scope: " + tradePositionGuard.getScopeType());
        }
    }

    private void validateThresholds(TradePositionGuard tradePositionGuard) {
        if (tradePositionGuard.getStopLossPct() == null
            && tradePositionGuard.getTakeProfitPct() == null
            && tradePositionGuard.getMaxHoldingMinutes() == null) {
            throw new ServiceException("At least one position guard threshold is required");
        }
        validatePct("stopLossPct", tradePositionGuard.getStopLossPct());
        validatePct("takeProfitPct", tradePositionGuard.getTakeProfitPct());
        if (tradePositionGuard.getMaxHoldingMinutes() != null && tradePositionGuard.getMaxHoldingMinutes() <= 0) {
            throw new ServiceException("maxHoldingMinutes must be greater than zero");
        }
    }

    private void validatePct(String fieldName, BigDecimal value) {
        if (value == null) {
            return;
        }
        if (value.compareTo(BigDecimal.ZERO) <= 0) {
            throw new ServiceException(fieldName + " must be greater than zero");
        }
        if (value.compareTo(BigDecimal.ONE) >= 0) {
            throw new ServiceException(fieldName + " must be less than one");
        }
    }

    private void validateStrategyExists(Long strategyId) {
        if (tradeStrategyMapper.selectTradeStrategyById(strategyId) == null) {
            throw new ServiceException("Referenced strategy does not exist");
        }
    }

    private void validateDuplicateGuard(TradePositionGuard tradePositionGuard) {
        if (!Boolean.TRUE.equals(tradePositionGuard.getEnabled())) {
            return;
        }
        TradePositionGuard query = new TradePositionGuard();
        query.setEnabled(Boolean.TRUE);
        List<TradePositionGuard> existingGuards = tradePositionGuardMapper.selectTradePositionGuardList(query);
        if (existingGuards == null || existingGuards.isEmpty()) {
            return;
        }
        for (TradePositionGuard existing : existingGuards) {
            if (existing == null) {
                continue;
            }
            if (tradePositionGuard.getId() != null && tradePositionGuard.getId().equals(existing.getId())) {
                continue;
            }
            if (!sameNullableText(existing.getScopeType(), tradePositionGuard.getScopeType())) {
                continue;
            }
            if (!sameNullableLong(existing.getStrategyId(), tradePositionGuard.getStrategyId())) {
                continue;
            }
            if (!sameNullableText(existing.getSymbol(), tradePositionGuard.getSymbol())) {
                continue;
            }
            if (!sameNullableText(existing.getExchangeCode(), tradePositionGuard.getExchangeCode())) {
                continue;
            }
            throw new ServiceException("Duplicate enabled position guard already exists for scope");
        }
    }

    private TradePositionGuard mergeWithExisting(TradePositionGuard existing, TradePositionGuard patch) {
        TradePositionGuard merged = new TradePositionGuard();
        merged.setId(existing.getId());
        merged.setGuardName(firstNonNull(patch.getGuardName(), existing.getGuardName()));
        merged.setScopeType(firstNonNull(patch.getScopeType(), existing.getScopeType()));
        merged.setStrategyId(firstNonNull(patch.getStrategyId(), existing.getStrategyId()));
        merged.setSymbol(firstNonNull(patch.getSymbol(), existing.getSymbol()));
        merged.setExchangeCode(firstNonNull(patch.getExchangeCode(), existing.getExchangeCode()));
        merged.setStopLossPct(firstNonNull(patch.getStopLossPct(), existing.getStopLossPct()));
        merged.setTakeProfitPct(firstNonNull(patch.getTakeProfitPct(), existing.getTakeProfitPct()));
        merged.setMaxHoldingMinutes(firstNonNull(patch.getMaxHoldingMinutes(), existing.getMaxHoldingMinutes()));
        merged.setEnabled(firstNonNull(patch.getEnabled(), existing.getEnabled()));
        merged.setPriority(firstNonNull(patch.getPriority(), existing.getPriority()));
        merged.setRemark(firstNonNull(patch.getRemark(), existing.getRemark()));
        return merged;
    }

    private String normalizeUpperOrNull(String value) {
        String normalized = normalizeUpper(value);
        return normalized.isEmpty() ? null : normalized;
    }

    private String normalizeUpper(String value) {
        String trimmed = trimToEmpty(value);
        return trimmed.isEmpty() ? "" : trimmed.toUpperCase(Locale.ROOT);
    }

    private String trimToNull(String value) {
        String trimmed = trimToEmpty(value);
        return trimmed.isEmpty() ? null : trimmed;
    }

    private String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }

    private boolean sameNullableText(String left, String right) {
        String normalizedLeft = left == null ? null : left.trim();
        String normalizedRight = right == null ? null : right.trim();
        return normalizedLeft == null ? normalizedRight == null : normalizedLeft.equalsIgnoreCase(normalizedRight);
    }

    private boolean sameNullableLong(Long left, Long right) {
        return left == null ? right == null : left.equals(right);
    }

    private <T> T firstNonNull(T preferred, T fallback) {
        return preferred != null ? preferred : fallback;
    }
}
