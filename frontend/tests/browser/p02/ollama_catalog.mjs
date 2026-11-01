"use strict";

import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  const page = await browser.newPage();
  await page.goto(`${origin}/login`);
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor", exact: true }).waitFor();
  const catalog = page.getByRole("region", { name: "Ollama local models" });
  await catalog.waitFor({ state: "visible", timeout: 10000 });
  if (!await catalog.getByText("Installed models", { exact: true }).isVisible()) {
    throw new Error("ollama_installed_catalog_missing");
  }
  if (!await catalog.getByText("Loaded models", { exact: true }).isVisible()) {
    throw new Error("ollama_loaded_catalog_missing");
  }
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    if (!await catalog.isVisible()) throw new Error("ollama_catalog_hidden");
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) {
      throw new Error("ollama_catalog_horizontal_overflow");
    }
  }
  console.log("P02 OLLAMA CATALOG: PASSED");
} finally {
  await browser.close();
}
