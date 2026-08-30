import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react, { reactCompilerPreset } from "@vitejs/plugin-react";
import babel from "@rolldown/plugin-babel";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    babel({ presets: [reactCompilerPreset()] }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  build: {
    outDir: "../src/mybench/dashboard/static",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": process.env.MYBENCH_API_URL ?? "http://127.0.0.1:5199",
    },
  },
});
