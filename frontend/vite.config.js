import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    // En Windows los eventos de archivos no cruzan al contenedor: polling
    watch: { usePolling: true },
    proxy: {
      // Solo para desarrollo local con `npm run dev` fuera de Docker
      "/api": process.env.API_URL || "http://localhost:8000",
    },
  },
});
