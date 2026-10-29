import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  use: { baseURL: "http://localhost:3100", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    {
      command:
        process.platform === "win32"
          ? "..\\backend\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --app-dir ../backend --port 8100"
          : "../backend/.venv/bin/python -m uvicorn app.main:app --app-dir ../backend --port 8100",
      url: "http://localhost:8100/health",
      env: {
        BEANY_LLM_MODE: "mock",
        BEANY_SEARCH_PROVIDER: "catalogue",
        BROWSER_USE_API_KEY: "",
        BROWSER_USE_REPLAY: "",
        OPENAI_API_KEY: "",
        BEANY_DB: "../backend/data/e2e.sqlite3",
        BEANY_RESEARCH_KEY: "e2e-key",
        FRONTEND_ORIGIN: "http://localhost:3100",
      },
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --port 3100",
      url: "http://localhost:3100",
      env: { NEXT_PUBLIC_API_URL: "http://localhost:8100", BEANY_E2E: "1" },
      reuseExistingServer: false,
      timeout: 120000,
    },
  ],
});
