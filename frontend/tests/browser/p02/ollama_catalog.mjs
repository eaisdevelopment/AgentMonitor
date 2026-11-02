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
  let catalogRequests = 0;
  page.on("request", request => {
    if (request.url() === `${origin}/api/v1/providers/ollama/local-catalog` &&
        request.method() === "GET") catalogRequests += 1;
  });
  await page.goto(`${origin}/login`);
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor", exact: true }).waitFor();
  const catalog = page.getByRole("region", { name: "Ollama local models" });
  await catalog.waitFor({ state: "visible", timeout: 10000 });
  await catalog.getByText("Installed models", { exact: true }).waitFor({ state: "visible" });
  await catalog.getByText("Loaded models", { exact: true }).waitFor({ state: "visible" });
  if (catalogRequests !== 1) throw new Error("ollama_initial_request_duplicated");
  const installed = catalog.getByRole("region", { name: "Installed models" });
  const loaded = catalog.getByRole("region", { name: "Loaded models" });
  if (!await catalog.getByText(/Service version 0\.24\.0/).isVisible() ||
      !await installed.getByText(/^Read .* · current$/).isVisible() ||
      !await loaded.getByText(/^Read .* · current$/).isVisible()) {
    if (await catalog.getByText("Another Ollama reading is in progress. Try again shortly.").isVisible()) {
      throw new Error("ollama_initial_read_busy");
    }
    throw new Error("ollama_reading_provenance_missing");
  }
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
  const refreshed = await page.waitForResponse(response =>
    response.url() === `${origin}/api/v1/providers/ollama/local-catalog` &&
    response.request().method() === "GET" && response.status() === 200,
  { timeout: 40_000 });
  if (!refreshed.ok()) throw new Error("ollama_auto_refresh_failed");
  await installed.getByText(/^Read .* · current$/).waitFor({ state: "visible" });
  let processPayload;
  const processDeadline = Date.now() + 15_000;
  while (Date.now() < processDeadline) {
    const response = await page.request.get(
      `${origin}/api/v1/process-metrics?provider_key=ollama&limit=200`,
      { headers: { Origin: origin } },
    );
    if (!response.ok()) throw new Error(`ollama_process_api_unavailable_${response.status()}`);
    processPayload = await response.json();
    if (processPayload.items?.length > 0) break;
    await page.waitForTimeout(100);
  }
  if (!processPayload?.items?.length ||
      processPayload.items.some((item) => item.provider_key !== "ollama" ||
        item.provenance?.source_id !== "linux.proc.process.v1" ||
        "account_id" in item || "model_id" in item)) {
    throw new Error("ollama_process_api_invalid");
  }
  await page.getByRole("button", { name: "Sessions", exact: true }).click();
  const processTable = page.getByRole("region", { name: "Process observations table" });
  await processTable.waitFor({ state: "visible", timeout: 15_000 });
  const processRows = processTable.locator('tbody tr[data-process-row="true"]');
  const ollamaRows = processRows.filter({ has: page.getByRole("rowheader", { name: "ollama", exact: true }) });
  if (await ollamaRows.count() < 1 ||
      !await ollamaRows.first().getByText("linux.proc.process.v1", { exact: true }).isVisible()) {
    throw new Error("ollama_process_row_missing");
  }
  console.log("P02 OLLAMA CATALOG: PASSED");
} finally {
  await browser.close();
}
