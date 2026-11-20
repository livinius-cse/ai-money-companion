import { expect, test, type Page } from "@playwright/test";

type SyntheticReport = {
  reportType: "ORDERS" | "KENP_READ" | "PRIOR_MONTH_ROYALTIES";
  filename: string;
  headers: string[];
  row: string[];
  mappings: Array<[string, string]>;
};

async function importSyntheticReport(page: Page, report: SyntheticReport) {
  const csv = `${report.headers.join(",")}\n${report.row.join(",")}\n`;
  await page.getByLabel("Report type").selectOption(report.reportType);
  await page.getByLabel("Report provenance").selectOption("SIMULATED_DEMO");
  await page.locator('input[type="file"]').setInputFiles({
    name: report.filename,
    mimeType: "text/csv",
    buffer: Buffer.from(csv, "utf8"),
  });
  await page.getByRole("button", { name: "Detect report headers" }).click();
  await expect(page.getByRole("heading", { name: "Detected source headers" })).toBeVisible();
  await expect(page.getByText(/SHA-256 [a-f0-9]{64}/)).toBeVisible();

  for (const [fieldLabel, sourceHeader] of report.mappings) {
    await page.getByLabel(new RegExp(fieldLabel)).selectOption(sourceHeader);
  }

  await page.getByRole("button", { name: "Preview mapped records" }).click();
  await expect(page.getByRole("heading", { name: "Mapped record preview" })).toBeVisible();
  await expect(page.getByRole("cell", { name: report.row[2], exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Confirm import of 1 rows" }).click();
  await expect(page.getByRole("status")).toContainText(`Imported 1`);
  await expect(page.getByText(new RegExp(`${report.filename}.*VALID`))).toBeVisible();
}

test.describe("Milestone 5 and 6 browser release journey", () => {
  test("pre-flight, approval gate, exports, guided reports, analytics, and research", async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });
    page.on("pageerror", (error) => pageErrors.push(error.message));

    await page.goto("/login");
    await expect(page).toHaveTitle(/AI Money Companion/i);
    const signInTab = page.getByRole("button", { name: "Sign In", exact: true });
    await signInTab.click();
    await page.fill('input[type="email"]', "admin@e2e-publishing.com");
    await page.fill('input[type="password"]', "StrongPassword123!");
    await page.getByRole("button", { name: "Secure Sign In" }).click();
    await page.waitForURL("/", { timeout: 15000 });

    await page.goto("/books/new");
    await page.fill('input[placeholder="e.g. The 30-Day Money Reset"]', "M5 M6 Release QA Book");
    await page.fill(
      'input[placeholder="e.g. A Practical Step-by-Step Budgeting and Debt Snowball Guide"]',
      "A Synthetic Verification Workbook"
    );
    await page.fill(
      'textarea[placeholder="Describe what the book is about, the specific problems it solves, and the unique mechanism it teaches."]',
      "A synthetic isolated book used to verify release workflows."
    );
    await page.getByRole("button", { name: "Create Book & Open Studio" }).click();
    await page.waitForURL(/\/books\/[0-9a-f-]+$/, { timeout: 15000 });
    const bookId = new URL(page.url()).pathname.split("/").pop();
    expect(bookId).toBeTruthy();

    await page.goto(`/books/${bookId}/preflight`);
    await expect(page.getByRole("heading", { name: "Pre-Flight QA & Cryptographic Approval" })).toBeVisible();
    await expect(page.getByText("Readiness Gate")).toBeVisible();
    await page.route(`**/api/v1/books/${bookId}/preflight/run`, async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 250));
      await route.continue();
    });
    await page.getByRole("button", { name: "Re-Run QA Audit" }).click();
    await expect(page.getByRole("button", { name: "Auditing..." })).toBeVisible();
    await expect(page.getByText("Pre-flight QA re-audit completed successfully.")).toBeVisible({
      timeout: 15000,
    });
    await page.unroute(`**/api/v1/books/${bookId}/preflight/run`);
    await expect(page.getByRole("button", { name: "Sign Off & Approve Publication" })).toBeDisabled();

    await page.route(`**/api/v1/books/${bookId}/preflight/run`, (route) =>
      route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Synthetic pre-flight failure state." }),
      })
    );
    await page.getByRole("button", { name: "Re-Run QA Audit" }).click();
    await expect(page.getByText("Verification Alert")).toBeVisible();
    await page.unroute(`**/api/v1/books/${bookId}/preflight/run`);

    const exportListPath = `/api/v1/books/${bookId}/exports`;
    const exportListRoute = (url: URL) => url.pathname === exportListPath;
    await page.route(exportListRoute, async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 250));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0 }),
      });
    });
    await page.goto(`/books/${bookId}/export`);
    await expect(page.getByRole("heading", { name: "KDP package export" })).toBeVisible();
    await expect(page.getByText("Loading exports…")).toBeVisible();
    await expect(page.getByText("Export is blocked")).toBeVisible();
    await expect(page.getByText("No export packages have been generated.")).toBeVisible();
    await page.unroute(exportListRoute);
    await expect(page.getByRole("button", { name: "Generate KDP ZIP" })).toBeDisabled();
    const exportEligibilityRoute = `**/api/v1/books/${bookId}/exports/eligibility**`;
    await page.route(exportEligibilityRoute, (route) =>
      route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Synthetic export failure state." }),
      })
    );
    await page.getByRole("button", { name: "Refresh exports" }).click();
    await expect(page.locator("main [role='alert']")).toContainText("Synthetic export failure state.");
    await page.unroute(exportEligibilityRoute);

    await page.goto(`/books/${bookId}/sales-import`);
    await expect(page.getByRole("heading", { name: "Sales report imports" })).toBeVisible();
    await expect(page.getByText(/Exact downloaded-file header compatibility must be confirmed/)).toBeVisible();
    await expect(page.getByText("No reports imported for this report type and provenance.")).toBeVisible();

    await importSyntheticReport(page, {
      reportType: "ORDERS",
      filename: "synthetic-orders.csv",
      headers: [
        "Synthetic report date",
        "Synthetic marketplace",
        "Synthetic book title",
        "Synthetic paid units",
        "Synthetic free units",
      ],
      row: ["2025-01-03", "amazon.com", "M5 M6 Release QA Book", "12", "2"],
      mappings: [
        ["Reporting date or period", "Synthetic report date"],
        ["Marketplace", "Synthetic marketplace"],
        ["Book title", "Synthetic book title"],
        ["Paid units", "Synthetic paid units"],
        ["Free units", "Synthetic free units"],
      ],
    });

    await importSyntheticReport(page, {
      reportType: "KENP_READ",
      filename: "synthetic-kenp.csv",
      headers: [
        "Synthetic report date",
        "Synthetic marketplace",
        "Synthetic book title",
        "Synthetic KENP pages",
      ],
      row: ["2025-01-03", "amazon.com", "M5 M6 Release QA Book", "250"],
      mappings: [
        ["Reporting date or period", "Synthetic report date"],
        ["Marketplace", "Synthetic marketplace"],
        ["Book title", "Synthetic book title"],
        ["KENP pages read", "Synthetic KENP pages"],
      ],
    });

    await importSyntheticReport(page, {
      reportType: "PRIOR_MONTH_ROYALTIES",
      filename: "synthetic-royalties.csv",
      headers: [
        "Synthetic report period",
        "Synthetic marketplace",
        "Synthetic book title",
        "Synthetic royalty amount",
        "Synthetic currency",
      ],
      row: [
        "2025-01",
        "amazon.com",
        "M5 M6 Release QA Book",
        "12.5",
        "USD",
      ],
      mappings: [
        ["Reporting date or period", "Synthetic report period"],
        ["Marketplace", "Synthetic marketplace"],
        ["Book title", "Synthetic book title"],
        ["Reported royalty amount", "Synthetic royalty amount"],
        ["Currency", "Synthetic currency"],
      ],
    });

    await page.goto(`/books/${bookId}/analytics`);
    await expect(page.getByText("No Orders report data")).toBeVisible();
    await page.getByLabel("Provenance").selectOption("SIMULATED_DEMO");
    await expect(page.getByText("DEMO DATA — NOT REAL KDP EARNINGS")).toBeVisible();
    await expect(page.getByText("Paid units")).toBeVisible();
    await expect(page.getByText("12", { exact: true })).toBeVisible();

    await page.getByLabel("Report type").selectOption("KENP_READ");
    await expect(page.getByText("KENP pages read")).toBeVisible();
    await expect(page.getByText("250", { exact: true })).toBeVisible();

    await page.getByLabel("Report type").selectOption("PRIOR_MONTH_ROYALTIES");
    await expect(page.getByText("Reported royalties · kept separate by currency")).toBeVisible();
    await expect(page.getByText("USD", { exact: true })).toBeVisible();
    await expect(page.getByText("12.50", { exact: true })).toBeVisible();

    await page.goto(`/books/${bookId}/research-assistance`);
    await page.getByRole("button", { name: "Generate assistance" }).click();
    await expect(page.getByText("Verified persisted facts")).toBeVisible();
    await expect(page.getByText("External research not performed")).toBeVisible();

    await page.goto(`/books/${bookId}/business-recommendation`);
    await expect(page.getByRole("heading", { name: "No evidence-based recommendations yet" })).toBeVisible();
    const recommendationsRoute = `**/api/v1/books/${bookId}/business-recommendations**`;
    await page.route(recommendationsRoute, (route) =>
      route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Synthetic recommendation failure state." }),
      })
    );
    await page.reload();
    await expect(page.locator("main [role='alert']")).toContainText("Synthetic recommendation failure state.");
    await page.unroute(recommendationsRoute);

    expect(pageErrors).toEqual([]);
    expect(consoleErrors.filter((message) => !message.includes("503"))).toEqual([]);
  });
});
