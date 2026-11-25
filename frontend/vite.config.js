import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The app lives under /app/ so that short links like /aB3x9 can use the root path.
// In dev, /api calls are forwarded to the FastAPI server on port 8000.
export default defineConfig({
  base: "/app/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000" },
  },
});
