import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['substrate-icon.svg'],
      manifest: {
        name: 'Substrate AI - AI Companion',
        short_name: 'Substrate',
        description: 'Your AI companion',
        theme_color: '#121214',
        background_color: '#121214',
        display: 'standalone',
        icons: [
          {
            src: 'substrate-icon.svg',
            sizes: '512x512',
            type: 'image/svg+xml',
            purpose: 'any maskable'
          }
        ]
      }
    })
  ],
  optimizeDeps: {
    exclude: ['lucide-react'],
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/ollama': {
        target: 'http://localhost:11434',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/ollama/, ''),
      },
      '/localfs': {
        target: 'http://localhost:3009',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/localfs/, ''),
      },
      '/graphsync': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/graphsync/, ''),
      },
    },
  },
});