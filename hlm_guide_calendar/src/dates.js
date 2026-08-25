import { addDays } from "./calendar.js";

const months = new Map([
  ["january", 1], ["february", 2], ["march", 3], ["april", 4],
  ["may", 5], ["june", 6], ["july", 7], ["august", 8],
  ["september", 9], ["october", 10], ["november", 11], ["december", 12],
  ["jan", 1], ["feb", 2], ["mar", 3], ["apr", 4], ["jun", 6],
  ["jul", 7], ["aug", 8], ["sep", 9], ["sept", 9], ["oct", 10],
  ["nov", 11], ["dec", 12],
]);

const iso = (year, month, day) => `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;

export function parseDisplayedDate(value) {
  const text = String(value || "").replace(/[–—]/g, "-").replace(/\s+/g, " ").trim();
  let match = text.match(/([A-Za-z]+)\s+(\d{1,2})\s*-\s*([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})/i);
  if (match) {
    const startMonth = months.get(match[1].toLowerCase());
    const endMonth = months.get(match[3].toLowerCase());
    if (!startMonth || !endMonth) return null;
    const year = Number(match[5]);
    return {
      start: iso(year, startMonth, Number(match[2])),
      end: addDays(iso(year, endMonth, Number(match[4])), 1),
      all_day: true,
    };
  }
  match = text.match(/(?:\w{3,9},? )?(\d{1,2})\s*-\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/i);
  if (match) {
    const month = months.get(match[3].toLowerCase());
    if (!month) return null;
    const start = iso(Number(match[4]), month, Number(match[1]));
    const inclusiveEnd = iso(Number(match[4]), month, Number(match[2]));
    return { start, end: addDays(inclusiveEnd, 1), all_day: true };
  }

  match = text.match(/(?:\w{3,9},? )?(\d{1,2})\s+([A-Za-z]+)\s*-\s*(?:\w{3,9},? )?(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/i);
  if (match) {
    const startMonth = months.get(match[2].toLowerCase());
    const endMonth = months.get(match[4].toLowerCase());
    if (!startMonth || !endMonth) return null;
    const year = Number(match[5]);
    return {
      start: iso(year, startMonth, Number(match[1])),
      end: addDays(iso(year, endMonth, Number(match[3])), 1),
      all_day: true,
    };
  }

  match = text.match(/(?:\w{3,9},? )?(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/i);
  if (match) {
    const month = months.get(match[2].toLowerCase());
    if (!month) return null;
    const start = iso(Number(match[3]), month, Number(match[1]));
    return { start, end: addDays(start, 1), all_day: true };
  }
  return null;
}
