import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  const page = await browser.newPage();
  await page.goto(`${process.argv[2]}/login`);
  await page.getByLabel("Administrator password").fill(readFileSync(0, "utf8"));
  await page.getByRole("button", { name: "Sign in" }).click();
  const support = page.locator(".dashboard-header").getByRole("link", { name: /Help to keep Agent Monitor Project Free!/ });
  await support.waitFor({ state: "visible", timeout: 10000 });
  const [checkout] = await Promise.all([page.waitForEvent("popup"), support.click()]);
  await checkout.waitForLoadState("domcontentloaded");
  await checkout.getByText("Donate to Agent Monitor").waitFor({ timeout: 20000 });
  await checkout.locator('input[placeholder="£0.00"]').waitFor({ timeout: 20000 });
  console.log("P02 SUPPORT CHECKOUT: PASSED");
} finally {
  await browser.close();
}
