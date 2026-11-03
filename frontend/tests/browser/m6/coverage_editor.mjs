import { chromium } from "@playwright/test";
let browser;
let page;
try {
  browser = await chromium.connectOverCDP("http://127.0.0.1:9225");
  const shared = browser.contexts().flatMap(context => context.pages()).find(item => item.url().startsWith("http://127.0.0.1:43110/"));
  if (!shared) throw new Error("shared_dashboard_required");
  page = await shared.context().newPage();
  await page.goto("http://127.0.0.1:43110/organizations");
  await page.getByRole("heading", { name: "Organization registry", exact: true }).waitFor();
  await page.locator(".record-card").first().waitFor();
  const editor = page.getByText("Provider coverage", { exact: true }).first();
  if (!await editor.count()) {
    console.log(JSON.stringify({status:"failed",reason:"organization_coverage_editor_missing"}));
    process.exitCode = 1;
  } else {
    await editor.click();
    await page.getByLabel("Coverage arrangement").first().waitFor();
    console.log(JSON.stringify({status:"passed",reason:null}));
  }
} catch {
  console.log(JSON.stringify({status:"blocked",reason:"signed_in_organization_page_required"}));
  process.exitCode = 3;
} finally {
  if (page) await page.close();
  if (browser) await browser.close();
}
