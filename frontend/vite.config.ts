import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    sourcemap: false, // do not ship source maps to production
  },
  server: {
    // Local development only: forwards /api to a backend running on port 8000
    proxy: { '/api': 'http://localhost:8000' },
  },
});
