import { chromium } from "playwright-core";
import { parseDisplayedDate } from "./dates.js";
import { stableUid } from "./calendar.js";
import { favouriteFromText } from "./favourites.js";

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
      // Use the visible title node for proximity. The clickable ancestor may
      // span the whole row, which would make every date badge appear equally near.
      const titleBox = element.getBoundingClientRect();
      const datePattern = /\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b[^\n]{0,30}\b\d{4}\b/i;
      const dateCandidate = nodes
        .filter((node) => {
          const text = String(node.textContent || "").replace(/\s+/g, " ").trim();
          return visible(node) && text.length <= 100 && datePattern.test(text);
        })
        .map((node) => {
          const box = node.getBoundingClientRect();
          const dx = Math.max(box.left - titleBox.right, titleBox.left - box.right, 0);
          const dy = Math.max(box.top - titleBox.bottom, titleBox.top - box.bottom, 0);
          return { text: String(node.textContent || "").replace(/\s+/g, " ").trim(), distance: dx + dy, area: box.width * box.height };
        })
        .sort((left, right) => left.distance - right.distance || left.area - right.area)[0]?.text || "";
      seen.add(label);
      let cardContainer = clickable;
      const hasDateText = (text) => /\b(?:\d{1,2}\s+)?(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b.*\b\d{4}\b/i.test(text);
      for (let level = 0; level < 8 && cardContainer.parentElement; level += 1) {
        const parent = cardContainer.parentElement;
        const parentText = String(parent.innerText || parent.textContent || "").trim();
        if (parentText.length > label.length && parentText.length <= 900) {
          cardContainer = parent;
          if (hasDateText(parentText)) break;
        }
      }
      results.push({
        token,
        label,
        dateText: dateCandidate,
        cardText: String(cardContainer.innerText || cardContainer.textContent || "")
          .replace(/\s*\n\s*/g, "\n")
          .trim(),
      });
    }
    return results;
  }, { startLabel, endLabel });
}

function eventFromText(lines, sourceUrl, fallbackSummary = "") {
  const dateLine = lines.find((line) => parseDisplayedDate(line));
  const dates = dateLine ? parseDisplayedDate(dateLine) : null;
  if (!dates) return null;
  const dateIndex = lines.indexOf(dateLine);
  const isGeneric = (line) => /^(open|closed|show more|other events|home|explore|property|about|local events(?:\s*&\s*favourite places)?|what(?:'|’)s on)$/i.test(line);
  const isUseful = (line) => line.length > 3 && !isGeneric(line) && !parseDisplayedDate(line);
  const summary = (fallbackSummary && isUseful(fallbackSummary) ? fallbackSummary : "")
    || lines.slice(0, dateIndex).find((line) => line.length > 3 && !/^(open|closed)/i.test(line) && !isGeneric(line))
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

async function scrapeEventDetails(page, url, fallbackSummary = "") {
  await page.waitForTimeout(600);
  await expandShowMore(page);
  const lines = (await page.locator("body").innerText()).split("\n").map(tidy).filter(Boolean);
  return eventFromText(lines, page.url() || url, fallbackSummary);
}

function eventFromCard(card, sourceUrl) {
  const lines = String(card.cardText || "").split("\n").map(tidy).filter(Boolean);
  const titleIndex = lines.findIndex((line) => line === card.label || line.includes(card.label) || card.label.includes(line));
  const nearbyLines = titleIndex >= 0 ? lines.slice(Math.max(0, titleIndex - 2), titleIndex + 5) : lines;
  const dateLines = [card.dateText, ...nearbyLines].filter((line) => parseDisplayedDate(line));
  const dateLine = dateLines
    .map((line) => ({ line, dates: parseDisplayedDate(line) }))
    .filter(({ dates }) => dates && dates.end > new Date().toISOString().slice(0, 10))
    .sort((left, right) => left.dates.start.localeCompare(right.dates.start))[0]?.line
    || dateLines[0];
  return dateLine ? eventFromText([card.label, dateLine], sourceUrl, card.label, dateLine) : null;
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
    const cardEvent = eventFromCard(card, guideUrl);
    await target.click().catch(() => undefined);
    const detailEvent = await scrapeEventDetails(page, guideUrl, originalCard.label).catch(() => null);
    const event = cardEvent && detailEvent
      ? { ...detailEvent, summary: cardEvent.summary, start: cardEvent.start, end: cardEvent.end, all_day: cardEvent.all_day, uid: cardEvent.uid }
      : cardEvent || detailEvent;
    if (event && !events.some((item) => item.uid === event.uid)) events.push(event);
    else console.warn(`Could not extract an event from candidate: ${originalCard.label}`);
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
