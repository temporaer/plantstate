import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/plants': 'http://localhost:8000',
      '/tasks': 'http://localhost:8000',
      '/dashboard': 'http://localhost:8000',
      '/sync': 'http://localhost:8000',
    },
  },
})
