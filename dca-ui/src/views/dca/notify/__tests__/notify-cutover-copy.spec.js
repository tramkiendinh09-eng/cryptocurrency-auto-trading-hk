import { describe, expect, it } from 'vitest'

import { notifyChannelCompatibilityMessage } from '../index.vue'

describe('notify channel cutover copy', () => {
  it('describes notify channels as active persistence with policy binding already available', () => {
    expect(notifyChannelCompatibilityMessage).toContain('notify_channel persists active channel definitions')
    expect(notifyChannelCompatibilityMessage).toContain('Notify Policy')
    expect(notifyChannelCompatibilityMessage).not.toContain('will attach')
  })
})
