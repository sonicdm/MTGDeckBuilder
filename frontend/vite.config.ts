import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
  },
  esbuild: {
    jsx: 'automatic',
  },
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': 'http://localhost:8000'
    },
    watch: {
      usePolling: true,
      interval: 200,
    },
    hmr: {
      protocol: 'ws',
      host: 'localhost',
      port: 5173,
    }
  }
})


