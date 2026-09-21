"use strict";

import { chromium } from "@playwright/test";

const origin = process.argv[2];
let browser;
let stage = "browser_launch";
try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ baseURL: origin });
  stage = "uninitialized_install";
  const entry = await page.goto(`${origin}/login`);
  if (entry?.status() !== 200) throw new Error("local_login_entry_missing");
  await page.getByRole("heading", { name: "Administrator setup required" }).waitFor();
  await page.getByText("docs/modules/identity-access.md").waitFor();
  if (await page.getByLabel("Administrator password").count()) throw new Error("web_setup_credential_field_present");
  await browser.close();
  console.log("P02 SETUP BROWSER: PASSED");
} catch {
  if (browser) await browser.close();
  console.error(`P02 SETUP BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
}
