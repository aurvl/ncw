import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Relative base so the built site works from any static host or sub-path.
export default defineConfig({
  base: './',
  plugins: [react()],
  // MapLibre 6 resolves its worker relative to its own module URL; pre-bundling breaks that path.
  optimizeDeps: { exclude: ['maplibre-gl'] },
})
