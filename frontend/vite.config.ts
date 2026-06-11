import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/video-files': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/model-files': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('element-plus') || id.includes('@element-plus/icons-vue')) {
            return 'element-plus'
          }
        },
      },
    },
  },
})
