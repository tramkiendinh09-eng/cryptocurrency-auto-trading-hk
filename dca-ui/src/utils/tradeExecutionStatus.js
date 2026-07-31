export function executionStatusTag(status) {
  if (status === 'filled') {
    return 'success'
  }
  if (status === 'submitted' || status === 'partial' || status === 'pending') {
    return 'warning'
  }
  if (status === 'failed' || status === 'blocked') {
    return 'danger'
  }
  if (status === 'canceled' || status === 'expired' || status === 'skipped') {
    return 'info'
  }
  return 'info'
}

export function orderStatusTag(status) {
  if (status === 'FILLED') {
    return 'success'
  }
  if (status === 'REJECTED' || status === 'BLOCKED') {
    return 'danger'
  }
  if (status === 'SKIPPED') {
    return 'info'
  }
  return 'info'
}
