import { describe, expect, it } from 'vitest'

import { highlightTokens, rankSearchResults } from '../index.vue'

/** 按真实侧边栏的形状造一份候选集 */
const POOL = [
  { path: '/trade/orders', title: ['交易控制台', '订单管理'] },
  { path: '/trade/fills', title: ['交易控制台', '成交明细'] },
  { path: '/trade/positions', title: ['交易控制台', '持仓管理'] },
  { path: '/trade/position-guard', title: ['交易控制台', '持仓守护'] },
  { path: '/trade/notify-policy', title: ['交易控制台', '通知策略'] },
  { path: '/trade/notify-template', title: ['交易控制台', '通知模板'] },
  { path: '/data/market', title: ['数据与模型', '行情数据'] }
]

const paths = (rows) => rows.map((r) => r.path)

describe('rankSearchResults', () => {
  it('空输入时原样返回全部候选，不做任何过滤', () => {
    expect(rankSearchResults(POOL, '')).toEqual(POOL)
    expect(rankSearchResults(POOL, '   ')).toEqual(POOL)
  })

  it('中文标题子串直接命中 —— 这是改动前最容易搜不到的一类', () => {
    expect(paths(rankSearchResults(POOL, '持仓')))
      .toEqual(['/trade/positions', '/trade/position-guard'])
  })

  it('英文路径子串同样命中', () => {
    expect(paths(rankSearchResults(POOL, 'orders'))).toEqual(['/trade/orders'])
  })

  it('空格分隔的多个关键词按「全部命中」筛', () => {
    expect(paths(rankSearchResults(POOL, '通知 模板')))
      .toEqual(['/trade/notify-template'])
  })

  it('多关键词顺序无关', () => {
    expect(paths(rankSearchResults(POOL, '模板 通知')))
      .toEqual(['/trade/notify-template'])
  })

  it('模糊匹配的结果排在精确命中之后，且不重复', () => {
    const fuzzy = [
      { path: '/trade/positions', title: ['交易控制台', '持仓管理'] },
      { path: '/data/market', title: ['数据与模型', '行情数据'] }
    ]
    const got = paths(rankSearchResults(POOL, '持仓', fuzzy))
    expect(got).toEqual(['/trade/positions', '/trade/position-guard', '/data/market'])
  })

  it('大小写不敏感', () => {
    expect(paths(rankSearchResults(POOL, 'ORDERS'))).toEqual(['/trade/orders'])
  })

  it('没有任何命中时返回空数组，而不是整个候选集', () => {
    expect(rankSearchResults(POOL, '这个词不存在')).toEqual([])
  })

  it('title 缺失也不炸', () => {
    expect(paths(rankSearchResults([{ path: '/x/y' }], 'x'))).toEqual(['/x/y'])
  })
})

describe('highlightTokens', () => {
  it('按空白切词，忽略多余空格', () => {
    expect(highlightTokens('  通知   模板 ')).toEqual(['通知', '模板'])
  })

  it('空输入切出空数组', () => {
    expect(highlightTokens('')).toEqual([])
    expect(highlightTokens(null)).toEqual([])
  })
})
