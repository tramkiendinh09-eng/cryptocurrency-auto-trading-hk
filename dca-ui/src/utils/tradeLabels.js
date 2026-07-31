function normalizeLabelValue(value) {
  if (value == null) {
    return ''
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }
  return String(value).trim().toLowerCase()
}

const tradeLabelMaps = {
  runtimeMode: {
    paper: '模拟',
    shadow: '影子',
    live: '实盘'
  },
  promptScope: {
    supervisor: '监督者',
    market_agent: '市场专家',
    news_agent: '新闻专家',
    onchain_agent: '链上专家',
    social_agent: '社交专家',
    deliberation_referee: '复核裁判'
  },
  outputSchema: {
    supervisor_decision_v1: '监督者决策',
    agent_view_v1: '专家视图',
    deliberation_referee_v1: '复核裁决'
  },
  healthStatus: {
    unknown: '未知',
    healthy: '健康',
    degraded: '降级',
    unhealthy: '异常'
  },
  agentType: {
    rule: '规则',
    llm: '模型',
    hybrid: '混合'
  },
  accountRole: {
    execution: '执行',
    readonly: '只读',
    shadow: '影子'
  },
  marginMode: {
    cross: '全仓',
    isolated: '逐仓'
  },
  leverageMode: {
    manual: '手动',
    auto: '自动'
  },
  positionMode: {
    one_way: '单向持仓',
    hedge: '双向持仓'
  },
  action: {
    open_long: '开多',
    open_short: '开空',
    close_long: '平多',
    close_short: '平空',
    reduce_long: '减多',
    reduce_short: '减空',
    add_long: '加多',
    add_short: '加空',
    reduce: '减仓',
    close: '平仓',
    enter: '开仓',
    increase: '加仓',
    adjust: '调仓',
    hold: '观望',
    skip: '跳过',
    blocked: '拦截',
    no_action: '不操作'
  },
  orderSide: {
    buy: '买入',
    sell: '卖出',
    long: '多头',
    short: '空头',
    hold: '观望',
    open_long: '开多',
    open_short: '开空',
    close_long: '平多',
    close_short: '平空'
  },
  executionStatus: {
    filled: '已成交',
    submitted: '已提交',
    partial: '部分成交',
    pending: '待执行',
    failed: '执行失败',
    blocked: '已拦截',
    canceled: '已取消',
    expired: '已过期',
    skipped: '已跳过',
    success: '成功',
    unknown: '未知'
  },
  orderStatus: {
    filled: '已成交',
    pending: '待处理',
    partially_filled: '部分成交',
    canceled: '已取消',
    expired: '已过期',
    rejected: '已拒绝',
    blocked: '已拦截',
    skipped: '已跳过',
    new: '新建'
  },
  replayStatus: {
    queued: '排队中',
    running: '回放中',
    completed: '已完成',
    failed: '失败'
  },
  eventStrength: {
    strong: '强',
    normal: '正常',
    noise: '噪声'
  },
  eventType: {
    market_tick: '行情事件',
    news: '新闻事件',
    onchain: '链上事件',
    social: '社交事件',
    liquidation: '强平事件',
    announcement: '公告事件',
    decision: '决策结果',
    risk_guard_hit: '风控命中',
    execution: '执行结果',
    position: '持仓变更',
    runtime: '运行时事件',
    market_source_abnormal: '市场源异常',
    source_health: '源健康事件'
  },
  severity: {
    info: '提示',
    warn: '警告',
    error: '错误',
    critical: '严重'
  },
  policyScope: {
    global: '全局',
    strategy: '策略'
  },
  status: {
    true: '启用',
    false: '禁用',
    '1': '启用',
    '0': '禁用'
  },
  transportType: {
    rest: 'REST 接口',
    ws: 'WebSocket',
    websocket: 'WebSocket',
    poll: '轮询',
    hybrid: '混合'
  },
  promptSource: {
    inline: '内联',
    template: '模板',
    binding: '绑定模板',
    fallback: '回退模板'
  },
  sourceStatus: {
    healthy: '正常',
    degraded: '降级',
    stale: '数据过旧',
    unavailable: '不可用',
    unknown: '未知'
  },
  dataCategory: {
    price: '价格',
    volume: '成交量',
    kline: 'K 线',
    fear_greed: '恐慌贪婪',
    onchain: '链上',
    gas: 'Gas'
  }
}

export function formatTradeLabel(category, value) {
  const normalized = normalizeLabelValue(value)
  if (!normalized) {
    return ''
  }
  const label = tradeLabelMaps?.[category]?.[normalized]
  return label || String(value).trim()
}

export function formatTradeLabels(category, values) {
  return (Array.isArray(values) ? values : [])
    .map((item) => formatTradeLabel(category, item))
    .filter(Boolean)
}
