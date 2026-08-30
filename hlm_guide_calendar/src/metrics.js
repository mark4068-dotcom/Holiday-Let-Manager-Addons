import { readFile, writeFile, rename, mkdir } from "node:fs/promises";
import { dirname } from "node:path";

const ALLOWED = new Set([
  "session", "tab_welcome", "tab_events", "tab_house", "tab_heating",
  "tab_weather", "directions", "screensaver_wakeup", "external_return",
]);

const dayKey = (date = new Date()) => date.toISOString().slice(0, 10);

export async function recordMetric(path, event, date = new Date()) {
  if (!ALLOWED.has(event)) return false;
  let data = {};
  try { data = JSON.parse(await readFile(path, "utf8")); } catch { /* first event */ }
  const cutoff = new Date(date);
  cutoff.setUTCFullYear(cutoff.getUTCFullYear() - 1);
  for (const key of Object.keys(data)) if (key < dayKey(cutoff)) delete data[key];
  const day = dayKey(date);
  data[day] ||= { total: 0, events: {} };
  data[day].total += 1;
  data[day].events[event] = (data[day].events[event] || 0) + 1;
  await mkdir(dirname(path), { recursive: true });
  const temporary = `${path}.tmp`;
  await writeFile(temporary, `${JSON.stringify(data, null, 2)}\n`);
  await rename(temporary, path);
  return true;
}

export const allowedMetrics = ALLOWED;

export async function metricsSummary(path) {
  let data = {};
  try { data = JSON.parse(await readFile(path, "utf8")); } catch { /* no usage yet */ }
  const days = Object.keys(data).sort();
  const total = days.reduce((sum, day) => sum + Number(data[day]?.total || 0), 0);
  const latestDay = days.at(-1) || null;
  return { total, days: days.length, latest_day: latestDay, latest_total: latestDay ? data[latestDay].total : 0, latest_events: latestDay ? data[latestDay].events : {} };
}
