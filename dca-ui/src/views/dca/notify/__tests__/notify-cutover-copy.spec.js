import { describe, expect, it } from 'vitest'

import { notifyChannelCompatibilityMessage } from '../index.vue'

describe('notify channel cutover copy', () => {
  it('describes notify channels as active persistence with policy binding already available', () => {
    expect(notifyChannelCompatibilityMessage).toContain('notify_channel 持久化活动渠道定义')
    expect(notifyChannelCompatibilityMessage).toContain('通知策略')
    // 这句断言是这个测试的本意：文案不能再把策略绑定说成「将要」支持
    expect(notifyChannelCompatibilityMessage).not.toContain('将会')
  })
})
