import { describe, expect, it } from 'vitest'

import { buildOrderQuery, executionStatusTag, orderStatusTag } from '../index.vue'

describe('orderStatusTag', () => {
  it('maps FILLED to success', () => {
    expect(orderStatusTag('FILLED')).toBe('success')
  })

  it('maps BLOCKED to danger', () => {
    expect(orderStatusTag('BLOCKED')).toBe('danger')
  })
})

describe('executionStatusTag', () => {
  it('maps filled to success', () => {
    expect(executionStatusTag('filled')).toBe('success')
  })

  it('maps failed to danger', () => {
    expect(executionStatusTag('failed')).toBe('danger')
  })

  it('maps blocked and skipped without collapsing to pending', () => {
    expect(executionStatusTag('blocked')).toBe('danger')
    expect(executionStatusTag('skipped')).toBe('info')
  })
})

describe('buildOrderQuery', () => {
  it('drops empty filters and keeps active status filters', () => {
    expect(buildOrderQuery({ status: 'filled', orderStatus: '' })).toEqual({ status: 'filled' })
  })
})
