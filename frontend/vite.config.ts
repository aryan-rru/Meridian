/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: "0.0.0.0",
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // jsdom + react-query renders can be starved when many test files run in
    // parallel on a loaded machine; the default 5s timeout then trips the first
    // async findBy in a file even though the logic is correct. Give it headroom.
    testTimeout: 20000,
    hookTimeout: 20000,
  },
});
