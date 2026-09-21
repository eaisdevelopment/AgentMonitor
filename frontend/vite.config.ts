import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  envDir: false,
  build: {
    rollupOptions: {
      input: {
        foundation: "index.html",
        dashboard: "dashboard.html",
      },
    },
  },
});
