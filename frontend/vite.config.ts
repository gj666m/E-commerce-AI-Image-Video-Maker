import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // SSE 流式接口单独配置：剥掉 Accept-Encoding 避免 upstream gzip 缓冲，
      // 否则 vite proxy 会把整条 event-stream 攒到请求结束才一次性吐给浏览器
      '/api/agent': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('Accept-Encoding', 'identity')
            proxyReq.setHeader('Accept', 'text/event-stream')
          })
        },
      },
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
