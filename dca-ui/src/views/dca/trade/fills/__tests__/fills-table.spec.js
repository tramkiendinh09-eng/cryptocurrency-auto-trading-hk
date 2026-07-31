import { describe, expect, it } from 'vitest'

import { extractFillRows } from '../index.vue'

describe('extractFillRows', () => {
  it('prefers data arrays and falls back to rows arrays', () => {
    expect(extractFillRows({ data: [{ orderRef: 'ord-1' }] })).toEqual([{ orderRef: 'ord-1' }])
    expect(extractFillRows({ rows: [{ orderRef: 'ord-2' }] })).toEqual([{ orderRef: 'ord-2' }])
    expect(extractFillRows({})).toEqual([])
  })
})
