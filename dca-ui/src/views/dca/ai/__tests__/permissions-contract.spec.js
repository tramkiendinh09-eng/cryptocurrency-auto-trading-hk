import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

function readView(relativePath) {
  return readFileSync(fileURLToPath(new URL(relativePath, import.meta.url)), 'utf8')
}

describe('ai page permission contract', () => {
  it('aligns ai page action permissions with backend aiModel authorities', () => {
    const indexSource = readView('../index.vue')
    const modelSource = readView('../model.vue')

    expect(indexSource).toContain("v-hasPermi=\"['dca:aiModel:add']\"")
    expect(indexSource).toContain("v-hasPermi=\"['dca:aiModel:edit']\"")
    expect(indexSource).toContain("v-hasPermi=\"['dca:aiModel:remove']\"")
    expect(indexSource).not.toContain("v-hasPermi=\"['dca:ai:add']\"")

    expect(modelSource).toContain("v-hasPermi=\"['dca:aiModel:add']\"")
    expect(modelSource).toContain("v-hasPermi=\"['dca:aiModel:edit']\"")
    expect(modelSource).toContain("v-hasPermi=\"['dca:aiModel:remove']\"")
    expect(modelSource).not.toContain("v-hasPermi=\"['dca:ai:add']\"")
  })
})
