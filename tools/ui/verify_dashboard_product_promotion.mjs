/** Real authenticated-dashboard check for the requested product promotion. */
import { chromium } from '../../frontend/node_modules/@playwright/test/index.mjs';
const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT ?? 'http://127.0.0.1:9225';
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN ?? 'http://127.0.0.1:43110';
const browser = await chromium.connectOverCDP(endpoint);
const context = browser.contexts()[0];
if (!context) throw new Error('shared_dashboard_browser_required');
const page = await context.newPage();
try {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(origin, { waitUntil: 'domcontentloaded' });
  await page.getByRole('heading', { name: 'AgentMonitor', exact: true }).waitFor({ timeout: 15000 });
  const promotion = page.getByRole('region', { name: 'Discover the Essential AI product family' });
  await promotion.waitFor({ timeout: 10000 });
  const products = [
    ['Cogent', 'https://cogent.tools'], ['All2WIKI', 'https://all2wiki.com'],
    ['Clone Detector', 'https://clonedetector.com'], ['Marvin', 'https://marvinpda.com'],
    ['KLAIRE', 'https://klaire.pro'], ['Megaprompting', 'https://megaprompting.com'],
    ['Jev MCP', 'https://github.com'], ['Agent Skills', 'https://github.com'],
    ['MCP Multi-Edit', 'https://github.com'],
  ];
  for (const [name, expectedOrigin] of products) {
    const link = promotion.getByRole('link', { name: `Explore ${name}` });
    await link.waitFor({ timeout: 10000 });
    if (await link.getAttribute('target') !== '_blank') throw new Error('promotion_target_invalid');
    const rel = (await link.getAttribute('rel') ?? '').split(/\s+/);
    if (!rel.includes('noopener') || !rel.includes('noreferrer')) throw new Error('promotion_rel_invalid');
    const [tab] = await Promise.all([context.waitForEvent('page', { timeout: 15000 }), link.click()]);
    try { await tab.waitForURL(url => url.origin === expectedOrigin, { timeout: 15000 }); }
    finally { await tab.close(); }
    await promotion.getByRole('button', { name: 'Next product' }).click();
  }
  await page.setViewportSize({ width: 360, height: 800 });
  if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('promotion_mobile_overflow');
  console.log('DASHBOARD PRODUCT PROMOTION: PASSED — nine product tabs and mobile layout');
} finally { await page.close(); await browser.close(); }
