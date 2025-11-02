import { defineConfig } from 'vite';

// https://vitejs.dev/config/
export default defineConfig({
  // Prevent vite from obscuring rust errors
  clearScreen: false,
  
  // Point to the source directory
  root: 'src',
  
  // Tauri expects a fixed port, fail if that port is not available
  server: {
    port: 1420,
    strictPort: true,
    watch: {
      // Tell vite to ignore watching `src-tauri`
      ignored: ['**/src-tauri/**'],
    },
  },
  
  // Env variables starting with VITE_ will be exposed to your frontend
  envPrefix: ['VITE_', 'TAURI_'],
  
  build: {
    // Output to dist in project root
    outDir: '../dist',
    emptyOutDir: true,
    // Tauri uses Chromium on Windows and WebKit on macOS and Linux
    target: process.env.TAURI_PLATFORM === 'windows' ? 'chrome105' : 'safari13',
    // Don't minify for debug builds
    minify: !process.env.TAURI_DEBUG ? 'esbuild' : false,
    // Produce sourcemaps for debug builds
    sourcemap: !!process.env.TAURI_DEBUG,
  },
});
