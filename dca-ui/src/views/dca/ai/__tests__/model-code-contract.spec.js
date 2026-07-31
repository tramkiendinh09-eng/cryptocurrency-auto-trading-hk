import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

function readView(relativePath) {
  return readFileSync(fileURLToPath(new URL(relativePath, import.meta.url)), 'utf8')
}

describe('ai model page modelCode contract', () => {
  it('exposes modelCode in the real ai model configuration page', () => {
    const indexSource = readView('../index.vue')

    expect(indexSource).toContain('prop="modelCode"')
    expect(indexSource).toContain('v-model="form.modelCode"')
  })
})
