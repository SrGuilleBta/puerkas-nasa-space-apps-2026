import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    // En Windows los eventos de archivos no cruzan al contenedor: polling
    watch: { usePolling: true },
    // El navegador solo habla con este servidor; él reenvía la API y sus docs al backend
    proxy: {
      "/api": process.env.API_URL || "http://localhost:8000",
      "/docs": process.env.API_URL || "http://localhost:8000",
      "/openapi.json": process.env.API_URL || "http://localhost:8000",
    },
  },
});
