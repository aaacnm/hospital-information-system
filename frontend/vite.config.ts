import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import {fileURLToPath} from 'node:url';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {alias: {'@':fileURLToPath(new URL('./src',import.meta.url))}},
  test: {
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',
    globals: true,
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      // Keep the browser on the Vite origin during local development.
      // Production deployments can override VITE_API_BASE_URL and use nginx instead.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
