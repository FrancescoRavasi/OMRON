require('dotenv').config();
const { chromium } = require('playwright');

// Helper to inject log container
async function setupUILog(page) {
  await page.evaluate(() => {
    if (document.getElementById('automation-log')) return;
    const div = document.createElement('div');
    div.id = 'automation-log';
    div.style.position = 'fixed';
    div.style.top = '10px';
    div.style.right = '10px';
    div.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
    div.style.color = '#fff';
    div.style.padding = '10px';
    div.style.zIndex = '999999';
    div.style.borderRadius = '5px';
    div.style.fontSize = '12px';
    div.style.maxWidth = '300px';
    div.innerHTML = '<strong>Automation Log:</strong>';
    document.body.appendChild(div);
  });
}

// Helper to update log container
async function updateUILog(page, message) {
  console.log(message); // Still log to console for debugging
  await page.evaluate((msg) => {
    const log = document.getElementById('automation-log');
    if (log) {
      const entry = document.createElement('div');
      entry.innerText = `> ${msg}`;
      log.appendChild(entry);
    }
  }, message);
}

async function login() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto('https://industrial.omron.it/it/login');
    await setupUILog(page); // Inject after initial load
    
    await updateUILog(page, 'Navigating to login page...');

    await page.fill('input[name="email"]', process.env.OMRON_USERNAME);
    await page.fill('input[name="password"]', process.env.OMRON_PASSWORD);

    await updateUILog(page, 'Logging in...');
    await page.click('button[type="submit"]');

    await page.waitForNavigation();
    
    // Re-inject on new page
    await setupUILog(page); 
    await updateUILog(page, 'Login successful!');

  } catch (error) {
    console.error('Login failed:', error);
  } finally {
    // Keep browser open for inspection
  }
}

login();
