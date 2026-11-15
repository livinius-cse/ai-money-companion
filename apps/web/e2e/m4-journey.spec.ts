import { test, expect } from "@playwright/test";

test.describe("Milestone 4 — Publishing Document Engine & Quality Validation Real Browser E2E Journey", () => {
  test("Complete Milestone 4 Real Browser Document Generation Journey", async ({ page }) => {
    // -------------------------------------------------------------
    // Step 1: Open the application & Authenticate
    // -------------------------------------------------------------
    console.log("M4 Step 1: Authenticating...");
    await page.goto("/login");
    await expect(page).toHaveTitle(/AI Money Companion/i);

    const setupTab = page.getByRole("button", { name: "First-Run Setup" });
    if (await setupTab.isVisible()) {
      await setupTab.click();
      await page.fill('input[placeholder="Publisher Name"]', "M4 Test Publisher");
      await page.fill('input[type="email"]', "admin@e2e-publishing.com");
      await page.fill('input[type="password"]', "StrongPassword123!");
      await page.getByRole("button", { name: "Initialize Root Admin" }).click();
    }

    try {
      await page.waitForURL("/", { timeout: 3000 });
    } catch {
      const signInTab = page.getByRole("button", { name: "Sign In" });
      if (await signInTab.isVisible()) {
        await signInTab.click();
      }
      await page.fill('input[type="email"]', "admin@e2e-publishing.com");
      await page.fill('input[type="password"]', "StrongPassword123!");
      await page.getByRole("button", { name: "Secure Sign In" }).click();
      await page.waitForURL("/", { timeout: 15000 });
    }

    // -------------------------------------------------------------
    // Step 2: Create a test book for M4 document generation
    // -------------------------------------------------------------
    console.log("M4 Step 2: Creating new book...");
    await page.goto("/books/new");
    await page.fill('input[placeholder="e.g. The 30-Day Money Reset"]', "Wealth Blueprint 2026");
    await page.fill(
      'input[placeholder="e.g. A Practical Step-by-Step Budgeting and Debt Snowball Guide"]',
      "Architecting Passive Income and Financial Independence"
    );
    await page.fill(
      'textarea[placeholder="Describe what the book is about, the specific problems it solves, and the unique mechanism it teaches."]',
      "A complete tactical system for managing wealth, automated investments, and tax optimization."
    );
    await page.getByRole("button", { name: "Create Book & Open Studio" }).click();

    await page.waitForURL(/\/books\/[0-9a-f-]+$/, { timeout: 15000 });
    const bookUrl = page.url();
    const bookId = bookUrl.split("/").pop();
    expect(bookId).toBeTruthy();

    // -------------------------------------------------------------
    // Step 3: Add content chapters in Content Studio
    // -------------------------------------------------------------
    console.log("M4 Step 3: Adding chapter in Content Studio...");
    await page.goto(`/books/${bookId}/content`);
    await page.waitForLoadState("networkidle");

    // Add first chapter using the tested Add Chapter icon button
    await page.getByTitle("Add Chapter").click();
    await expect(page.getByText(/Chapter \d+: New Topic/)).toBeVisible({ timeout: 10000 });

    // Fill markdown content
    const sampleMarkdown =
      "# Foundations of Cash Flow Architecture\n\n" +
      "True financial security begins with understanding cash flow dynamics and system leverage.\n\n" +
      "## The Three Pillars of Wealth\n\n" +
      "1. **Deterministic Budgeting**: Directing every unit of income before it arrives.\n" +
      "2. **Systemic Investment**: Capital allocation into diversified index funds.\n" +
      "3. **Risk Mitigation**: Liquidity buffers matching 6 months of operating expenses.\n\n" +
      "> \"Discipline is the bridge between financial goals and real financial freedom.\"\n\n" +
      "Through disciplined compounding and low-cost execution, financial independence becomes an engineering problem rather than a matter of chance.";

    const contentEditor = page.locator("textarea").nth(0);
    await contentEditor.fill(sampleMarkdown);

    // Save chapter
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Saved", { exact: true })).toBeVisible({ timeout: 10000 });

    // Populate chapters to meet Amazon KDP 24-page minimum paperback requirement
    console.log("M4 Step 3b: Adding additional chapters to satisfy KDP 24-page paperback threshold...");
    const cookies = await page.context().cookies();
    const csrfCookie = cookies.find((c) => c.name === "csrf_token");
    for (let i = 2; i <= 24; i++) {
      await page.request.post(`http://127.0.0.1:8000/api/v1/books/${bookId}/chapters`, {
        data: {
          chapter_number: i,
          title: `System Execution Principle ${i}`,
          content: `Tactical breakdown and execution protocol for chapter ${i}. Maintaining operating liquidity buffers.`,
        },
        headers: {
          "X-CSRF-Token": csrfCookie?.value || "",
          "Origin": "http://127.0.0.1:3000",
        },
      });
    }

    // -------------------------------------------------------------
    // Step 4: Navigate to Interior Layout Studio
    // -------------------------------------------------------------
    console.log("M4 Step 4: Navigating to Interior Layout Studio...");
    await page.goto(`/books/${bookId}/layout`);
    await page.waitForLoadState("networkidle");

    // Verify page header and layout specs
    await expect(page.getByRole("heading", { name: /Interior Layout Studio & PDF Engine/i })).toBeVisible();
    await expect(page.getByText(/Amazon KDP Standard/i).first()).toBeVisible();
    await expect(page.getByText(/Even Parity Guaranteed/i).first()).toBeVisible();

    // -------------------------------------------------------------
    // Step 5: Compile Interior PDF
    // -------------------------------------------------------------
    console.log("M4 Step 5: Compiling Interior PDF...");
    const compileBtn = page.getByRole("button", { name: /Generate Interior PDF/i });
    await expect(compileBtn).toBeVisible();
    await compileBtn.click();

    // Wait for generation to finish and verify success notification
    await expect(page.getByText(/Interior PDF compiled successfully/i)).toBeVisible({ timeout: 25000 });

    // Verify document version card and even physical page count
    await expect(page.getByText(/Version 1/i).first()).toBeVisible();
    await expect(page.getByText(/Even Parity/i).first()).toBeVisible();

    // Verify PDF preview iframe is loaded
    const previewIframe = page.locator('iframe[title="Interior PDF Preview"]');
    await expect(previewIframe).toBeVisible();
    const iframeSrc = await previewIframe.getAttribute("src");
    expect(iframeSrc).toContain(`/api/v1/books/${bookId}/documents/`);
    expect(iframeSrc).toContain(`/preview`);

    // Verify Download button exists with valid download endpoint
    const downloadLink = page.getByRole("link", { name: /Download PDF/i });
    await expect(downloadLink).toBeVisible();
    const downloadHref = await downloadLink.getAttribute("href");
    expect(downloadHref).toContain(`/api/v1/books/${bookId}/documents/`);
    expect(downloadHref).toContain(`/download`);

    // Verify Quality findings panel
    await expect(page.getByText(/Pre-Flight Quality & Structural Validation/i)).toBeVisible();
    await expect(page.getByText(/Flesch Reading Ease/i)).toBeVisible();

    // -------------------------------------------------------------
    // Step 6: Navigate to Cover Design Studio
    // -------------------------------------------------------------
    console.log("M4 Step 6: Navigating to Cover Design Studio...");
    await page.goto(`/books/${bookId}/cover`);
    await page.waitForLoadState("networkidle");

    // Verify Cover Design Studio heading and mathematical specs
    await expect(page.getByRole("heading", { name: /Full-Jacket Cover Studio & Calculator/i })).toBeVisible();
    await expect(page.getByText(/Spine Thickness/i)).toBeVisible();
    await expect(page.getByText(/Full Cover Dimensions/i)).toBeVisible();
    await expect(page.getByText(/Full-Jacket Design Options/i)).toBeVisible();

    // Fill cover options
    await page.locator('input[type="text"]').first().fill("Wealth Blueprint 2026");
    await page.locator("textarea").first().fill("The definitive manual on money management and cash flow automation.");

    // Toggle guide lines checkbox
    const guideCheckbox = page.getByRole("checkbox").last();
    if (await guideCheckbox.isVisible()) {
      await guideCheckbox.check();
    }

    // -------------------------------------------------------------
    // Step 7: Generate Full-Jacket Cover PDF
    // -------------------------------------------------------------
    console.log("M4 Step 7: Generating Full-Jacket Cover PDF...");
    const generateCoverBtn = page.getByRole("button", { name: /Generate Full-Jacket Cover/i });
    await expect(generateCoverBtn).toBeVisible();
    await generateCoverBtn.click();

    // Wait for generation to finish and verify success notification
    await expect(page.getByText(/Cover PDF generated successfully/i)).toBeVisible({ timeout: 25000 });

    // Verify cover document version card
    await expect(page.getByText(/Version 1/i).first()).toBeVisible();

    // Verify Cover PDF preview iframe is loaded
    const coverIframe = page.locator('iframe[title="Full Jacket Cover Preview"]');
    await expect(coverIframe).toBeVisible();
    const coverIframeSrc = await coverIframe.getAttribute("src");
    expect(coverIframeSrc).toContain(`/api/v1/books/${bookId}/documents/`);
    expect(coverIframeSrc).toContain(`/preview`);

    // Verify Download Cover button exists
    const downloadCoverLink = page.getByRole("link", { name: /Download Cover/i });
    await expect(downloadCoverLink).toBeVisible();

    // -------------------------------------------------------------
    // Step 8: Persistence Verification across page reload
    // -------------------------------------------------------------
    console.log("M4 Step 8: Verifying document persistence across reload...");
    await page.reload();
    await page.waitForLoadState("networkidle");

    // Both documents must be persisted and visible
    await expect(page.getByText(/Version 1/i).first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('iframe[title="Full Jacket Cover Preview"]')).toBeVisible();

    // Navigate back to Layout page and verify persisted Interior document
    await page.goto(`/books/${bookId}/layout`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/Version 1/i).first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('iframe[title="Interior PDF Preview"]')).toBeVisible();

    console.log("✓ Milestone 4 Real Browser E2E Journey fully completed and verified!");
  });
});
