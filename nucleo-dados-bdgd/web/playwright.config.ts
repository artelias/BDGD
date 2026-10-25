import { defineConfig, devices } from "@playwright/test";

// PW_BASE_URL aponta para um servidor já ativo (ex.: dev local); sem ele, testa o build estático exportado.
const external = process.env.PW_BASE_URL;
// Em Actions usa Chrome pré-instalado no ubuntu-latest, sem downloads de Chromium.
const chromeDoRunner = process.env.CI ? { channel: "chrome" as const } : {};
export default defineConfig({
  testDir: "e2e",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: { baseURL: external ?? "http://localhost:3211", locale: "pt-BR", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], ...chromeDoRunner, viewport: { width: 1440, height: 900 } }, grepInvert: /@mobile/ },
    { name: "mobile", use: { ...devices["Pixel 7"], ...chromeDoRunner }, grep: /@mobile/ },
  ],
  webServer: external ? undefined : { command: "npx serve@14.2.4 out -l 3211 --no-clipboard", port: 3211, reuseExistingServer: true, timeout: 120_000 },
});
