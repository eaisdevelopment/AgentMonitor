import { expect, test } from "@playwright/test";

test.use({ channel: "chrome" });

for (const viewport of [
  { width: 1920, height: 1080 },
  { width: 390, height: 844 },
]) {
  test(`loads the real foundation shell at ${viewport.width} px`, async ({
    page,
  }) => {
    const origin = process.env.AGENTMONITOR_TEST_ORIGIN;
    expect(origin).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
    await page.setViewportSize(viewport);

    const requestedUrls: string[] = [];
    const browserErrors: string[] = [];
    const failedResponses: number[] = [];
    page.on("request", (request) => requestedUrls.push(request.url()));
    page.on("response", (response) => {
      if (response.status() >= 400) {
        failedResponses.push(response.status());
      }
    });
    page.on("pageerror", (error) => browserErrors.push(error.name));
    page.on("console", (message) => {
      if (message.type() === "error") browserErrors.push("console_error");
    });

    const response = await page.goto(origin!);
    expect(response?.status()).toBe(200);
    expect(new URL(response!.url()).origin).toBe(origin);
    const schemaResponse = await page.request.get(`${origin}/openapi.json`);
    expect(schemaResponse.status()).toBe(200);
    const schema: { info: { version: string }; paths: Record<string, unknown> } =
      await schemaResponse.json();
    expect(schema.paths).toEqual({});

    const main = page.getByRole("main");
    await expect(main.getByRole("heading", { name: "AgentMonitor" })).toBeVisible();
    await expect(page.getByText(`API contract ${schema.info.version}`)).toBeVisible();
    await expect(main).toContainText(
      "Monitoring data will appear only after an approved provider integration",
    );
    await expect(main).not.toContainText(/quota|token usage|running agents/i);
    const text = (await main.innerText()).replace(
      `API contract ${schema.info.version}`,
      "",
    );
    expect(text).not.toMatch(/\b\d+(?:[.,]\d+)?\s*(?:%|credits?|tokens?|requests?)\b/i);

    expect(requestedUrls.length).toBeGreaterThan(1);
    for (const requested of requestedUrls) {
      const url = new URL(requested);
      expect(url.origin).toBe(origin);
      expect(url.pathname).not.toMatch(/^\/api\/v1(?:\/|$)/);
    }
    expect(failedResponses).toEqual([]);
    expect(browserErrors).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  });
}
