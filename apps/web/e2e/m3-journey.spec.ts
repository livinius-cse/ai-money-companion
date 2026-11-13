import { test, expect } from "@playwright/test";

test.describe("Milestone 3 — Product Studio & Content Engine Real Browser E2E Journey", () => {
  // Valid 1x1 pixel PNG buffer
  const validPngBase64 =
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";
  const validPngBuffer = Buffer.from(validPngBase64, "base64");

  test("Complete 21-Step Real Browser User Journey", async ({ page }) => {
    // -------------------------------------------------------------
    // Step 1: Open the application
    // -------------------------------------------------------------
    console.log("Step 1: Opening application...");
    await page.goto("/login");
    await expect(page).toHaveTitle(/AI Money Companion/i);
    await expect(page.getByRole("heading", { name: "AI Money Companion" })).toBeVisible();

    // -------------------------------------------------------------
    // Step 2: Authenticate using existing authentication flow
    // -------------------------------------------------------------
    console.log("Step 2: Authenticating via First-Run Admin Setup...");
    const setupTab = page.getByRole("button", { name: "First-Run Setup" });
    if (await setupTab.isVisible()) {
      await setupTab.click();
      await page.fill('input[placeholder="Publisher Name"]', "Test Publisher");
      await page.fill('input[type="email"]', "admin@e2e-publishing.com");
      await page.fill('input[type="password"]', "StrongPassword123!");
      await page.getByRole("button", { name: "Initialize Root Admin" }).click();
    } else {
      await page.fill('input[type="email"]', "admin@e2e-publishing.com");
      await page.fill('input[type="password"]', "StrongPassword123!");
      await page.getByRole("button", { name: "Secure Sign In" }).click();
    }

    // Wait for redirect to dashboard
    await page.waitForURL("/", { timeout: 15000 });
    await expect(page.getByText(/Product Studio/i).first()).toBeVisible();

    // -------------------------------------------------------------
    // Step 3: Navigate to Book Portfolio
    // -------------------------------------------------------------
    console.log("Step 3: Navigating to Book Portfolio...");
    await page.goto("/books");
    await expect(page.getByRole("heading", { name: "Product Studio Portfolio" })).toBeVisible();

    // -------------------------------------------------------------
    // Step 4: Create a new book
    // -------------------------------------------------------------
    console.log("Step 4: Creating a new book concept...");
    await page.getByRole("button", { name: "Create New Book" }).click();
    await page.waitForURL("/books/new");

    await page.fill('input[placeholder="e.g. The 30-Day Money Reset"]', "Mastering Cash Flow Architecture");
    await page.fill('input[placeholder="e.g. A Practical Step-by-Step Budgeting and Debt Snowball Guide"]', "A Practical System for Wealth");
    await page.fill(
      'textarea[placeholder="Describe what the book is about, the specific problems it solves, and the unique mechanism it teaches."]',
      "Personal cash flow allocation and automated savings protocols."
    );

    // Submit new book form
    await page.getByRole("button", { name: "Create Book & Open Studio" }).click();

    // Navigates to Book Hub (/books/[id])
    await page.waitForURL(/\/books\/[0-9a-f-]+$/, { timeout: 15000 });
    const bookUrl = page.url();
    const bookId = bookUrl.split("/").pop();
    expect(bookId).toBeTruthy();
    await expect(page.getByRole("heading", { name: "Mastering Cash Flow Architecture" }).first()).toBeVisible();

    // -------------------------------------------------------------
    // Step 5: Edit and save its concept
    // -------------------------------------------------------------
    console.log("Step 5: Editing and saving book concept...");
    await page.getByRole("button", { name: "Book Concept" }).click();
    await page.waitForURL(`/books/${bookId}/concept`);

    const conceptTextarea = page.locator('textarea').first();
    await conceptTextarea.fill("Updated Premise: Algorithmic cash flow management eliminates human cognitive fatigue.");
    await page.getByRole("button", { name: "Save Changes" }).click();
    await expect(page.getByText("Saved successfully!")).toBeVisible({ timeout: 10000 });

    // -------------------------------------------------------------
    // Step 6: Generate a page plan using MockAIProvider
    // -------------------------------------------------------------
    console.log("Step 6: Generating page plan using AI Provider...");
    await page.getByRole("button", { name: "Page Planner" }).click();
    await page.waitForURL(`/books/${bookId}/planner`);

    await page.getByRole("button", { name: "Generate Plan with AI" }).click();
    // Wait for plan chapters to appear
    await expect(page.getByText("Total Planned Pages")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("AI Suggested Title & Subtitle Options")).toBeVisible();

    // -------------------------------------------------------------
    // Step 7: Apply and persist the plan
    // -------------------------------------------------------------
    console.log("Step 7: Applying and persisting page plan...");
    await page.getByRole("button", { name: "Save Plan to Studio" }).click();
    await expect(page.getByText("Plan successfully saved and applied to Product Studio!")).toBeVisible({ timeout: 10000 });

    // -------------------------------------------------------------
    // Step 8: Open Content Studio
    // -------------------------------------------------------------
    console.log("Step 8: Opening Content Studio...");
    await page.getByRole("button", { name: "Content Studio" }).click();
    await page.waitForURL(`/books/${bookId}/content`);
    await expect(page.getByText(/Chapters \(\d+\)/)).toBeVisible();

    // -------------------------------------------------------------
    // Step 9: Create a chapter
    // -------------------------------------------------------------
    console.log("Step 9: Adding a new chapter...");
    await page.getByTitle("Add Chapter").click();
    // Verify newly added chapter appears
    await expect(page.getByText(/Chapter \d+: New Topic/)).toBeVisible();

    // -------------------------------------------------------------
    // Step 10: Edit and save Markdown content
    // -------------------------------------------------------------
    console.log("Step 10: Editing and saving Markdown content...");
    const sampleMarkdown =
      "# The Systematic Reserve Ratio\n\n" +
      "Before allocating capital toward market risk, an author must establish a systematic reserve ratio. " +
      "Uncertainty is countered through liquidity and predictable execution.\n\n" +
      "## Operational Directives\n\n" +
      "- Maintain 90 days liquid cash reserves.\n" +
      "- Automate fixed percentage sweep rules.\n" +
      "- Eliminate high-interest recurring debt.";

    const contentEditor = page.locator("textarea").nth(0);
    await contentEditor.fill(sampleMarkdown);

    // Click Save button
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Saved", { exact: true })).toBeVisible({ timeout: 10000 });

    // -------------------------------------------------------------
    // Step 11: Verify the displayed word count and reading time
    // -------------------------------------------------------------
    console.log("Step 11: Verifying word count and reading time metrics...");
    // 47 words in sample markdown -> ~1 min reading time
    await expect(page.getByText(/words/)).toBeVisible();
    await expect(page.getByText(/~?\d+\s*min/)).toBeVisible();

    // -------------------------------------------------------------
    // Step 12: Generate an AI draft and verify it does NOT overwrite existing chapter content
    // -------------------------------------------------------------
    console.log("Step 12: Generating AI draft and verifying non-destructive safety...");
    await page.getByRole("button", { name: "AI Draft" }).click();
    await expect(page.getByRole("heading", { name: "Generate AI Chapter Draft" })).toBeVisible();

    // Generate draft inside modal
    await page.getByRole("button", { name: "Generate Draft" }).click();
    await expect(page.getByText("UNCONFIRMED DRAFT")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Generated Draft Preview")).toBeVisible();

    // Verify editor behind modal still holds the author's original text
    const editorValBefore = await contentEditor.inputValue();
    expect(editorValBefore).toContain("The Systematic Reserve Ratio");

    // -------------------------------------------------------------
    // Step 13: Accept and save reviewed chapter content
    // -------------------------------------------------------------
    console.log("Step 13: Reviewing, accepting, and saving draft...");
    await page.getByRole("button", { name: "Review & Insert into Editor" }).click();

    // Verify content inserted
    const editorValAfter = await contentEditor.inputValue();
    expect(editorValAfter.length).toBeGreaterThan(100);

    // Append author signoff notes
    await contentEditor.fill(editorValAfter + "\n\n## Publisher Verification\nManually audited by author.");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Saved", { exact: true })).toBeVisible({ timeout: 10000 });

    // -------------------------------------------------------------
    // Step 14: Navigate to Illustration Studio
    // -------------------------------------------------------------
    console.log("Step 14: Navigating to Illustration Studio...");
    await page.getByRole("button", { name: "Illustration Studio" }).click();
    await page.waitForURL(`/books/${bookId}/illustrations`);
    await expect(page.getByRole("heading", { name: "Illustration Studio & Asset Manager" })).toBeVisible();

    // -------------------------------------------------------------
    // Step 15: Generate illustration prompts
    // -------------------------------------------------------------
    console.log("Step 15: Generating AI illustration prompts...");
    await page.getByRole("button", { name: "Generate Prompts with AI" }).click();
    await expect(page.getByRole("heading", { name: "Generate Cohesive Visual Prompts" })).toBeVisible();

    await page.getByRole("button", { name: "Generate Prompts", exact: true }).click();
    await expect(page.getByText(/Generated Prompts \(\d+\)/)).toBeVisible({ timeout: 15000 });

    // Click "Add to Studio" on the first generated prompt
    await page.getByRole("button", { name: "Add to Studio" }).first().click();
    await page.getByRole("button", { name: "Done" }).click();

    // -------------------------------------------------------------
    // Step 16: Create a placeholder
    // -------------------------------------------------------------
    console.log("Step 16: Creating layout placeholder...");
    await page.getByRole("button", { name: "Add Placeholder" }).click();
    await expect(page.getByRole("heading", { name: "Add Visual Placeholder" })).toBeVisible();

    await page.fill(
      'textarea[placeholder="Describe the subject, visual composition, style, and contrast..."]',
      "Minimalist vector diagram of automated cash flow waterfall with high-contrast monochrome lines."
    );
    await page.getByRole("button", { name: "Add to Studio" }).click();

    // Verify placeholder card is displayed
    await expect(page.getByText("Reserved Layout Slot").first()).toBeVisible();

    // -------------------------------------------------------------
    // Step 17: Upload a valid test image
    // -------------------------------------------------------------
    console.log("Step 17: Uploading valid PNG asset...");
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Upload File" }).first().click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles({
      name: "cashflow_waterfall.png",
      mimeType: "image/png",
      buffer: validPngBuffer,
    });

    // -------------------------------------------------------------
    // Step 18: Verify image preview and asset persistence
    // -------------------------------------------------------------
    console.log("Step 18: Verifying image preview rendered via private streaming endpoint...");
    const previewImg = page.locator('img[src*="/asset"]').first();
    await expect(previewImg).toBeVisible({ timeout: 15000 });

    // -------------------------------------------------------------
    // Step 19: Change status to GENERATED
    // -------------------------------------------------------------
    console.log("Step 19: Verifying status transitioned to GENERATED...");
    await expect(page.locator("span", { hasText: "GENERATED" }).first()).toBeVisible();

    // -------------------------------------------------------------
    // Step 20: Explicitly confirm and transition to APPROVED_FINAL
    // -------------------------------------------------------------
    console.log("Step 20: Explicitly approving illustration for publication...");
    const statusSelect = page.locator("select").filter({ hasText: "APPROVED_FINAL" }).first();
    await statusSelect.selectOption("APPROVED_FINAL");

    // Modal pops up requiring human checkbox
    await expect(page.getByRole("heading", { name: "Confirm Final Human Approval" })).toBeVisible();
    await page.locator("#human-approval-check").check();
    await page.getByRole("button", { name: "Confirm & Sign Off" }).click();

    // Verify card badge transitions to APPROVED_FINAL
    await expect(page.locator("span", { hasText: "APPROVED_FINAL" }).first()).toBeVisible();

    // -------------------------------------------------------------
    // Step 21: Reload the page and verify persisted book, chapter and illustration data
    // -------------------------------------------------------------
    console.log("Step 21: Reloading browser and verifying full database persistence...");
    await page.reload();

    // Verify illustration persists after reload
    await expect(page.locator("span", { hasText: "APPROVED_FINAL" }).first()).toBeVisible();
    await expect(page.locator('img[src*="/asset"]').first()).toBeVisible();

    // Navigate to Content Studio and verify content persists
    await page.getByRole("button", { name: "Content Studio" }).click();
    await page.waitForURL(`/books/${bookId}/content`);
    const createdChapterItem = page.getByText(/Chapter \d+: New Topic/);
    await expect(createdChapterItem).toBeVisible();
    await createdChapterItem.click();
    await expect(page.locator("textarea").first()).toHaveValue(/Publisher Verification/);

    // Navigate to Book Overview Hub and verify metrics
    await page.getByRole("button", { name: "Overview" }).click();
    await page.waitForURL(`/books/${bookId}`);
    await expect(page.getByText("Manuscript").first()).toBeVisible();
    await expect(page.getByText("Illustrations").first()).toBeVisible();

    console.log("SUCCESS: All 21 real browser E2E journey steps passed cleanly!");
  });
});
