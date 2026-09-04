import request from "@/utils/request"

/**
 * 行情终端的 K 线。
 *
 * 走后端代理而不是浏览器直连交易所：用户所在网络未必能通，而且直连会把
 * 交易所的限流配额按客户端 IP 分散掉。后端有 10 秒缓存。
 */
export function listKlines(query) {
  return request({
    url: "/dca/market/klines",
    method: "get",
    params: query
  })
}

/** 自选列表的批量报价：一次请求覆盖全部标的，避免首屏十几个串行往返。 */
export function listTickers(query) {
  return request({
    url: "/dca/market/tickers",
    method: "get",
    params: query
  })
}
