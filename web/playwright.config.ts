import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  use: {
    baseURL: "http://127.0.0.1:3001",
    trace: "retain-on-failure",
    launchOptions: {
      executablePath:
        process.env.CHROMIUM_PATH ||
        (existsSync("/usr/bin/chromium") ? "/usr/bin/chromium" : undefined),
      args: ["--no-sandbox"],
    },
  },
  webServer: [
    {
      command:
        "cd .. && ECHOLOOM_TEST_SERVER=1 .venv/bin/python tests/mvp/browser_server.py",
      url: "http://127.0.0.1:8001/api/health",
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command: "API_BASE_URL=http://127.0.0.1:8001 npm run dev -- --port 3001",
      url: "http://127.0.0.1:3001/characters",
      reuseExistingServer: false,
      timeout: 60000,
    },
  ],
});
