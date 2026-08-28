import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Backend is reached through a same-origin proxy (dev: Vite, prod: nginx),
// so the app can use relative /api and /media URLs - no CORS, no baked host.
const backend = process.env.VITE_BACKEND_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": backend,
      "/media": backend,
      "/health": backend,
    },
  },
  preview: { port: 4173 },
  build: {
    rollupOptions: {
      output: {
        // Split the charting library out of the app bundle so the initial
        // parse is smaller and vendor code caches independently.
        manualChunks: {
          charts: ["recharts"],
          react: ["react", "react-dom", "react-router-dom"],
        },
      },
    },
  },
});
