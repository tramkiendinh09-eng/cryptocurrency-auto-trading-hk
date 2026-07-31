export const retiredMessage =
  '旧策略模板已退役，请改用运行时模型配置与交易策略版本。'

export const pageTitle = '策略模板入口已迁移'

export const pageDescription =
  '旧策略模板不再作为交易系统入口，请改用运行时模型配置、交易策略版本和控制面配置。'

export function createLegacyTemplateConsoleLinks() {
  return [
    { label: '交易策略', path: '/dca/trade/strategy' },
    { label: '运行模式', path: '/dca/trade/runtime' },
    { label: '账户绑定', path: '/dca/trade/account' }
  ]
}

export function createLegacyTemplateGuidance() {
  return [
    '模型与提示参数改由数据库配置维护，不再在旧模板页直接编辑。',
    '交易语义统一进入 trade_strategy / trade_strategy_version / trade_runtime_config。',
    '如需核对执行结果，请前往运行时总览、决策审计和历史回放页面。'
  ]
}
