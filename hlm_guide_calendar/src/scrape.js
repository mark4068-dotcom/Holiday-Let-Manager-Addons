import { chromium } from "playwright-core";
import { parseDisplayedDate } from "./dates.js";
import { stableUid } from "./calendar.js";
import { favouriteFromText } from "./favourites.js";
import { titlesMatch } from "./titles.js";

const CHROMIUM_PATHS = ["/usr/bin/chromium-browser", "/usr/bin/chromium"];

async function findChromium() {
  const { access } = await import("node:fs/promises");
  for (const path of [process.env.CHROMIUM_PATH, ...CHROMIUM_PATHS].filter(Boolean)) {
    try { await access(path); return path; } catch { /* try next */ }
  }
  throw new Error("Chromium executable was not found");
}

const tidy = (value) => String(value || "").replace(/\s+/g, " ").trim();

async function gotoWithRetry(page, url) {
  let lastError;
  for (let attempt = 1; attempt <= 4; attempt += 1) {
    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60_000 });
      return;
    } catch (error) {
      lastError = error;
      if (attempt === 4) break;
      const delay = attempt * 3_000;
      console.warn(`Page load attempt ${attempt} failed; retrying in ${delay / 1_000}s: ${error.message}`);
      await page.waitForTimeout(delay);
    }
  }
  throw lastError;
}

async function expandShowMore(page) {
  const controls = page.getByText(/show more/i);
  for (let index = 0; index < await controls.count(); index += 1) {
    const control = controls.nth(index);
    if (await control.isVisible().catch(() => false)) await control.click().catch(() => undefined);
  }
}

async function discoverCards(page, startLabel, endLabel) {
  return page.evaluate(({ startLabel, endLabel }) => {
    const visible = (element) => {
      const style = window.getComputedStyle(element);
      const box = element.getBoundingClientRect();
      return style.visibility !== "hidden" && style.display !== "none" && box.width > 1 && box.height > 1;
    };
    const nodes = [...document.querySelectorAll("body *")];
    document.querySelectorAll("[data-guide-scrape-token]").forEach((node) => node.removeAttribute("data-guide-scrape-token"));
    const exactVisible = (label) => nodes.filter((el) => visible(el) && el.textContent?.trim() === label);
    const startElement = exactVisible(startLabel).sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top)[0];
    if (!startElement) return [];
    const startY = startElement.getBoundingClientRect().bottom;
    const endElement = exactVisible(endLabel)
      .filter((el) => el.getBoundingClientRect().top > startY)
      .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top)[0];
    const endY = endElement ? endElement.getBoundingClientRect().top : Number.POSITIVE_INFINITY;
    const seen = new Set();
    const results = [];
    for (const element of nodes) {
      if (!visible(element) || element.children.length) continue;
      const box = element.getBoundingClientRect();
      if (box.top < startY || box.top >= endY) continue;
      const label = element.textContent?.replace(/\s+/g, " ").trim();
      if (!label || label.length < 4 || label.length > 100 || seen.has(label)) continue;
      if (/^(search by date|show more|home|explore|property|about)$/i.test(label)) continue;
      let clickable = element;
      while (clickable && clickable !== document.body) {
        const style = window.getComputedStyle(clickable);
        if (clickable.matches("button,a,[role=button]") || style.cursor === "pointer") break;
        clickable = clickable.parentElement;
      }
      if (!clickable || clickable === document.body) continue;
      const token = `guide-card-${results.length}`;
      clickable.setAttribute("data-guide-scrape-token", token);
      seen.add(label);
      results.push({ token, label });
    }
    return results;
  }, { startLabel, endLabel });
}

function eventFromText(lines, sourceUrl) {
  const dateLine = lines.find((line) => parseDisplayedDate(line));
  const dates = dateLine ? parseDisplayedDate(dateLine) : null;
  if (!dates) return null;
  const dateIndex = lines.indexOf(dateLine);
  const isGeneric = (line) => /^(open|closed|show more|other events|home|explore|property|about|local events(?:\s*&\s*favourite places)?|what(?:'|’)s on)$/i.test(line);
  const summary = lines.slice(0, dateIndex).find((line) => line.length > 3 && !/^(open|closed)/i.test(line) && !isGeneric(line))
    || lines.slice(dateIndex + 1).find((line) => line.length > 3 && !parseDisplayedDate(line));
  if (!summary) return null;
  const location = lines.find((line) => /\b(?:UK|PO\d{1,2}|Cowes|Newport|Shorwell|Ryde|Yarmouth|Sandown|Ventnor)\b/i.test(line) && line !== summary) || "Isle of Wight, UK";
  const locationIndex = lines.indexOf(location);
  const relatedIndex = lines.findIndex((line, index) => index > locationIndex && /^other events\s*:?$/i.test(line));
  const descriptionEnd = relatedIndex > locationIndex ? relatedIndex : lines.length;
  const description = lines.slice(locationIndex + 1, descriptionEnd)
    .filter((line) => !/^(show more|home|explore|property|about)/i.test(line) && line.length > 20)
    .join("\n\n");
  const event = { summary, ...dates, location, description, url: sourceUrl };
  event.uid = stableUid(event);
  return event;
}

function selectedEventFromText(lines, sourceUrl, selectedTitle) {
  const titleIndex = lines.findIndex((line) => !parseDisplayedDate(line) && titlesMatch(selectedTitle, line));
  if (titleIndex < 0) return null;
  const nearbyBefore = lines.slice(Math.max(0, titleIndex - 4), titleIndex).reverse();
  const nearbyAfter = lines.slice(titleIndex + 1, titleIndex + 5);
  const dateLine = [...nearbyBefore, ...nearbyAfter].find((line) => parseDisplayedDate(line));
  if (!dateLine) return null;
  return eventFromText([dateLine, lines[titleIndex], ...lines.slice(titleIndex + 1)], sourceUrl);
}

async function scrapeEventDetails(page, url, selectedTitle) {
  let lastEvent = null;
  for (let attempt = 0; attempt < 24; attempt += 1) {
    const lines = (await page.locator("body").innerText()).split("\n").map(tidy).filter(Boolean);
    lastEvent = selectedEventFromText(lines, page.url() || url, selectedTitle);
    if (lastEvent) {
      await expandShowMore(page);
      const expandedLines = (await page.locator("body").innerText()).split("\n").map(tidy).filter(Boolean);
      return selectedEventFromText(expandedLines, page.url() || url, selectedTitle) || lastEvent;
    }
    await page.waitForTimeout(500);
  }
  return lastEvent;
}

async function scrapeEvents(page, guideUrl) {
  await gotoWithRetry(page, guideUrl);
  await page.waitForTimeout(4_000);
  const cards = await discoverCards(page, "Events", "Our Favourite Places");
  console.log(`Discovered ${cards.length} event-card candidates: ${cards.map((card) => card.label).join(" | ")}`);
  const events = [];
  for (const originalCard of cards) {
    const currentCards = await discoverCards(page, "Events", "Our Favourite Places");
    const card = currentCards.find((item) => item.label === originalCard.label);
    if (!card) continue;
    const target = page.locator(`[data-guide-scrape-token="${card.token}"]`);
    if (!await target.count()) continue;
    await Promise.all([
      page.waitForURL((url) => url.searchParams.get("v") === "event" && Boolean(url.searchParams.get("event")), { timeout: 15_000 }),
      target.click(),
    ]);
    const eventUrl = page.url();
    await gotoWithRetry(page, eventUrl);
    const event = await scrapeEventDetails(page, eventUrl, originalCard.label);
    if (!event) throw new Error(`Could not extract detail-page data for selected event: ${originalCard.label}`);
    if (!titlesMatch(originalCard.label, event.summary)) {
      throw new Error(`Selected event title did not match detail page: ${originalCard.label} -> ${event.summary} (${eventUrl})`);
    }
    console.log(`Selected event detail: url=${eventUrl} title=${event.summary} date=${event.start}${event.end ? `..${event.end}` : ""}`);
    if (events.some((item) => item.uid === event.uid)) {
      throw new Error(`Duplicate event detail returned for selected event: ${originalCard.label} (${eventUrl})`);
    }
    events.push(event);
    await gotoWithRetry(page, guideUrl);
    await page.waitForTimeout(4_000);
  }
  if (events.length !== cards.length) {
    throw new Error(`Incomplete event scrape: extracted ${events.length} of ${cards.length}; retained the previous successful feed`);
  }
  console.log(`Scraped event dates: ${events.map((event) => `${event.summary}=${event.start}`).join(" | ")}`);
  return events;
}

async function scrapeFavourites(page, guideUrl) {
  await gotoWithRetry(page, guideUrl);
  await page.waitForTimeout(3_000);
  const cards = (await discoverCards(page, "Our Favourite Places", "__end_of_page__"))
    .filter((card) => !/^(home|explore|property|about)$/i.test(card.label));
  console.log(`Discovered ${cards.length} favourite-place candidates: ${cards.map((card) => card.label).join(" | ")}`);
  const favourites = [];
  for (const originalCard of cards.slice(0, 60)) {
    const currentCards = (await discoverCards(page, "Our Favourite Places", "__end_of_page__"))
      .filter((item) => !/^(home|explore|property|about)$/i.test(item.label));
    const card = currentCards.find((item) => item.label === originalCard.label);
    if (!card) continue;
    const target = page.locator(`[data-guide-scrape-token="${card.token}"]`);
    if (!await target.count()) continue;
    await target.click().catch(() => undefined);
    await page.waitForURL((url) => url.searchParams.get("v") === "POI" && Boolean(url.searchParams.get("poi")), { timeout: 15_000 }).catch(() => undefined);
    const sourceUrl = page.url();
    await gotoWithRetry(page, sourceUrl);
    await page.waitForTimeout(2_500);
    await expandShowMore(page);
    const lines = (await page.locator("body").innerText()).split("\n").map(tidy).filter(Boolean);
    const mapsUrl = await page.locator('a[href*="maps.google.com"],a[href*="google.com/maps"]').first().getAttribute("href").catch(() => null);
    const favourite = favouriteFromText(lines, card.label, { mapsUrl: mapsUrl || "", sourceUrl });
    if (favourite) favourites.push(favourite);
    else console.warn(`Could not isolate details for favourite place: ${originalCard.label}`);
    await gotoWithRetry(page, guideUrl);
    await page.waitForTimeout(3_000);
  }
  if (favourites.length !== cards.length) {
    throw new Error(`Incomplete favourite-place scrape: extracted ${favourites.length} of ${cards.length}; retained the previous successful feed`);
  }
  return favourites;
}

export async function scrapeGuide({ guideUrl, scrapeFavourites: includeFavourites = true, timezone = "Europe/London" }) {
  const browser = await chromium.launch({
    executablePath: await findChromium(),
    headless: true,
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
  });
  try {
    const context = await browser.newContext({ locale: "en-GB", timezoneId: timezone });
    const page = await context.newPage();
    const events = await scrapeEvents(page, guideUrl);
    if (!events.length) throw new Error("No events were extracted; retained the previous successful feed");
    const favourites = includeFavourites ? await scrapeFavourites(page, guideUrl) : [];
    return { events, favourites };
  } finally {
    await browser.close();
  }
}
