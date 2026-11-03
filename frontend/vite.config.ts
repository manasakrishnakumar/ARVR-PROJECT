import react from "@vitejs/plugin-react";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig } from "vitest/config";

// ARVR_HTTPS=1 serves the dev site over https with the self-signed certificate from scripts/make_dev_cert.ps1.
// Needed to use the camera from another device (a phone) on the local network: browsers only allow the camera on https.
const certDir = resolve(__dirname, "../certs");
const https = process.env.ARVR_HTTPS && existsSync(`${certDir}/dev.pem`)
  ? { cert: readFileSync(`${certDir}/dev.pem`), key: readFileSync(`${certDir}/dev-key.pem`) }
  : undefined;

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, https, proxy: { "/api": { target: "http://127.0.0.1:8000", ws: true } } },
  test: { environment: "jsdom", setupFiles: ["./src/test/setup.ts"], css: false },
});
