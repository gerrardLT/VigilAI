import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'
import { transform as sucraseTransform } from 'sucrase'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const sucrasePlugin = {
  name: 'sucrase-test-transform',
  enforce: 'pre',
  transform(code, id) {
    if (id.includes('/node_modules/')) {
      return null
    }

    if (!/\.(jsx?|tsx?)$/.test(id)) {
      return null
    }

    const transforms = []
    if (id.endsWith('.ts') || id.endsWith('.tsx')) {
      transforms.push('typescript')
    }
    if (id.endsWith('.jsx') || id.endsWith('.tsx')) {
      transforms.push('jsx')
    }

    if (transforms.length === 0) {
      return null
    }

    const result = sucraseTransform(code, {
      transforms,
      disableESTransforms: true,
      jsxRuntime: 'automatic',
      production: false,
      filePath: id,
    })

    return {
      code: result.code,
      map: result.sourceMap ?? null,
    }
  },
}

export default defineConfig({
  plugins: [sucrasePlugin],
  esbuild: false,
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    pool: 'forks',
    fileParallelism: false,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
