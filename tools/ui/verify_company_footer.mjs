import { chromium } from '../../frontend/node_modules/@playwright/test/index.mjs';
const browser = await chromium.connectOverCDP('http://127.0.0.1:9225');
const context = browser.contexts()[0]; const page = await context.newPage();
try {
  await page.goto('http://127.0.0.1:43110/');
  await page.getByRole('heading', { name: 'AgentMonitor', exact: true }).waitFor({ timeout: 15000 });
  const link = page.locator('footer.dashboard-company-footer').getByRole('link', { name: 'Essential AI Solutions Ltd' });
  await link.waitFor({ timeout: 8000 });
  if (await link.getAttribute('href') !== 'https://essentialai.uk/' || await link.getAttribute('target') !== '_blank') throw new Error('company_footer_link_invalid');
  console.log('COMPANY FOOTER: PASSED — dashboard attribution and company link');
} finally { await page.close(); await browser.close(); }
