import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const API_URL = process.env.VITE_API_URL || 'http://localhost:5000'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: API_URL,
        changeOrigin: true,
      },
      '/socket.io': {
        target: API_URL,
        changeOrigin: true,
        ws: true,
      }
    }
  },
  preview: {
    host: '0.0.0.0',
    port: 3000,
  }
})
