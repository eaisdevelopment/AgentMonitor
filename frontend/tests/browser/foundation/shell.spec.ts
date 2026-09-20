import { expect, test } from "@playwright/test";

test.use({ channel: "chrome" });

test("loads the production shell without invented telemetry", async ({ page }) => {
  const origin = process.env.AGENTMONITOR_TEST_ORIGIN;
  expect(origin).toBeDefined();

  await page.goto(origin!);

  await expect(
    page.getByRole("heading", { name: "AgentMonitor" }),
  ).toBeVisible();
  await expect(
    page.getByText(/quota|token usage|running agents/i),
  ).toHaveCount(0);
});
