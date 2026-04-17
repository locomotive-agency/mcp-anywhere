import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/mcp-anywhere/',
  server: {
    allowedHosts: [
      '5775-2804-7f0-b77d-1daf-1184-f729-ffe6-79e9.ngrok-free.app',
    ],
  },
})