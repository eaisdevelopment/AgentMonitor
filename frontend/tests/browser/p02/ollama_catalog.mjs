"use strict";

import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
async function realModelNames(path) {
  const response = await fetch(`http://127.0.0.1:11434${path}`, {
    signal: AbortSignal.timeout(3000), redirect: "error",
  });
  if (!response.ok) throw new Error("ollama_source_unavailable");
  const reader = response.body?.getReader();
  if (!reader) throw new Error("ollama_source_invalid");
  let size = 0;
  const chunks = [];
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > 256 * 1024) {
      await reader.cancel();
      throw new Error("ollama_source_too_large");
    }
    chunks.push(value);
  }
  const payload = JSON.parse(new TextDecoder().decode(Buffer.concat(chunks)));
  if (!Array.isArray(payload.models)) throw new Error("ollama_source_invalid");
  const names = payload.models.map((model) => model.name);
  if (names.some((name) => typeof name !== "string")) {
    throw new Error("ollama_model_name_unavailable");
  }
  return names.sort();
}

const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  const installedBefore = await realModelNames("/api/tags");
  const loadedBefore = await realModelNames("/api/ps");
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
  const installed = catalog.getByRole("region", { name: "Installed models" });
  const loaded = catalog.getByRole("region", { name: "Loaded models" });
  if (installedBefore.length === 0 && !await installed.getByText("No installed models", { exact: true }).isVisible()) {
    throw new Error("ollama_empty_installed_state_missing");
  }
  if (loadedBefore.length === 0 && !await loaded.getByText("No loaded models", { exact: true }).isVisible()) {
    throw new Error("ollama_empty_loaded_state_missing");
  }
  for (const name of installedBefore) {
    if (!await installed.getByText(name, { exact: true }).isVisible()) {
      throw new Error("ollama_installed_model_not_displayed");
    }
  }
  for (const name of loadedBefore) {
    if (!await loaded.getByText(name, { exact: true }).isVisible()) {
      throw new Error("ollama_loaded_model_not_displayed");
    }
  }
  if (JSON.stringify(installedBefore) !== JSON.stringify(await realModelNames("/api/tags")) ||
      JSON.stringify(loadedBefore) !== JSON.stringify(await realModelNames("/api/ps"))) {
    throw new Error("ollama_model_state_changed_during_test");
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
