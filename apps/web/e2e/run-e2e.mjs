import { spawn, execSync } from "child_process";
import fs from "fs";
import path from "path";
import http from "http";

const projectRoot = path.resolve("../../");
const apiDir = path.resolve("../api");
const webDir = path.resolve(".");

const testDbPath = path.join(apiDir, "test_browser_e2e.db");
const testStorageDir = path.join(apiDir, "storage_test_browser_e2e");
const pythonExe = path.join(apiDir, ".venv", "Scripts", "python.exe");

async function waitHttp(url, timeoutMs = 30000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await new Promise((resolve, reject) => {
        const req = http.get(url, (res) => resolve(res.statusCode));
        req.on("error", reject);
        req.setTimeout(1000, () => req.destroy());
      });
      if (res >= 200 && res < 500) return true;
    } catch {}
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Timeout waiting for ${url}`);
}

function cleanupTestData() {
  console.log("Cleaning up temporary test database and storage...");
  try {
    if (fs.existsSync(testDbPath)) fs.unlinkSync(testDbPath);
  } catch (e) {
    console.warn("Could not delete test db:", e.message);
  }
  try {
    if (fs.existsSync(testStorageDir)) {
      fs.rmSync(testStorageDir, { recursive: true, force: true });
    }
  } catch (e) {
    console.warn("Could not delete test storage:", e.message);
  }
}

async function main() {
  console.log("=== Launching Milestone 3 Real Browser E2E Test Suite ===");
  cleanupTestData();

  // 1. Run Alembic migrations on isolated test DB
  console.log("1. Initializing isolated test database schema via Alembic...");
  const dbUrl = "sqlite:///./test_browser_e2e.db";
  execSync(`"${pythonExe}" -m alembic upgrade head`, {
    cwd: apiDir,
    env: {
      ...process.env,
      DATABASE_URL: dbUrl,
      STORAGE_DIR: "./storage_test_browser_e2e",
      SECRET_KEY: "qSxEGL3i6z1uHpkLXmBo6mLe6Z8Sa9rbJnfXVXCJrkTpqJm5",
      CSRF_SECRET_KEY: "GHhEnpM1E-GRhjRKCDa5gC9V23nhW6ZUrPO1mzZrkiGBBD0j",
      AI_PROVIDER: "mock",
    },
    stdio: "inherit",
  });

  // 2. Launch FastAPI backend
  console.log("2. Spawning backend server on 127.0.0.1:8000...");
  const backend = spawn(
    pythonExe,
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    {
      cwd: apiDir,
      env: {
        ...process.env,
        DATABASE_URL: dbUrl,
        STORAGE_DIR: "./storage_test_browser_e2e",
        SECRET_KEY: "qSxEGL3i6z1uHpkLXmBo6mLe6Z8Sa9rbJnfXVXCJrkTpqJm5",
        CSRF_SECRET_KEY: "GHhEnpM1E-GRhjRKCDa5gC9V23nhW6ZUrPO1mzZrkiGBBD0j",
        AI_PROVIDER: "mock",
      },
      stdio: "pipe",
    }
  );

  backend.stderr.on("data", (d) => process.stderr.write(`[api] ${d}`));
  backend.stdout.on("data", (d) => process.stdout.write(`[api] ${d}`));

  let frontend = null;
  let exitCode = 1;

  try {
    await waitHttp("http://127.0.0.1:8000/api/v1/health");
    console.log("✓ Backend is alive and ready at http://127.0.0.1:8000");

    // 3. Launch Next.js web application
    console.log("3. Spawning Next.js production server on 127.0.0.1:3000...");
    frontend = spawn(
      "pnpm.cmd",
      ["exec", "next", "start", "-p", "3000"],
      {
        cwd: webDir,
        env: {
          ...process.env,
          NODE_ENV: "production",
        },
        stdio: "pipe",
        shell: true,
      }
    );

    frontend.stderr.on("data", (d) => process.stderr.write(`[web] ${d}`));
    frontend.stdout.on("data", (d) => process.stdout.write(`[web] ${d}`));

    await waitHttp("http://127.0.0.1:3000");
    console.log("✓ Frontend is alive and ready at http://127.0.0.1:3000");

    // 4. Run Playwright real browser test
    console.log("4. Running Playwright browser test on Chromium...");
    const playwright = spawn(
      "pnpm.cmd",
      ["exec", "playwright", "test", "e2e/m3-journey.spec.ts"],
      {
        cwd: webDir,
        env: {
          ...process.env,
        },
        stdio: "inherit",
        shell: true,
      }
    );

    exitCode = await new Promise((resolve) => {
      playwright.on("exit", (code) => resolve(code ?? 1));
    });
  } catch (err) {
    console.error("E2E Test Execution Error:", err);
    exitCode = 1;
  } finally {
    console.log("Terminating servers...");
    if (backend && !backend.killed) {
      try {
        process.kill(backend.pid);
      } catch {}
      try {
        execSync(`taskkill /F /T /PID ${backend.pid}`);
      } catch {}
    }
    if (frontend && !frontend.killed) {
      try {
        process.kill(frontend.pid);
      } catch {}
      try {
        execSync(`taskkill /F /T /PID ${frontend.pid}`);
      } catch {}
    }
    cleanupTestData();
  }

  process.exit(exitCode);
}

main();
