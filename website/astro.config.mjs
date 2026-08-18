import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://pedroltz.github.io/rdp-session-manager/",
  output: "static",
  vite: {
    server: {
      allowedHosts: [".ngrok-free.app"]
    }
  },
  build: {
    format: "directory"
  }
});
