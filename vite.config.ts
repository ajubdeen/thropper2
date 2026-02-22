import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "frontend", "src"),
      "@shared": path.resolve(__dirname, "shared"),
      "@assets": path.resolve(__dirname, "attached_assets"),
    },
  },
  root: path.resolve(__dirname, "frontend"),
  build: {
    outDir: path.resolve(__dirname, "static"),
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": "http://localhost:5000",
      "/portraits": "http://localhost:5000",
      "/login": "http://localhost:5000",
      "/auth": "http://localhost:5000",
      "/logout": "http://localhost:5000",
      "/socket.io": {
        target: "http://localhost:5000",
        ws: true,
      },
    },
  },
});
