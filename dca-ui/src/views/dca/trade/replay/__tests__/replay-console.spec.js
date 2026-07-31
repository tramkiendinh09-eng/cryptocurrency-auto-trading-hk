import { describe, expect, it } from 'vitest'

import {
  extractReplaySessionRows,
  formatAction,
  formatDecisionModel,
  formatEventType,
  formatExecutionStatus,
  formatOrderStatus,
  formatReplayStatus,
  formatRuntimeMode,
  replayStatusTag
} from '../index.vue'

describe('extractReplaySessionRows', () => {
  it('prefers data arrays and falls back to rows arrays', () => {
    expect(extractReplaySessionRows({ data: [{ id: 8, status: 'completed' }] })).toEqual([{ id: 8, status: 'completed' }])
    expect(extractReplaySessionRows({ rows: [{ id: 9, status: 'queued' }] })).toEqual([{ id: 9, status: 'queued' }])
    expect(extractReplaySessionRows({})).toEqual([])
  })
})

describe('replayStatusTag', () => {
  it('maps running and completed statuses to operator-friendly tags', () => {
    expect(replayStatusTag('running')).toBe('warning')
    expect(replayStatusTag('completed')).toBe('success')
  })

  it('maps failed status to danger and defaults queued to info', () => {
    expect(replayStatusTag('failed')).toBe('danger')
    expect(replayStatusTag('queued')).toBe('info')
  })
})

describe('formatDecisionModel', () => {
  it('formats replay decision model metadata when present', () => {
    expect(formatDecisionModel({ modelCode: 'gpt-4.1', modelProvider: 'openai' })).toBe('gpt-4.1 / openai')
  })

  it('returns a dash when replay decision model metadata is missing', () => {
    expect(formatDecisionModel(null)).toBe('-')
  })
})

describe('display label helpers', () => {
  it('formats replay-related values into Chinese display text', () => {
    expect(formatReplayStatus('queued')).toBe('排队中')
    expect(formatRuntimeMode('paper')).toBe('模拟')
    expect(formatAction('OPEN_SHORT')).toBe('开空')
    expect(formatExecutionStatus('failed')).toBe('执行失败')
    expect(formatOrderStatus('BLOCKED')).toBe('已拦截')
    expect(formatEventType('source_health')).toBe('源健康事件')
  })
})
