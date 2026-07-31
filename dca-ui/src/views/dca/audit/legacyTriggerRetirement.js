export const retiredMessage = '旧DCA触发审计已退役，请使用运行时决策审计控制台。'

export const pageTitle = '运行时控制台入口'

export const pageDescription =
  '旧触发审计不再承载运行时交易链路，请改用新的决策审计、运行时总览与历史回放页面。'

export function createLegacyTriggerConsoleLinks() {
  return [
    { label: '运行时总览', path: '/dca/trade/runtime' },
    { label: '决策审计', path: '/dca/trade/decision' },
    { label: '历史回放', path: '/dca/trade/replay' }
  ]
}
