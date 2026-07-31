import { describe, expect, it } from 'vitest'

import { formatTradeLabel, formatTradeLabels } from '../tradeLabels'

describe('formatTradeLabel', () => {
  it('formats common runtime trade labels into Chinese display text', () => {
    expect(formatTradeLabel('runtimeMode', 'shadow')).toBe('影子')
    expect(formatTradeLabel('runtimeMode', 'live')).toBe('实盘')
    expect(formatTradeLabel('healthStatus', 'healthy')).toBe('健康')
    expect(formatTradeLabel('healthStatus', 'degraded')).toBe('降级')
    expect(formatTradeLabel('promptScope', 'SUPERVISOR')).toBe('监督者')
    expect(formatTradeLabel('promptScope', 'NEWS_AGENT')).toBe('新闻专家')
    expect(formatTradeLabel('outputSchema', 'agent_view_v1')).toBe('专家视图')
    expect(formatTradeLabel('agentType', 'HYBRID')).toBe('混合')
    expect(formatTradeLabel('accountRole', 'READONLY')).toBe('只读')
    expect(formatTradeLabel('marginMode', 'isolated')).toBe('逐仓')
    expect(formatTradeLabel('positionMode', 'one_way')).toBe('单向持仓')
    expect(formatTradeLabel('action', 'OPEN_LONG')).toBe('开多')
    expect(formatTradeLabel('orderSide', 'SELL')).toBe('卖出')
    expect(formatTradeLabel('executionStatus', 'blocked')).toBe('已拦截')
    expect(formatTradeLabel('orderStatus', 'PARTIALLY_FILLED')).toBe('部分成交')
    expect(formatTradeLabel('replayStatus', 'queued')).toBe('排队中')
    expect(formatTradeLabel('eventType', 'market_source_abnormal')).toBe('市场源异常')
    expect(formatTradeLabel('eventType', 'risk_guard_hit')).toBe('风控命中')
    expect(formatTradeLabel('severity', 'CRITICAL')).toBe('严重')
    expect(formatTradeLabel('promptSource', 'inline')).toBe('内联')
    expect(formatTradeLabel('sourceStatus', 'STALE')).toBe('数据过旧')
    expect(formatTradeLabel('policyScope', 'GLOBAL')).toBe('全局')
    expect(formatTradeLabel('status', true)).toBe('启用')
    expect(formatTradeLabel('status', false)).toBe('禁用')
  })

  it('falls back to original content for unknown values', () => {
    expect(formatTradeLabel('runtimeMode', 'custom')).toBe('custom')
    expect(formatTradeLabel('eventType', '')).toBe('')
    expect(formatTradeLabel('unknown', 'value')).toBe('value')
  })
})

describe('formatTradeLabels', () => {
  it('formats label arrays while removing empty items', () => {
    expect(formatTradeLabels('runtimeMode', ['shadow', '', 'live'])).toEqual(['影子', '实盘'])
    expect(formatTradeLabels('severity', ['WARN', 'CRITICAL'])).toEqual(['警告', '严重'])
    expect(formatTradeLabels('agentType', ['RULE', 'HYBRID'])).toEqual(['规则', '混合'])
    expect(formatTradeLabels('action', ['OPEN_LONG', 'HOLD'])).toEqual(['开多', '观望'])
  })
})
