export function formatAiCallModel(row = {}) {
  const model = String(row?.model || '').trim()
  const modelCode = String(row?.modelCode || '').trim()
  const modelProvider = String(row?.modelProvider || '').trim()
  const primaryModel = model || modelCode
  if (primaryModel && modelProvider) {
    return `${primaryModel} / ${modelProvider}`
  }
  if (primaryModel) {
    return primaryModel
  }
  if (modelProvider) {
    return modelProvider
  }
  return '-'
}

export function normalizeAiCallRows(rows = []) {
  if (!Array.isArray(rows)) {
    return []
  }
  return rows.map((row) => {
    const displayModel = formatAiCallModel(row)
    return {
      ...row,
      model: displayModel === '-' ? row?.model || '' : displayModel,
      displayModel
    }
  })
}

export function buildAiCallModelOptions(rows = []) {
  const values = Array.from(
    new Set(
      normalizeAiCallRows(rows)
        .map((row) => String(row?.modelCode || row?.model || '').trim())
        .filter(Boolean)
    )
  ).sort((left, right) => left.localeCompare(right))
  return values.map((value) => ({
    label: value,
    value
  }))
}
