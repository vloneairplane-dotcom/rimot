import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  preview: {
    // Railway serves the app from a dynamic *.up.railway.app (or custom) domain,
    // so Vite's preview server needs to accept that Host header.
    allowedHosts: true,
  },
});
