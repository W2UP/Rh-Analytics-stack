import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  cacheDir: '.cache/vite',
  server: { proxy: { '/api': process.env.RH_API_TARGET || 'http://127.0.0.1:8000' } },
  preview: { proxy: { '/api': process.env.RH_API_TARGET || 'http://127.0.0.1:8000' } },
  plugins: [
    tailwindcss(),
    react(),
  ],
})