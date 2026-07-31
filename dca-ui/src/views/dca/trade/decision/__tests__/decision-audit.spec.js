import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import {
  buildDecisionQuery,
  buildReplayRiskSummary,
  buildTranscriptRows,
  buildLatestReplaySessionMap,
  eventStrengthTag,
  extractMarketSourceConfig,
  executionStatusTag,
  formatAgentMessagePreview,
  formatAction,
  formatMarketSourceSummary,
  formatMemorySummary,
  formatTradeMemoryOutcome,
  formatDecisionModel,
  formatExecutionStatus,
  formatEventStrength,
  formatMessageType,
  formatOrderStatus,
  formatPromptAuditSummary,
  parseAgentMessageContent,
  formatRuntimeMode,
  resolveEventStrength,
  resolveReplayActionLabel,
  tradeMemoryStatusTag
} from '../index.vue'

describe('executionStatusTag', () => {
  it('maps filled execution to success', () => {
    expect(executionStatusTag('filled')).toBe('success')
  })

  it('maps blocked and skipped execution states distinctly', () => {
    expect(executionStatusTag('blocked')).toBe('danger')
    expect(executionStatusTag('skipped')).toBe('info')
  })
})

describe('buildDecisionQuery', () => {
  it('keeps active execution filters and drops empty ones', () => {
    expect(buildDecisionQuery({ executionStatus: 'filled', orderStatus: '' })).toEqual({ executionStatus: 'filled' })
  })
})

describe('formatDecisionModel', () => {
  it('joins model code and provider for operator display', () => {
    expect(formatDecisionModel({ modelCode: 'gpt-4.1', modelProvider: 'openai' })).toBe('gpt-4.1 / openai')
  })

  it('falls back to a dash when model audit fields are missing', () => {
    expect(formatDecisionModel({})).toBe('-')
  })
})

describe('formatPromptAuditSummary', () => {
  it('joins resolved template, prompt source, and fallback marker for operator display', () => {
    expect(
      formatPromptAuditSummary({
        resolvedTemplateCode: 'trade.supervisor.v1',
        promptSource: 'template',
        promptTemplateFallbackUsed: true
      })
    ).toBe('trade.supervisor.v1 / 模板 / 回退')
  })

  it('falls back to binding template or dash when resolved prompt metadata is missing', () => {
    expect(
      formatPromptAuditSummary({
        bindingTemplateCode: 'trade.supervisor.v1',
        promptSource: 'inline'
      })
    ).toBe('trade.supervisor.v1 / 内联')
    expect(formatPromptAuditSummary({})).toBe('-')
  })

  it('labels supervisor decisions adopted from deliberation referee explicitly', () => {
    expect(
      formatPromptAuditSummary({
        resolvedTemplateCode: 'trade.supervisor.v1',
        promptSource: 'deliberation_referee'
      })
    ).toBe('trade.supervisor.v1 / 会审裁判采纳')
  })
})

describe('resolveEventStrength', () => {
  it('prefers top-level event strength when available', () => {
    expect(resolveEventStrength({ eventStrength: 'strong', featureSnapshot: { eventStrength: 'normal' } })).toBe('strong')
  })

  it('falls back to feature snapshot strength when the run is missing it', () => {
    expect(resolveEventStrength({ featureSnapshot: { eventStrength: 'normal' } })).toBe('normal')
  })
})

describe('eventStrengthTag', () => {
  it('maps event strength levels to operator-friendly tags', () => {
    expect(eventStrengthTag('strong')).toBe('danger')
    expect(eventStrengthTag('normal')).toBe('warning')
    expect(eventStrengthTag('noise')).toBe('info')
  })
})

describe('extractMarketSourceConfig', () => {
  it('prefers top-level market source config', () => {
    expect(
      extractMarketSourceConfig({
        marketSourceConfig: { vendorCode: 'BINANCE' },
        featureSnapshot: { snapshot: { marketSourceConfig: { vendorCode: 'OKX' } } }
      })
    ).toEqual({ vendorCode: 'BINANCE' })
  })

  it('falls back to nested feature snapshot market source config', () => {
    expect(
      extractMarketSourceConfig({
        featureSnapshot: { snapshot: { marketSourceConfig: { vendorCode: 'OKX' } } }
      })
    ).toEqual({ vendorCode: 'OKX' })
  })
})

describe('formatMarketSourceSummary', () => {
  it('labels source config update time to avoid implying market freshness', () => {
    expect(
      formatMarketSourceSummary({
        marketSourceConfig: {
          vendorCode: 'BINANCE',
          transportType: 'WEBSOCKET',
          updateTime: '2026-04-17 10:15:00'
        }
      })
    ).toBe('BINANCE / WebSocket / 配置更新: 2026-04-17 10:15:00')
  })

  it('supports legacy snake case payloads and empty fallback', () => {
    expect(
      formatMarketSourceSummary({
        marketSourceConfig: {
          vendor_code: 'OKX',
          transport_type: 'REST',
          updated_at: '2026-04-17 11:20:00'
        }
      })
    ).toBe('OKX / REST 接口 / 配置更新: 2026-04-17 11:20:00')
    expect(formatMarketSourceSummary({})).toBe('-')
  })
})

describe('buildLatestReplaySessionMap', () => {
  it('keeps the latest replay session for each source trace', () => {
    expect(
      buildLatestReplaySessionMap([
        { id: 3, sourceTraceId: 'trace-1', replayTraceId: 'replay-1a' },
        { id: 8, sourceTraceId: 'trace-1', replayTraceId: 'replay-1b' },
        { id: 5, sourceTraceId: 'trace-2', replayTraceId: 'replay-2a' }
      ])
    ).toEqual({
      'trace-1': { id: 8, sourceTraceId: 'trace-1', replayTraceId: 'replay-1b' },
      'trace-2': { id: 5, sourceTraceId: 'trace-2', replayTraceId: 'replay-2a' }
    })
  })

  it('drops sessions without a source trace id', () => {
    expect(buildLatestReplaySessionMap([{ id: 1 }, { id: 2, sourceTraceId: '' }])).toEqual({})
  })
})

describe('resolveReplayActionLabel', () => {
  it('returns replay trigger label when trace has not been replayed yet', () => {
    expect(resolveReplayActionLabel({ traceId: 'trace-1' }, {})).toBe('影子回放')
  })

  it('returns compare label when replay session already exists', () => {
    expect(resolveReplayActionLabel({ traceId: 'trace-1' }, { 'trace-1': { id: 8 } })).toBe('查看回放')
  })
})

describe('buildReplayRiskSummary', () => {
  it('summarizes replay risk hits for compare cards', () => {
    expect(
      buildReplayRiskSummary([
        { ruleCode: 'max_position_ratio', reason: 'too large' },
        { ruleCode: 'live_account_unhealthy', reason: 'account degraded' }
      ])
    ).toBe('2 次 / max_position_ratio / live_account_unhealthy')
  })

  it('falls back to a dash when no replay risk hits exist', () => {
    expect(buildReplayRiskSummary([])).toBe('-')
    expect(buildReplayRiskSummary()).toBe('-')
  })
})

describe('parseAgentMessageContent', () => {
  it('parses valid JSON content and falls back to an empty object on invalid payloads', () => {
    expect(parseAgentMessageContent('{"stance":"bullish"}')).toEqual({ stance: 'bullish' })
    expect(parseAgentMessageContent('{bad json}')).toEqual({})
  })
})

describe('formatAgentMessagePreview', () => {
  it('prefers summary text and otherwise falls back to important JSON keys', () => {
    expect(formatAgentMessagePreview({ summaryText: 'market opens bearish', contentJson: '{"stance":"bearish"}' })).toBe('market opens bearish')
    expect(formatAgentMessagePreview({ contentJson: '{"stance":"bearish"}' })).toBe('stance: bearish')
  })

  it('surfaces full agent conclusions when summary text is terse', () => {
    expect(
      formatAgentMessagePreview({
        summaryText: 'market opens bearish',
        contentJson: '{"bias":"bearish","confidence":87,"reason":"liquidation cascade","risk_note":"high_volatility"}'
      })
    ).toContain('liquidation cascade')
  })
})

describe('buildTranscriptRows', () => {
  it('builds transcript rows for deliberation display', () => {
    expect(
      buildTranscriptRows({
        agentMessages: [
          {
            roundNo: 0,
            speakerAgent: 'market_agent',
            targetAgent: 'news_agent',
            messageType: 'proposal',
            templateCode: 'trade.market.v1',
            modelCode: 'gpt-4.1',
            contentJson: '{"stance":"bearish"}',
            summaryText: 'market opens bearish'
          }
        ]
      })
    ).toEqual([
      {
        roundNo: 0,
        speakerAgent: 'market_agent',
        targetAgent: 'news_agent',
        messageType: 'proposal',
        templateCode: 'trade.market.v1',
        modelCode: 'gpt-4.1',
        contentJson: '{"stance":"bearish"}',
        summaryText: 'market opens bearish',
        contentPreview: 'market opens bearish'
      }
    ])
  })

  it('falls back to metadata embedded in content payloads when row fields are blank', () => {
    expect(
      buildTranscriptRows({
        agentMessages: [
          {
            roundNo: 0,
            speakerAgent: 'market_agent',
            targetAgent: 'supervisor_agent',
            messageType: 'conclusion',
            templateCode: '',
            modelCode: '',
            contentJson: '{"template_code":"trade.market.v2","model_code":"gpt-5.4","bias":"bullish","reason":"breakout confirmed"}',
            summaryText: ''
          }
        ]
      })
    ).toEqual([
      expect.objectContaining({
        templateCode: 'trade.market.v2',
        modelCode: 'gpt-5.4'
      })
    ])
  })
})

describe('display label helpers', () => {
  it('formats runtime values into Chinese display text', () => {
    expect(formatRuntimeMode('shadow')).toBe('影子')
    expect(formatEventStrength('strong')).toBe('强')
    expect(formatAction('OPEN_LONG')).toBe('开多')
    expect(formatAction('REDUCE')).toBe(formatAction('reduce'))
    expect(formatAction('adjust')).not.toBe('adjust')
    expect(formatExecutionStatus('blocked')).toBe('已拦截')
    expect(formatOrderStatus('PARTIALLY_FILLED')).toBe('部分成交')
    expect(formatMessageType('proposal')).toBe('提议')
    expect(formatMessageType('challenge')).toBe('质疑')
    expect(formatMessageType('revision')).toBe('修正')
    expect(formatMessageType('summary')).toBe('总结')
    expect(formatMessageType('referee_review')).toBe('复核')
    expect(formatMessageType('final_decision')).toBe('最终裁决')
  })
})


describe('formatMemorySummary', () => {
  it('shows short and long memory counts', () => {
    const row = {
      memoryUsage: {
        short_term_counts: { market: 3, news: 2, onchain: 1, social: 0, supervisor_decision: 1 },
        long_term_count: 2
      }
    }

    expect(formatMemorySummary(row)).toContain('?? 7')
    expect(formatMemorySummary(row)).toContain('?? 2')
  })

  it('handles missing memory payload', () => {
    expect(formatMemorySummary({})).toBe('-')
  })
})

describe('trade memory outcome helpers', () => {
  it('prefers learned lesson text over memory usage counters', () => {
    expect(
      formatTradeMemoryOutcome({
        tradeMemoryStatus: {
          status: 'stored',
          lesson_text: 'Wait for reclaim confirmation before closing the short.'
        },
        memoryUsage: {
          short_term_counts: { market: 3 },
          long_term_count: 0
        }
      })
    ).toBe('Wait for reclaim confirmation before closing the short.')
  })

  it('falls back to failure reason when no lesson was stored', () => {
    expect(
      formatTradeMemoryOutcome({
        tradeMemoryStatus: {
          status: 'failed',
          reason: 'memory_store_create_failed'
        }
      })
    ).toBe('failed / memory_store_create_failed')
    expect(tradeMemoryStatusTag('stored')).toBe('success')
    expect(tradeMemoryStatusTag('failed')).toBe('danger')
  })
})


describe('decision audit table summary overflow', () => {
  it('uses Element Plus overflow tooltip for summary reason cells', () => {
    const source = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../index.vue'), 'utf-8')

    expect(source).toMatch(/<el-table-column[^>]*prop="summaryReason"[^>]*show-overflow-tooltip/)
  })
})
