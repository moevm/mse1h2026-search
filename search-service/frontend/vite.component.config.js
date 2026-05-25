import { defineConfig } from 'vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    lib: {
      entry: fileURLToPath(new URL('./src/web-components/etu-search-input.js', import.meta.url)),
      name: 'EtuSearchInputBundle',
      formats: ['iife'],
      fileName: () => 'etu-search-input.js',
    },
  },
})
