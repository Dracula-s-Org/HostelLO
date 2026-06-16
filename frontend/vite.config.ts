import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The FastAPI backend serves the built bundle from `frontend/dist` and exposes
// hashed assets under `/assets` (see app/spa.py). In dev, Vite proxies API +
// upload traffic to uvicorn so the browser sees a single same-origin app and
// the auth cookie flows without CORS.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    // CSP is `script-src 'self'` (app/main.py) — no inline scripts allowed.
    // Drop Vite's inline module-preload polyfill so index.html stays clean.
    modulePreload: { polyfill: false },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/static": "http://localhost:8000",
    },
  },
});
