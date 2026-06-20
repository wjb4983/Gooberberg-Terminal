import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const VITE_HOST = process.env.GB_VITE_HOST;

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    host: VITE_HOST || undefined,
    port: 1420,
    strictPort: true,
  },
});
